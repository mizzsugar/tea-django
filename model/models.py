import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

from config import settings


class UserManager(BaseUserManager):
    """カスタムユーザーマネージャー"""

    def _generate_unique_username(self, email):
        """ユニークなusernameを生成"""
        base_username = email.split("@")[0]
        username = base_username
        counter = 1
        while self.model.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        return username

    def create_user(self, email, password=None, **extra_fields):
        """一般ユーザーを作成"""
        if not email:
            raise ValueError("メールアドレスは必須です")

        email = self.normalize_email(email)

        # デフォルトでは未確認・非アクティブ
        extra_fields.setdefault("is_email_verified", False)
        extra_fields.setdefault("is_active", False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """スーパーユーザーを作成"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_email_verified", True)  # 確認済み
        extra_fields.setdefault("is_active", True)  # アクティブ

        if extra_fields.get("is_staff") is not True:
            raise ValueError("スーパーユーザーはis_staff=Trueである必要があります")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("スーパーユーザーはis_superuser=Trueである必要があります")

        if "username" not in extra_fields or not extra_fields["username"]:
            extra_fields["username"] = self._generate_unique_username(email)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """カスタムユーザーモデル"""

    objects = UserManager()

    TEA_PREFERENCE_CHOICES = [
        ("light", "浅蒸し"),
        ("middle", "中蒸し"),
        ("deep", "深蒸し"),
    ]

    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        verbose_name="ユーザー名(管理者用)",
        help_text="管理者用のユーザー名",
    )
    email = models.EmailField(unique=True, verbose_name="メールアドレス")
    nickname = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="ユーザー名(一般ユーザー用)",
        help_text="一般ユーザー用のユーザー名",
    )

    # メール確認用フィールド
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name="メール確認済み",
        help_text="メールアドレスが確認されているかどうか",
    )
    email_verification_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name="メール確認トークン",
    )
    email_verification_sent_at = models.DateTimeField(
        null=True, blank=True, verbose_name="確認メール送信日時"
    )

    tea_preference = models.CharField(
        max_length=20,
        choices=TEA_PREFERENCE_CHOICES,
        blank=True,
        null=True,
        verbose_name="お茶の好み",
        help_text="診断結果によるお茶の好み（蒸し度）",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"
        db_table = "users"

    def __str__(self):
        return self.nickname or self.username or self.email

    def _generate_unique_username_from_email(self):
        """emailからユニークなusernameを生成"""
        base_username = self.email.split("@")[0]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exclude(pk=self.pk).exists():
            username = f"{base_username}{counter}"
            counter += 1
        return username

    def save(self, *args, **kwargs):
        if (self.is_superuser or self.is_staff) and not self.username:
            self.username = self._generate_unique_username_from_email()
        super().save(*args, **kwargs)

    def get_display_name(self):
        """表示用の名前を取得"""
        return self.nickname or self.email.split("@")[0]

    @property
    def favorites_count(self):
        return self.favorite_teas.count()

    def is_verification_token_valid(self):
        """確認トークンが有効かチェック(24時間以内)"""
        if not self.email_verification_sent_at:
            return True
        expiry_time = self.email_verification_sent_at + timedelta(hours=24)
        return timezone.now() < expiry_time


class Tea(models.Model):
    """お茶マスタ"""

    STEAM_TYPE_CHOICES = [
        ("light", "浅蒸し"),
        ("middle", "中蒸し"),
        ("deep", "深蒸し"),
    ]

    name = models.CharField(max_length=100, verbose_name="お茶名")
    image = models.ImageField(null=True, blank=True, upload_to="photos/")
    steam_type = models.CharField(
        max_length=20, choices=STEAM_TYPE_CHOICES, verbose_name="蒸し度"
    )
    origin = models.CharField(max_length=100, blank=True, verbose_name="産地")
    description = models.TextField(blank=True, verbose_name="説明")
    caffeine_free = models.BooleanField(default=False, verbose_name="カフェインレス")
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="公開日時")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "お茶"
        verbose_name_plural = "お茶一覧"
        db_table = "teas"


class FavoriteTea(models.Model):
    """お気に入りテーブル（ユーザーとお茶の中間テーブル）"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="favorite_teas"
    )
    tea = models.ForeignKey(Tea, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")

    class Meta:
        unique_together = ("user", "tea")  # 同じお茶を重複登録できないように
        verbose_name = "お気に入り"
        verbose_name_plural = "お気に入り一覧"
        db_table = "favorite_teas"

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
        db_table = "tea_reviews"

    def __str__(self):
        return f"{self.user} のレビュー: {self.content[:20]}..."

    def get_star_display(self):
        """星表示を返す"""
        return "★" * self.rating + "☆" * (5 - self.rating)


class TaxRate(models.Model):
    """消費税率マスタ"""

    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="税率(%)",
        help_text="例: 10.00 (10%の場合)",
    )
    start_date = models.DateField(verbose_name="適用開始日")
    is_active = models.BooleanField(default=True, verbose_name="有効")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")

    def __str__(self):
        return f"{self.rate}% (適用開始: {self.start_date})"

    @classmethod
    def get_current_rate(cls):
        """現在有効な税率を取得"""
        from django.utils import timezone

        today = timezone.now().date()

        tax_rate = (
            cls.objects.filter(is_active=True, start_date__lte=today)
            .order_by("-start_date")
            .first()
        )

        if tax_rate:
            return tax_rate.rate
        return 10.00  # デフォルト10%

    class Meta:
        db_table = "tax_rates"
        verbose_name = "消費税率"
        verbose_name_plural = "消費税率"
        ordering = ["-start_date"]


class ShippingFee(models.Model):
    """送料設定"""

    fee = models.IntegerField(verbose_name="送料(円)")
    free_shipping_threshold = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="送料無料の金額(円)",
        help_text="この金額以上で送料無料。設定しない場合は常に送料がかかります",
    )
    is_active = models.BooleanField(default=True, verbose_name="有効")
    start_date = models.DateField(verbose_name="適用開始日")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="登録日時")

    def __str__(self):
        if self.free_shipping_threshold:
            return f"送料: {self.fee}円 ({self.free_shipping_threshold}円以上で無料)"
        return f"送料: {self.fee}円"

    @classmethod
    def get_current_fee(cls):
        """現在有効な送料設定を取得"""
        from django.utils import timezone

        today = timezone.now().date()

        shipping = (
            cls.objects.filter(is_active=True, start_date__lte=today)
            .order_by("-start_date")
            .first()
        )

        if shipping:
            return shipping
        # デフォルト設定
        return cls(fee=800, free_shipping_threshold=None)

    @classmethod
    def calculate_shipping_fee(cls, subtotal):
        """小計に基づいて送料を計算"""
        shipping = cls.get_current_fee()

        if (
            shipping.free_shipping_threshold
            and subtotal >= shipping.free_shipping_threshold
        ):
            return 0
        return shipping.fee

    class Meta:
        db_table = "shipping_fees"
        verbose_name = "送料設定"
        verbose_name_plural = "送料設定"
        ordering = ["-start_date"]


class TeaProduct(models.Model):
    """お茶商品（重量別価格）"""

    WEIGHT_CHOICES = [
        (100, "100g"),
        (200, "200g"),
        (300, "300g"),
    ]

    tea = models.ForeignKey(
        Tea, on_delete=models.CASCADE, related_name="products", verbose_name="お茶"
    )
    weight = models.IntegerField(choices=WEIGHT_CHOICES, verbose_name="重量(g)")
    price = models.IntegerField(verbose_name="価格(円・税抜)")
    stock = models.IntegerField(default=0, verbose_name="在庫数")
    is_available = models.BooleanField(default=True, verbose_name="販売中")

    def __str__(self):
        return f"{self.tea.name} - {self.weight}g"

    def get_price_with_tax(self):
        """税込価格を取得"""
        tax_rate = TaxRate.get_current_rate()
        return int(self.price * (1 + tax_rate / 100))

    class Meta:
        db_table = "tea_products"
        verbose_name = "お茶商品"
        verbose_name_plural = "お茶商品"
        unique_together = ["tea", "weight"]
        ordering = ["tea", "weight"]


class Order(models.Model):
    """注文"""

    STATUS_CHOICES = [
        ("pending", "支払い待ち"),
        ("paid", "支払い完了"),
        ("processing", "処理中"),
        ("shipped", "発送済み"),
        ("delivered", "配達完了"),
        ("cancelled", "キャンセル"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="ユーザー",
    )
    order_number = models.CharField(max_length=50, unique=True, verbose_name="注文番号")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="ステータス",
    )

    # 金額
    subtotal = models.IntegerField(verbose_name="小計(税抜)")
    tax_amount = models.IntegerField(verbose_name="消費税額")
    shipping_fee = models.IntegerField(verbose_name="送料")
    total_amount = models.IntegerField(verbose_name="合計金額(税込)")

    # 税率（注文時の税率を保存）
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name="適用税率(%)"
    )

    # Stripe関連
    stripe_checkout_session_id = models.CharField(
        max_length=200, blank=True, verbose_name="Stripe Checkout Session ID"
    )
    stripe_payment_intent_id = models.CharField(
        max_length=200, blank=True, verbose_name="Stripe Payment Intent ID"
    )

    # 配送先情報
    shipping_name = models.CharField(max_length=100, verbose_name="配送先名")
    shipping_postal_code = models.CharField(max_length=8, verbose_name="郵便番号")
    shipping_address = models.CharField(max_length=200, verbose_name="住所")
    shipping_phone = models.CharField(max_length=20, verbose_name="電話番号")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="注文日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return f"注文 {self.order_number}"

    def calculate_amounts(self):
        """金額を計算"""
        # 小計（税抜）
        self.subtotal = sum(item.price * item.quantity for item in self.items.all())

        # 税率取得
        self.tax_rate = TaxRate.get_current_rate()

        # 消費税額
        self.tax_amount = int(self.subtotal * self.tax_rate / 100)

        # 送料
        self.shipping_fee = ShippingFee.calculate_shipping_fee(self.subtotal)

        # 合計金額
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_fee

    class Meta:
        db_table = "orders"
        verbose_name = "注文"
        verbose_name_plural = "注文"
        ordering = ["-created_at"]


class OrderItem(models.Model):
    """注文明細"""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="注文"
    )
    product = models.ForeignKey(
        TeaProduct, on_delete=models.PROTECT, verbose_name="商品"
    )
    quantity = models.IntegerField(default=1, verbose_name="数量")
    price = models.IntegerField(verbose_name="単価(税抜)")

    def __str__(self):
        return f"{self.order.order_number} - {self.product}"

    @property
    def subtotal(self):
        """小計（税抜）"""
        return self.price * self.quantity

    @property
    def subtotal_with_tax(self):
        """小計（税込）"""
        return int(self.subtotal * (1 + self.order.tax_rate / 100))

    class Meta:
        db_table = "order_items"
        verbose_name = "注文明細"
        verbose_name_plural = "注文明細"


class Cart(models.Model):
    """カート"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name="ユーザー",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")

    def __str__(self):
        return f"{self.user.email}のカート"

    @property
    def subtotal(self):
        """小計（税抜）"""
        return sum(item.subtotal for item in self.items.all())

    @property
    def tax_amount(self):
        """消費税額"""
        tax_rate = TaxRate.get_current_rate()
        return int(self.subtotal * tax_rate / 100)

    @property
    def shipping_fee(self):
        """送料"""
        return ShippingFee.calculate_shipping_fee(self.subtotal)

    @property
    def total_amount(self):
        """合計金額（税込）"""
        return self.subtotal + self.tax_amount + self.shipping_fee

    @property
    def item_count(self):
        """商品点数"""
        return sum(item.quantity for item in self.items.all())

    class Meta:
        db_table = "carts"
        verbose_name = "カート"
        verbose_name_plural = "カート"


class CartItem(models.Model):
    """カート明細"""

    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items", verbose_name="カート"
    )
    product = models.ForeignKey(
        TeaProduct, on_delete=models.CASCADE, verbose_name="商品"
    )
    quantity = models.IntegerField(default=1, verbose_name="数量")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="追加日時")

    def __str__(self):
        return f"{self.cart.user.email} - {self.product}"

    @property
    def subtotal(self):
        """小計（税抜）"""
        return self.product.price * self.quantity

    @property
    def subtotal_with_tax(self):
        """小計（税込）"""
        tax_rate = TaxRate.get_current_rate()
        return int(self.subtotal * (1 + tax_rate / 100))

    class Meta:
        db_table = "cart_items"
        verbose_name = "カート明細"
        verbose_name_plural = "カート明細"
        unique_together = ["cart", "product"]
