from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """カスタムユーザーマネージャー"""
    
    def _generate_unique_username(self, email):
        """ユニークなusernameを生成"""
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        # 重複しないusernameを探す
        while self.model.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        return username
    
    def create_user(self, email, password=None, **extra_fields):
        """一般ユーザーを作成"""
        if not email:
            raise ValueError('メールアドレスは必須です')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """スーパーユーザーを作成"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('スーパーユーザーはis_staff=Trueである必要があります')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('スーパーユーザーはis_superuser=Trueである必要があります')
        
        # スーパーユーザーにはusernameを設定（重複しないように）
        if 'username' not in extra_fields or not extra_fields['username']:
            extra_fields['username'] = self._generate_unique_username(email)
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """カスタムユーザーモデル"""
    objects = UserManager()
    
    # usernameをオプショナルにする（一般ユーザーは不要）
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        verbose_name="ユーザー名(管理者用)",
        help_text="管理者用のユーザー名"
    )

    email = models.EmailField(
        unique=True,
        verbose_name="メールアドレス"
    )
    
    nickname = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="ユーザー名(一般ユーザー用)",
        help_text="一般ユーザー用のユーザー名"
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"
    
    def __str__(self):
        return self.nickname or self.username or self.email
    
    def _generate_unique_username_from_email(self):
        """emailからユニークなusernameを生成"""
        base_username = self.email.split('@')[0]
        username = base_username
        counter = 1
        
        # 自分自身は除外して重複チェック
        while User.objects.filter(username=username).exclude(pk=self.pk).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        return username
    
    def save(self, *args, **kwargs):
        # スーパーユーザーまたはスタッフの場合、usernameが必須
        # 一般ユーザーの場合、usernameはNulになる。
        if (self.is_superuser or self.is_staff) and not self.username:
            self.username = self._generate_unique_username_from_email()
        

        super().save(*args, **kwargs)
    
    def get_display_name(self):
        """表示用の名前を取得"""
        return self.nickname or self.email.split('@')[0]

    @property
    def favorites_count(self):
        return self.favorite_teas.count()


class Tea(models.Model):
    """お茶マスタ"""
    STEAM_TYPE_CHOICES = [
        ("light", "浅蒸し"),
        ("middle", "中蒸し"),
        ("deep", "深蒸し"),
    ]

    name = models.CharField(max_length=100, verbose_name="お茶名")
    
    steam_type = models.CharField(max_length=20, choices=STEAM_TYPE_CHOICES, verbose_name="蒸し度")
    origin = models.CharField(max_length=100, blank=True, verbose_name="産地")
    description = models.TextField(blank=True, verbose_name="説明")
    caffeine_free = models.BooleanField(default=False, verbose_name="カフェインレス")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="公開日時")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return self.name


class FavoriteTea(models.Model):
    """お気に入りテーブル（ユーザーとお茶の中間テーブル）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorite_teas")
    tea = models.ForeignKey(Tea, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")

    class Meta:
        unique_together = ("user", "tea")  # 同じお茶を重複登録できないように
        verbose_name = "お気に入り"
        verbose_name_plural = "お気に入り一覧"

    def __str__(self):
        return f"{self.user} → {self.tea}"


class TeaReview(models.Model):
    """お茶に対するレビュー"""
    RATING_CHOICES = [
        (1, "★☆☆☆☆"),
        (2, "★★☆☆☆"),
        (3, "★★★☆☆"),
        (4, "★★★★☆"),
        (5, "★★★★★"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tea_reviews")
    tea = models.ForeignKey(Tea, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveIntegerField(verbose_name="評価", choices=RATING_CHOICES)
    content = models.TextField(blank=True, verbose_name="レビュー内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")

    class Meta:
        unique_together = ("user", "tea")
        verbose_name = "レビュー"
        verbose_name_plural = "レビュー一覧"
    
    def __str__(self):
        return f"{self.user} のレビュー: {self.content[:20]}..."
    
    def get_star_display(self):
        """星表示を返す"""
        return "★" * self.rating + "☆" * (5 - self.rating)