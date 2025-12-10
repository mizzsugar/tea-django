import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from django.db import IntegrityError

from authentication.utils import send_verification_email
from model.models import User

logger = logging.getLogger(__name__)


class RegistrationResultType(Enum):
    """登録結果の種類"""

    SUCCESS = "success"
    EMAIL_SEND_FAILED = "email_send_failed"
    INTEGRITY_ERROR = "integrity_error"


@dataclass
class RegistrationResult:
    """ユーザー登録の結果"""

    result_type: RegistrationResultType
    user: Optional[User] = None
    message: str = ""


class VerificationResultType(Enum):
    """メール確認結果の種類"""

    SUCCESS = "success"
    ALREADY_VERIFIED = "already_verified"
    TOKEN_EXPIRED = "token_expired"
    INVALID_TOKEN = "invalid_token"


@dataclass
class VerificationResult:
    """メール確認の結果"""

    result_type: VerificationResultType
    user: Optional[User] = None
    message: str = ""


class ResendResultType(Enum):
    """再送信結果の種類"""

    SUCCESS = "success"
    USER_NOT_FOUND = "user_not_found"
    ALREADY_VERIFIED = "already_verified"


@dataclass
class ResendResult:
    """確認メール再送信の結果"""

    result_type: ResendResultType
    message: str = ""


class RegistrationService:
    """ユーザー登録関連のビジネスロジック"""

    @staticmethod
    def register_user(
        email: str, password: str, nickname: str, base_url: str
    ) -> RegistrationResult:
        """
        ユーザー登録処理

        既存ユーザーが存在する場合:
        - 確認済み: 何もしない（セキュリティ上、成功と同じメッセージ）
        - 未確認: パスワードとニックネームを更新し、確認メールを再送信

        新規ユーザーの場合:
        - ユーザーを作成し、確認メールを送信

        Args:
            email: メールアドレス
            password: パスワード
            nickname: ニックネーム
            base_url: サイトのベースURL（メールのURL生成に使用）

        Returns:
            RegistrationResult: 登録結果
        """
        existing_user = User.objects.filter(email=email).first()

        if existing_user:
            return RegistrationService._handle_existing_user(
                existing_user, password, nickname, base_url
            )
        else:
            return RegistrationService._create_new_user(
                email, password, nickname, base_url
            )

    @staticmethod
    def _handle_existing_user(
        user: User, password: str, nickname: str, base_url: str
    ) -> RegistrationResult:
        """既存ユーザーの登録処理"""
        if user.is_email_verified:
            # セキュリティ上、新規登録と同じメッセージを返す
            return RegistrationResult(
                result_type=RegistrationResultType.SUCCESS,
                user=None,
                message="登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。",
            )

        # 未確認ユーザーの情報を更新
        try:
            user.set_password(password)
            user.nickname = nickname
            user.email_verification_token = uuid.uuid4()
            user.save()

            send_verification_email(user, base_url)

            return RegistrationResult(
                result_type=RegistrationResultType.SUCCESS,
                user=user,
                message="登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。",
            )
        except Exception as e:
            logger.info(f"Failed to update existing user: {e}")
            # セキュリティ上、エラーでも成功メッセージを返す
            return RegistrationResult(
                result_type=RegistrationResultType.SUCCESS,
                user=None,
                message="登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。",
            )

    @staticmethod
    def _create_new_user(
        email: str, password: str, nickname: str, base_url: str
    ) -> RegistrationResult:
        """新規ユーザー作成処理"""
        try:
            user = User(
                email=email,
                nickname=nickname,
                is_active=False,
                is_email_verified=False,
                email_verification_token=uuid.uuid4(),
            )
            user.set_password(password)
            user.save()

            try:
                send_verification_email(user, base_url)
                return RegistrationResult(
                    result_type=RegistrationResultType.SUCCESS,
                    user=user,
                    message="登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。",
                )
            except Exception as e:
                logger.info(f"Failed to send verification email: {e}")
                user.delete()
                return RegistrationResult(
                    result_type=RegistrationResultType.EMAIL_SEND_FAILED,
                    user=None,
                    message="登録処理中にエラーが発生しました。しばらくしてから再度お試しください。",
                )

        except IntegrityError:
            # 同時リクエストなどで重複が発生した場合
            return RegistrationResult(
                result_type=RegistrationResultType.INTEGRITY_ERROR,
                user=None,
                message="登録ありがとうございます。確認メールを送信しました。メール内のリンクをクリックして登録を完了してください。",
            )

    @staticmethod
    def verify_email(token: str) -> VerificationResult:
        """
        メールアドレス確認処理

        Args:
            token: 確認トークン

        Returns:
            VerificationResult: 確認結果
        """
        try:
            user = User.objects.get(email_verification_token=token)
        except User.DoesNotExist:
            return VerificationResult(
                result_type=VerificationResultType.INVALID_TOKEN,
                message="無効な確認リンクです。",
            )

        # トークンの有効期限チェック
        if not user.is_verification_token_valid():
            return VerificationResult(
                result_type=VerificationResultType.TOKEN_EXPIRED,
                user=user,
                message="確認リンクの有効期限が切れています。再度登録をお願いします。",
            )

        # 既に確認済みの場合
        if user.is_email_verified:
            return VerificationResult(
                result_type=VerificationResultType.ALREADY_VERIFIED,
                user=user,
                message="既にメールアドレスは確認済みです。",
            )

        # メール確認完了
        user.is_email_verified = True
        user.is_active = True
        user.save(update_fields=["is_email_verified", "is_active"])

        return VerificationResult(
            result_type=VerificationResultType.SUCCESS,
            user=user,
            message="メールアドレスの確認が完了しました。ログインしてください。",
        )

    @staticmethod
    def resend_verification_email(email: str, base_url: str) -> ResendResult:
        """
        確認メール再送信

        Args:
            email: メールアドレス
            base_url: サイトのベースURL

        Returns:
            ResendResult: 再送信結果
        """
        try:
            user = User.objects.get(email=email, is_email_verified=False)
            send_verification_email(user, base_url)
            return ResendResult(
                result_type=ResendResultType.SUCCESS,
                message="確認メールを再送信しました。",
            )
        except User.DoesNotExist:
            return ResendResult(
                result_type=ResendResultType.USER_NOT_FOUND,
                message="そのメールアドレスのユーザーが見つからないか、既に確認済みです。",
            )
