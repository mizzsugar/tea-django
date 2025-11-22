import uuid
from django.db import migrations


def populate_verification_tokens(apps, schema_editor):
    """既存ユーザーにemail_verification_tokenを設定"""
    User = apps.get_model('tea', 'User')
    
    # email_verification_tokenがNullの全ユーザーを取得
    users_without_token = User.objects.filter(email_verification_token__isnull=True)
    
    for user in users_without_token:
        user.email_verification_token = uuid.uuid4()
    
    # bulk_updateで一括更新（効率的）
    User.objects.bulk_update(users_without_token, ['email_verification_token'])


def reverse_populate_verification_tokens(apps, schema_editor):
    """ロールバック時の処理（必要に応じてNullに戻す）"""
    User = apps.get_model('tea', 'User')
    User.objects.all().update(email_verification_token=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tea', '0004_user_email_verification_sent_at_and_more'),
    ]

    operations = [
        migrations.RunPython(
            populate_verification_tokens,
            reverse_populate_verification_tokens
        ),
    ]