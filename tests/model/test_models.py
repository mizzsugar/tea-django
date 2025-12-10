from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from model.models import (
    Cart,
    CartItem,
    FavoriteTea,
    Order,
    OrderItem,
    ShippingFee,
    TaxRate,
    Tea,
    TeaProduct,
    TeaReview,
)

User = get_user_model()


@pytest.mark.django_db
class TestUserManager:
    """UserManagerのテスト"""

    def test_create_user_success(self):
        """一般ユーザーを作成できる"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert user.is_email_verified is False
        assert user.is_active is False
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_without_email_raises_error(self):
        """メールアドレスなしでユーザー作成するとエラー"""
        with pytest.raises(ValueError, match="メールアドレスは必須です"):
            User.objects.create_user(email="", password="testpass123")

    def test_create_user_normalizes_email(self):
        """メールアドレスが正規化される"""
        user = User.objects.create_user(
            email="Test@EXAMPLE.COM",
            password="testpass123",
        )
        assert user.email == "Test@example.com"

    def test_create_superuser_success(self):
        """スーパーユーザーを作成できる"""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
        )
        assert user.email == "admin@example.com"
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.is_email_verified is True
        assert user.is_active is True
        assert user.username == "admin"

    def test_create_superuser_with_username(self):
        """usernameを指定してスーパーユーザーを作成できる"""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            username="myadmin",
        )
        assert user.username == "myadmin"

    def test_create_superuser_without_is_staff_raises_error(self):
        """is_staff=Falseでスーパーユーザー作成するとエラー"""
        with pytest.raises(
            ValueError, match="スーパーユーザーはis_staff=Trueである必要があります"
        ):
            User.objects.create_superuser(
                email="admin@example.com",
                password="adminpass123",
                is_staff=False,
            )

    def test_create_superuser_without_is_superuser_raises_error(self):
        """is_superuser=Falseでスーパーユーザー作成するとエラー"""
        with pytest.raises(
            ValueError, match="スーパーユーザーはis_superuser=Trueである必要があります"
        ):
            User.objects.create_superuser(
                email="admin@example.com",
                password="adminpass123",
                is_superuser=False,
            )

    def test_generate_unique_username_with_duplicate(self):
        """同じemailプレフィックスのユーザーがいる場合は連番をつける"""
        User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
        )
        user2 = User.objects.create_superuser(
            email="admin@another.com",
            password="adminpass123",
        )
        assert user2.username == "admin1"


@pytest.mark.django_db
class TestUser:
    """Userモデルのテスト"""

    def test_str_with_nickname(self):
        """nicknameがある場合はnicknameを返す"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            nickname="テストユーザー",
        )
        assert str(user) == "テストユーザー"

    def test_str_with_username(self):
        """nicknameがなくusernameがある場合はusernameを返す"""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
        )
        user.nickname = ""
        user.save()
        assert str(user) == "admin"

    def test_str_with_email(self):
        """nicknameもusernameもない場合はemailを返す"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        assert str(user) == "test@example.com"

    def test_get_display_name_with_nickname(self):
        """nicknameがある場合はnicknameを返す"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            nickname="テストユーザー",
        )
        assert user.get_display_name() == "テストユーザー"

    def test_get_display_name_without_nickname(self):
        """nicknameがない場合はemailのプレフィックスを返す"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        assert user.get_display_name() == "test"

    def test_favorites_count_empty(self):
        """お気に入りがない場合は0"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        assert user.favorites_count == 0

    def test_favorites_count_with_favorites(self):
        """お気に入りがある場合はその数を返す"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea1 = Tea.objects.create(name="お茶1", steam_type="light")
        tea2 = Tea.objects.create(name="お茶2", steam_type="middle")
        FavoriteTea.objects.create(user=user, tea=tea1)
        FavoriteTea.objects.create(user=user, tea=tea2)
        assert user.favorites_count == 2

    def test_is_verification_token_valid_without_sent_at(self):
        """送信日時がない場合はTrue"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        user.email_verification_sent_at = None
        assert user.is_verification_token_valid() is True

    def test_is_verification_token_valid_within_24_hours(self):
        """24時間以内ならTrue"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        user.email_verification_sent_at = timezone.now() - timedelta(hours=23)
        assert user.is_verification_token_valid() is True

    def test_is_verification_token_valid_after_24_hours(self):
        """24時間を超えたらFalse"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        user.email_verification_sent_at = timezone.now() - timedelta(hours=25)
        assert user.is_verification_token_valid() is False

    def test_save_generates_username_for_staff(self):
        """staff userの場合はusernameが自動生成される"""
        user = User.objects.create_user(
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
            is_active=True,
        )
        assert user.username == "staff"

    def test_generate_unique_username_from_email_with_existing(self):
        """同じemailプレフィックスのユーザーがいる場合は連番をつける"""
        User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            is_staff=True,
        )
        user2 = User.objects.create_user(
            email="test@another.com",
            password="testpass123",
            is_staff=True,
        )
        assert user2.username == "test1"


@pytest.mark.django_db
class TestTaxRate:
    """TaxRateモデルのテスト"""

    def test_str(self):
        """__str__は税率と適用開始日を返す"""
        tax_rate = TaxRate.objects.create(
            rate=Decimal("10.00"),
            start_date=timezone.now().date(),
            is_active=True,
        )
        expected = f"10.00% (適用開始: {timezone.now().date()})"
        assert str(tax_rate) == expected

    def test_get_current_rate_returns_active_rate(self):
        """有効な税率が取得できる"""
        TaxRate.objects.create(
            rate=Decimal("10.00"),
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        assert TaxRate.get_current_rate() == Decimal("10.00")

    def test_get_current_rate_returns_latest(self):
        """複数の税率がある場合は最新を返す"""
        TaxRate.objects.create(
            rate=Decimal("8.00"),
            start_date=timezone.now().date() - timedelta(days=365),
            is_active=True,
        )
        TaxRate.objects.create(
            rate=Decimal("10.00"),
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        assert TaxRate.get_current_rate() == Decimal("10.00")

    def test_get_current_rate_ignores_future(self):
        """未来の税率は無視する"""
        TaxRate.objects.create(
            rate=Decimal("10.00"),
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        TaxRate.objects.create(
            rate=Decimal("15.00"),
            start_date=timezone.now().date() + timedelta(days=30),
            is_active=True,
        )
        assert TaxRate.get_current_rate() == Decimal("10.00")

    def test_get_current_rate_ignores_inactive(self):
        """非アクティブな税率は無視する"""
        TaxRate.objects.create(
            rate=Decimal("8.00"),
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        TaxRate.objects.create(
            rate=Decimal("15.00"),
            start_date=timezone.now().date() - timedelta(days=10),
            is_active=False,
        )
        assert TaxRate.get_current_rate() == Decimal("8.00")

    def test_get_current_rate_returns_default(self):
        """税率がない場合はデフォルト10%を返す"""
        assert TaxRate.get_current_rate() == 10.00


@pytest.mark.django_db
class TestShippingFee:
    """ShippingFeeモデルのテスト"""

    def test_str_without_threshold(self):
        """閾値なしの場合のstr"""
        shipping = ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date(),
            is_active=True,
            free_shipping_threshold=None,
        )
        assert str(shipping) == "送料: 800円"

    def test_str_with_threshold(self):
        """閾値ありの場合のstr"""
        shipping = ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date(),
            is_active=True,
            free_shipping_threshold=5000,
        )
        assert str(shipping) == "送料: 800円 (5000円以上で無料)"

    def test_get_current_fee_returns_active(self):
        """有効な送料設定が取得できる"""
        shipping = ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        result = ShippingFee.get_current_fee()
        assert result.fee == 800

    def test_get_current_fee_returns_latest(self):
        """複数の設定がある場合は最新を返す"""
        ShippingFee.objects.create(
            fee=1000,
            start_date=timezone.now().date() - timedelta(days=365),
            is_active=True,
        )
        ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        result = ShippingFee.get_current_fee()
        assert result.fee == 800

    def test_get_current_fee_returns_default(self):
        """送料設定がない場合はデフォルト値を返す"""
        result = ShippingFee.get_current_fee()
        assert result.fee == 800
        assert result.free_shipping_threshold is None

    def test_calculate_shipping_fee_normal(self):
        """通常の送料計算"""
        ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
            free_shipping_threshold=5000,
        )
        assert ShippingFee.calculate_shipping_fee(3000) == 800

    def test_calculate_shipping_fee_free_threshold_exact(self):
        """閾値ちょうどで送料無料"""
        ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
            free_shipping_threshold=5000,
        )
        assert ShippingFee.calculate_shipping_fee(5000) == 0

    def test_calculate_shipping_fee_free_threshold_over(self):
        """閾値超えで送料無料"""
        ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
            free_shipping_threshold=5000,
        )
        assert ShippingFee.calculate_shipping_fee(6000) == 0

    def test_calculate_shipping_fee_no_threshold(self):
        """閾値なしの場合は常に送料がかかる"""
        ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
            free_shipping_threshold=None,
        )
        assert ShippingFee.calculate_shipping_fee(10000) == 800


@pytest.mark.django_db
class TestTeaProduct:
    """TeaProductモデルのテスト"""

    def test_str(self):
        """__str__は「お茶名 - 重量g」形式を返す"""
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        assert str(product) == "静岡茶 - 100g"

    def test_get_price_with_tax(self):
        """税込価格を取得できる"""
        TaxRate.objects.create(
            rate=Decimal("10.00"),
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        assert product.get_price_with_tax() == 770  # 700 * 1.1 = 770

    def test_get_price_with_tax_default_rate(self):
        """税率がない場合はデフォルト10%"""
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        assert product.get_price_with_tax() == 770


@pytest.mark.django_db
class TestOrder:
    """Orderモデルのテスト"""

    def test_str(self):
        """__str__は注文番号を含む"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        order = Order.objects.create(
            user=user,
            order_number="ORD-123456",
            shipping_name="山田太郎",
            shipping_postal_code="123-4567",
            shipping_address="東京都渋谷区1-2-3",
            shipping_phone="090-1234-5678",
            subtotal=0,
            tax_amount=0,
            shipping_fee=0,
            total_amount=0,
            tax_rate=Decimal("10.00"),
        )
        assert str(order) == "注文 ORD-123456"

    def test_calculate_amounts(self):
        """金額計算が正しく行われる"""
        TaxRate.objects.create(
            rate=Decimal("10.00"),
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
            free_shipping_threshold=5000,
        )

        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=700)

        order = Order.objects.create(
            user=user,
            order_number="ORD-123456",
            shipping_name="山田太郎",
            shipping_postal_code="123-4567",
            shipping_address="東京都渋谷区1-2-3",
            shipping_phone="090-1234-5678",
            subtotal=0,
            tax_amount=0,
            shipping_fee=0,
            total_amount=0,
            tax_rate=Decimal("10.00"),
        )
        OrderItem.objects.create(order=order, product=product, quantity=2, price=700)

        order.calculate_amounts()

        assert order.subtotal == 1400  # 700 * 2
        assert order.tax_rate == Decimal("10.00")
        assert order.tax_amount == 140  # 1400 * 10%
        assert order.shipping_fee == 800  # 1400 < 5000
        assert order.total_amount == 2340  # 1400 + 140 + 800

    def test_calculate_amounts_free_shipping(self):
        """送料無料の場合の金額計算"""
        TaxRate.objects.create(
            rate=Decimal("10.00"),
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
            free_shipping_threshold=5000,
        )

        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=2500)

        order = Order.objects.create(
            user=user,
            order_number="ORD-123456",
            shipping_name="山田太郎",
            shipping_postal_code="123-4567",
            shipping_address="東京都渋谷区1-2-3",
            shipping_phone="090-1234-5678",
            subtotal=0,
            tax_amount=0,
            shipping_fee=0,
            total_amount=0,
            tax_rate=Decimal("10.00"),
        )
        OrderItem.objects.create(order=order, product=product, quantity=2, price=2500)

        order.calculate_amounts()

        assert order.subtotal == 5000  # 2500 * 2
        assert order.shipping_fee == 0  # 5000 >= 5000
        assert order.total_amount == 5500  # 5000 + 500 + 0


@pytest.mark.django_db
class TestOrderItem:
    """OrderItemモデルのテスト"""

    def test_str(self):
        """__str__は注文番号と商品名を返す"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        order = Order.objects.create(
            user=user,
            order_number="ORD-123456",
            shipping_name="山田太郎",
            shipping_postal_code="123-4567",
            shipping_address="東京都渋谷区1-2-3",
            shipping_phone="090-1234-5678",
            subtotal=0,
            tax_amount=0,
            shipping_fee=0,
            total_amount=0,
            tax_rate=Decimal("10.00"),
        )
        item = OrderItem.objects.create(
            order=order, product=product, quantity=2, price=700
        )
        assert str(item) == "ORD-123456 - 静岡茶 - 100g"

    def test_subtotal(self):
        """小計（税抜）が計算できる"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        order = Order.objects.create(
            user=user,
            order_number="ORD-123456",
            shipping_name="山田太郎",
            shipping_postal_code="123-4567",
            shipping_address="東京都渋谷区1-2-3",
            shipping_phone="090-1234-5678",
            subtotal=0,
            tax_amount=0,
            shipping_fee=0,
            total_amount=0,
            tax_rate=Decimal("10.00"),
        )
        item = OrderItem.objects.create(
            order=order, product=product, quantity=3, price=700
        )
        assert item.subtotal == 2100  # 700 * 3

    def test_subtotal_with_tax(self):
        """小計（税込）が計算できる"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        order = Order.objects.create(
            user=user,
            order_number="ORD-123456",
            shipping_name="山田太郎",
            shipping_postal_code="123-4567",
            shipping_address="東京都渋谷区1-2-3",
            shipping_phone="090-1234-5678",
            subtotal=0,
            tax_amount=0,
            shipping_fee=0,
            total_amount=0,
            tax_rate=Decimal("10.00"),
        )
        item = OrderItem.objects.create(
            order=order, product=product, quantity=3, price=700
        )
        assert item.subtotal_with_tax == 2310  # 2100 * 1.1



@pytest.mark.django_db
class TestCart:
    """Cartモデルのテスト"""

    def test_str(self):
        """__str__はユーザーのカートを返す"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        cart = Cart.objects.create(user=user)
        assert str(cart) == "test@example.comのカート"

    def test_subtotal_empty(self):
        """空のカートの小計は0"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        cart = Cart.objects.create(user=user)
        assert cart.subtotal == 0

    def test_subtotal_with_items(self):
        """商品がある場合の小計"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product1 = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        product2 = TeaProduct.objects.create(tea=tea, weight=200, price=1300)

        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product1, quantity=2)
        CartItem.objects.create(cart=cart, product=product2, quantity=1)

        assert cart.subtotal == 2700  # 700*2 + 1300*1

    def test_tax_amount(self):
        """消費税額が計算できる"""
        TaxRate.objects.create(
            rate=Decimal("10.00"),
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=1000)

        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=2)

        assert cart.tax_amount == 200  # 2000 * 10%

    def test_shipping_fee(self):
        """送料が計算できる"""
        ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
            free_shipping_threshold=5000,
        )
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=1000)

        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=2)

        assert cart.shipping_fee == 800  # 2000 < 5000

    def test_total_amount(self):
        """合計金額が計算できる"""
        TaxRate.objects.create(
            rate=Decimal("10.00"),
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        ShippingFee.objects.create(
            fee=800,
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
            free_shipping_threshold=5000,
        )
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=1000)

        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=2)

        assert cart.total_amount == 3000  # 2000 + 200 + 800

    def test_item_count(self):
        """商品点数が計算できる"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product1 = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        product2 = TeaProduct.objects.create(tea=tea, weight=200, price=1300)

        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product1, quantity=2)
        CartItem.objects.create(cart=cart, product=product2, quantity=3)

        assert cart.item_count == 5  # 2 + 3


@pytest.mark.django_db
class TestCartItem:
    """CartItemモデルのテスト"""

    def test_str(self):
        """__str__はユーザーと商品名を返す"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        cart = Cart.objects.create(user=user)
        item = CartItem.objects.create(cart=cart, product=product, quantity=2)
        assert str(item) == "test@example.com - 静岡茶 - 100g"

    def test_subtotal(self):
        """小計（税抜）が計算できる"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        cart = Cart.objects.create(user=user)
        item = CartItem.objects.create(cart=cart, product=product, quantity=3)
        assert item.subtotal == 2100  # 700 * 3

    def test_subtotal_with_tax(self):
        """小計（税込）が計算できる"""
        TaxRate.objects.create(
            rate=Decimal("10.00"),
            start_date=timezone.now().date() - timedelta(days=30),
            is_active=True,
        )
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        tea = Tea.objects.create(name="静岡茶", steam_type="middle")
        product = TeaProduct.objects.create(tea=tea, weight=100, price=700)
        cart = Cart.objects.create(user=user)
        item = CartItem.objects.create(cart=cart, product=product, quantity=3)
        assert item.subtotal_with_tax == 2310  # 2100 * 1.1

