import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from authentication.services.registration_service import (
    RegistrationResultType,
    RegistrationService,
    ResendResultType,
    VerificationResultType,
)
from model.models import User


@pytest.fixture
def base_url():
    """テスト用ベースURL"""
    return "http://example.com/"


@pytest.fixture
def unverified_user(db):
    """未確認ユーザー"""
    user = User(
        email="unverified@example.com",
        nickname="未確認ユーザー",
        is_active=False,
        is_email_verified=False,
        email_verification_token=uuid.uuid4(),
    )
    user.set_password("testpass123")
    user.save()
    return user


@pytest.fixture
def verified_user(db):
    """確認済みユーザー"""
    user = User(
        email="verified@example.com",
        nickname="確認済みユーザー",
        is_active=True,
        is_email_verified=True,
        email_verification_token=uuid.uuid4(),
    )
    user.set_password("testpass123")
    user.save()
    return user


class TestRegistrationServiceRegisterUser:
    """RegistrationService.register_user のテスト"""

    @patch("authentication.services.registration_service.send_verification_email")
    def test_creates_new_user_successfully(self, mock_send_email, db, base_url):
        """新規ユーザーを正常に作成できる"""
        result = RegistrationService.register_user(
            email="newuser@example.com",
            password="testpass123",
            nickname="新規ユーザー",
            base_url=base_url,
        )

        assert result.result_type == RegistrationResultType.SUCCESS
        assert result.user is not None
        assert result.user.email == "newuser@example.com"
        assert result.user.nickname == "新規ユーザー"
        assert result.user.is_active is False
        assert result.user.is_email_verified is False
        mock_send_email.assert_called_once()

    @patch("authentication.services.registration_service.send_verification_email")
    def test_updates_unverified_user(self, mock_send_email, unverified_user, base_url):
        """未確認ユーザーの情報を更新する"""
        old_token = unverified_user.email_verification_token

        result = RegistrationService.register_user(
            email="unverified@example.com",
            password="newpassword123",
            nickname="更新されたニックネーム",
            base_url=base_url,
        )

        assert result.result_type == RegistrationResultType.SUCCESS
        unverified_user.refresh_from_db()
        assert unverified_user.nickname == "更新されたニックネーム"
        assert unverified_user.email_verification_token != old_token
        mock_send_email.assert_called_once()

    @patch("authentication.services.registration_service.send_verification_email")
    def test_does_not_expose_verified_user(
        self, mock_send_email, verified_user, base_url
    ):
        """確認済みユーザーのメールアドレスで登録しても情報を漏らさない"""
        result = RegistrationService.register_user(
            email="verified@example.com",
            password="newpassword123",
            nickname="新しいニックネーム",
            base_url=base_url,
        )

        # セキュリティ上、成功と同じメッセージを返す
        assert result.result_type == RegistrationResultType.SUCCESS
        assert result.user is None  # ユーザー情報は返さない
        mock_send_email.assert_not_called()  # メールは送らない

    @patch("authentication.services.registration_service.send_verification_email")
    def test_returns_error_when_email_fails(self, mock_send_email, db, base_url):
        """メール送信失敗時はエラーを返す"""
        mock_send_email.side_effect = Exception("Email failed")

        result = RegistrationService.register_user(
            email="newuser@example.com",
            password="testpass123",
            nickname="新規ユーザー",
            base_url=base_url,
        )

        assert result.result_type == RegistrationResultType.EMAIL_SEND_FAILED
        assert "エラーが発生しました" in result.message
        # ユーザーは削除される
        assert not User.objects.filter(email="newuser@example.com").exists()


class TestRegistrationServiceVerifyEmail:
    """RegistrationService.verify_email のテスト"""

    def test_verifies_email_successfully(self, unverified_user):
        """メールアドレスを正常に確認できる"""
        token = str(unverified_user.email_verification_token)

        result = RegistrationService.verify_email(token)

        assert result.result_type == VerificationResultType.SUCCESS
        unverified_user.refresh_from_db()
        assert unverified_user.is_email_verified is True
        assert unverified_user.is_active is True

    def test_returns_already_verified_for_verified_user(self, verified_user):
        """確認済みユーザーには既に確認済みのメッセージを返す"""
        token = str(verified_user.email_verification_token)

        result = RegistrationService.verify_email(token)

        assert result.result_type == VerificationResultType.ALREADY_VERIFIED
        assert "既に" in result.message

    def test_returns_invalid_token_for_nonexistent_token(self, db):
        """存在しないトークンには無効なトークンのエラーを返す"""
        result = RegistrationService.verify_email(str(uuid.uuid4()))

        assert result.result_type == VerificationResultType.INVALID_TOKEN
        assert "無効" in result.message

    def test_returns_expired_for_old_token(self, unverified_user):
        """期限切れトークンにはエラーを返す"""
        # トークンを期限切れにする
        unverified_user.email_verification_sent_at = timezone.now() - timedelta(
            hours=25
        )
        unverified_user.save()

        token = str(unverified_user.email_verification_token)

        result = RegistrationService.verify_email(token)

        assert result.result_type == VerificationResultType.TOKEN_EXPIRED
        assert "有効期限" in result.message


class TestRegistrationServiceResendVerificationEmail:
    """RegistrationService.resend_verification_email のテスト"""

    @patch("authentication.services.registration_service.send_verification_email")
    def test_resends_email_successfully(
        self, mock_send_email, unverified_user, base_url
    ):
        """確認メールを正常に再送信できる"""
        result = RegistrationService.resend_verification_email(
            "unverified@example.com", base_url
        )

        assert result.result_type == ResendResultType.SUCCESS
        assert "再送信" in result.message
        mock_send_email.assert_called_once()

    @patch("authentication.services.registration_service.send_verification_email")
    def test_returns_error_for_nonexistent_email(self, mock_send_email, db, base_url):
        """存在しないメールアドレスにはエラーを返す"""
        result = RegistrationService.resend_verification_email(
            "nonexistent@example.com", base_url
        )

        assert result.result_type == ResendResultType.USER_NOT_FOUND
        assert "見つからない" in result.message
        mock_send_email.assert_not_called()

    @patch("authentication.services.registration_service.send_verification_email")
    def test_returns_error_for_verified_email(
        self, mock_send_email, verified_user, base_url
    ):
        """確認済みメールアドレスにはエラーを返す"""
        result = RegistrationService.resend_verification_email(
            "verified@example.com", base_url
        )

        assert result.result_type == ResendResultType.USER_NOT_FOUND
        assert "見つからない" in result.message or "確認済み" in result.message
        mock_send_email.assert_not_called()
