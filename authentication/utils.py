import uuid

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone


def send_verification_email(user, base_url: str):
    """
    確認メールを送信

    Args:
        user: ユーザー
        base_url: サイトのベースURL（例: "http://example.com/"）
    """
    # トークンを再生成
    user.email_verification_token = uuid.uuid4()
    user.email_verification_sent_at = timezone.now()
    user.save(update_fields=["email_verification_token", "email_verification_sent_at"])

    # 確認URL生成
    base_url = base_url.rstrip("/")
    verification_url = f"{base_url}/auth/verify-email/{user.email_verification_token}/"

    # メール本文
    subject = "メールアドレスの確認"
    message = render_to_string(
        "authentication/emails/verification_email.txt",
        {
            "user": user,
            "verification_url": verification_url,
        },
    )
    html_message = render_to_string(
        "authentication/emails/verification_email.html",
        {
            "user": user,
            "verification_url": verification_url,
        },
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
