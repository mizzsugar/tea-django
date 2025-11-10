from django.contrib.auth.models import AbstractUser

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """カスタムユーザーマスタ"""
    nickname = models.CharField(max_length=30, blank=True, verbose_name="ニックネーム")

    def __str__(self):
        return self.nickname or self.username


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
