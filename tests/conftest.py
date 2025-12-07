import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from model.models import (
    Cart,
    CartItem,
    Order,
    OrderItem,
    ShippingFee,
    TaxRate,
    Tea,
    TeaProduct,
)

User = get_user_model()


@pytest.fixture
def user(db):
    """テストユーザー"""
    return User.objects.create_user(
        email="test@example.com", password="testpass123", nickname="テストユーザー"
    )


@pytest.fixture
def authenticated_client(client, user):
    """認証済みクライアント（デフォルトユーザー）"""

    def f(_user=None):
        if not _user:
            _user = user
        client.force_login(_user)
        client.user = _user
        return client

    return f


@pytest.fixture
def another_user(db):
    """別のテストユーザー"""
    return User.objects.create_user(
        email="another@example.com", password="testpass123", nickname="別のユーザー"
    )


@pytest.fixture
def tax_rate(db):
    """消費税率"""
    return TaxRate.objects.create(
        rate=Decimal("10.00"), start_date=timezone.now().date(), is_active=True
    )


@pytest.fixture
def shipping_fee(db):
    """送料設定"""
    return ShippingFee.objects.create(
        fee=800,
        start_date=timezone.now().date(),
        is_active=True,
        free_shipping_threshold=None,
    )


@pytest.fixture
def tea(db):
    """お茶マスタ"""
    return Tea.objects.create(
        name="川根朝摘み",
        steam_type="light",
        origin="川根本町",
        description="さわやかな一杯",
        caffeine_free=False,
        published_at=timezone.now(),
    )


@pytest.fixture
def unpublished_tea(db):
    """未公開のお茶"""
    return Tea.objects.create(
        name="未公開のお茶",
        steam_type="middle",
        origin="静岡",
        description="まだ公開していません",
        caffeine_free=False,
        published_at=datetime.datetime(2024, 4, 1, 10, 0, tzinfo=datetime.timezon.utc),
    )


@pytest.fixture
def product_100g(db, tea):
    """100g商品"""
    return TeaProduct.objects.create(
        tea=tea, weight=100, price=700, stock=50, is_available=True
    )


@pytest.fixture
def product_200g(db, tea):
    """200g商品"""
    return TeaProduct.objects.create(
        tea=tea, weight=200, price=1300, stock=30, is_available=True
    )


@pytest.fixture
def out_of_stock_product(db, tea):
    """在庫切れ商品"""
    return TeaProduct.objects.create(
        tea=tea, weight=300, price=1800, stock=0, is_available=True
    )


@pytest.fixture
def cart(db, user):
    """カート"""
    return Cart.objects.create(user=user)


@pytest.fixture
def cart_with_items(db, cart, product_100g, product_200g):
    """商品入りカート"""
    CartItem.objects.create(cart=cart, product=product_100g, quantity=2)
    CartItem.objects.create(cart=cart, product=product_200g, quantity=1)
    return cart


@pytest.fixture
def order(db, user, tax_rate, shipping_fee):
    """注文"""
    order = Order.objects.create(
        user=user,
        order_number="ORD-TEST123456",
        status="pending",
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
    return order


@pytest.fixture
def order_with_items(db, order, product_100g, product_200g):
    """商品入り注文"""
    OrderItem.objects.create(
        order=order, product=product_100g, quantity=2, price=product_100g.price
    )
    OrderItem.objects.create(
        order=order, product=product_200g, quantity=1, price=product_200g.price
    )
    order.calculate_amounts()
    order.save()
    return order
