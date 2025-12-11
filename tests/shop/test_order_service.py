import pytest

from model.models import Order
from shop.services.order_service import OrderService, ShippingInfo


@pytest.fixture
def shipping_info():
    """配送情報"""
    return ShippingInfo(
        name="山田太郎",
        postal_code="123-4567",
        address="東京都渋谷区1-2-3",
        phone="090-1234-5678",
    )


class TestOrderServiceGenerateOrderNumber:
    """OrderService.generate_order_number のテスト"""

    def test_generates_order_number_with_correct_format(self):
        """正しい形式の注文番号を生成する"""
        order_number = OrderService.generate_order_number()

        assert order_number.startswith("ORD-")
        assert len(order_number) == 16  # "ORD-" + 12文字

    def test_generates_unique_order_numbers(self):
        """ユニークな注文番号を生成する"""
        numbers = {OrderService.generate_order_number() for _ in range(100)}
        assert len(numbers) == 100


class TestOrderServiceCreateOrderFromCart:
    """OrderService.create_order_from_cart のテスト"""

    def test_creates_order_from_cart_successfully(
        self, user, cart_with_items, shipping_info, tax_rate, shipping_fee
    ):
        """カートから注文を正常に作成できる"""
        result = OrderService.create_order_from_cart(
            user, cart_with_items, shipping_info
        )

        assert result.success is True
        assert result.order is not None
        assert result.order.user == user
        assert result.order.status == "pending"
        assert result.order.items.count() == 2

    def test_fails_when_cart_is_empty(self, user, cart, shipping_info):
        """カートが空の場合はエラーを返す"""
        result = OrderService.create_order_from_cart(user, cart, shipping_info)

        assert result.success is False
        assert "カートが空です" in result.message

    def test_calculates_amounts_correctly(
        self, user, cart_with_items, shipping_info, tax_rate, shipping_fee
    ):
        """金額が正しく計算される"""
        result = OrderService.create_order_from_cart(
            user, cart_with_items, shipping_info
        )

        order = result.order
        # 700円×2 + 1300円×1 = 2700円（税抜）
        assert order.subtotal == 2700
        # 消費税 10% = 270円
        assert order.tax_amount == 270
        # 送料 800円
        assert order.shipping_fee == 800
        # 合計 = 2700 + 270 + 800 = 3770円
        assert order.total_amount == 3770

    def test_stores_shipping_info_correctly(
        self, user, cart_with_items, shipping_info, tax_rate, shipping_fee
    ):
        """配送情報が正しく保存される"""
        result = OrderService.create_order_from_cart(
            user, cart_with_items, shipping_info
        )

        order = result.order
        assert order.shipping_name == "山田太郎"
        assert order.shipping_postal_code == "123-4567"
        assert order.shipping_address == "東京都渋谷区1-2-3"
        assert order.shipping_phone == "090-1234-5678"


class TestOrderServiceCompletePayment:
    """OrderService.complete_payment のテスト"""

    def test_completes_payment_successfully(
        self, order_with_items, product_100g, product_200g
    ):
        """支払い完了処理が正常に行われる"""
        original_stock_100g = product_100g.stock
        original_stock_200g = product_200g.stock

        result = OrderService.complete_payment(order_with_items, "pi_test123")

        assert result.success is True
        order_with_items.refresh_from_db()
        assert order_with_items.status == "paid"
        assert order_with_items.stripe_payment_intent_id == "pi_test123"

        # 在庫が減っていることを確認
        product_100g.refresh_from_db()
        product_200g.refresh_from_db()
        assert product_100g.stock == original_stock_100g - 2
        assert product_200g.stock == original_stock_200g - 1

    def test_skips_already_paid_order(self, order_with_items):
        """既に支払い済みの注文は処理をスキップする"""
        order_with_items.status = "paid"
        order_with_items.save()

        result = OrderService.complete_payment(order_with_items, "pi_test123")

        assert result.success is True
        assert "既に支払い完了" in result.message


class TestOrderServiceCancelOrder:
    """OrderService.cancel_order のテスト"""

    def test_cancels_pending_order_successfully(self, order):
        """保留中の注文をキャンセルできる"""
        result = OrderService.cancel_order(order)

        assert result.success is True
        order.refresh_from_db()
        assert order.status == "cancelled"

    def test_cannot_cancel_shipped_order(self, order):
        """発送済みの注文はキャンセルできない"""
        order.status = "shipped"
        order.save()

        result = OrderService.cancel_order(order)

        assert result.success is False
        assert "発送済み" in result.message

    def test_cannot_cancel_delivered_order(self, order):
        """配達完了の注文はキャンセルできない"""
        order.status = "delivered"
        order.save()

        result = OrderService.cancel_order(order)

        assert result.success is False


class TestOrderServiceGetUserOrders:
    """OrderService.get_user_orders のテスト"""

    def test_returns_orders_for_user(self, user, order):
        """ユーザーの注文一覧を返す"""
        orders = OrderService.get_user_orders(user)

        assert orders.count() == 1
        assert orders.first() == order

    def test_returns_empty_for_user_without_orders(self, another_user):
        """注文がないユーザーには空のQuerySetを返す"""
        orders = OrderService.get_user_orders(another_user)

        assert orders.count() == 0

    def test_returns_multiple_orders_in_correct_order(
        self, user, tax_rate, shipping_fee
    ):
        """複数の注文を作成日時の降順で返す"""
        order1 = Order.objects.create(
            user=user,
            order_number="ORD-001",
            status="pending",
            shipping_name="テスト",
            shipping_postal_code="123-4567",
            shipping_address="東京都",
            shipping_phone="090-0000-0000",
            subtotal=1000,
            tax_amount=100,
            shipping_fee=800,
            total_amount=1900,
            tax_rate=10,
        )
        order2 = Order.objects.create(
            user=user,
            order_number="ORD-002",
            status="paid",
            shipping_name="テスト",
            shipping_postal_code="123-4567",
            shipping_address="東京都",
            shipping_phone="090-0000-0000",
            subtotal=2000,
            tax_amount=200,
            shipping_fee=800,
            total_amount=3000,
            tax_rate=10,
        )

        orders = OrderService.get_user_orders(user)

        assert orders.count() == 2
        # 作成日時の降順なので、order2が先
        assert list(orders) == [order2, order1]

    def test_does_not_return_other_users_orders(self, user, another_user, order):
        """他のユーザーの注文は返さない"""
        orders = OrderService.get_user_orders(another_user)

        assert orders.count() == 0


class TestOrderServiceCreateOrderFromCartEdgeCases:
    """OrderService.create_order_from_cart のエッジケーステスト"""

    def test_fails_when_stock_becomes_insufficient(
        self, user, cart, product_100g, shipping_info, tax_rate, shipping_fee
    ):
        """カート作成後に在庫が減った場合はエラーを返す"""
        from model.models import CartItem

        CartItem.objects.create(cart=cart, product=product_100g, quantity=10)

        # 在庫を減らす
        product_100g.stock = 5
        product_100g.save()

        result = OrderService.create_order_from_cart(user, cart, shipping_info)

        assert result.success is False
        assert "在庫が不足" in result.message

    def test_creates_order_items_with_correct_prices(
        self, user, cart_with_items, shipping_info, tax_rate, shipping_fee
    ):
        """注文明細に正しい価格が保存される"""
        result = OrderService.create_order_from_cart(
            user, cart_with_items, shipping_info
        )

        assert result.success is True
        order_items = result.order.items.all()
        assert order_items.count() == 2

        # 価格が正しく保存されているか確認
        for item in order_items:
            assert item.price == item.product.price


class TestOrderServiceCancelOrderEdgeCases:
    """OrderService.cancel_order のエッジケーステスト"""

    def test_can_cancel_paid_order(self, order):
        """支払い済みの注文はキャンセルできる"""
        order.status = "paid"
        order.save()

        result = OrderService.cancel_order(order)

        assert result.success is True
        order.refresh_from_db()
        assert order.status == "cancelled"

    def test_can_cancel_processing_order(self, order):
        """処理中の注文はキャンセルできる"""
        order.status = "processing"
        order.save()

        result = OrderService.cancel_order(order)

        assert result.success is True
        order.refresh_from_db()
        assert order.status == "cancelled"

    def test_returns_order_in_result(self, order):
        """結果に注文オブジェクトが含まれる"""
        result = OrderService.cancel_order(order)

        assert result.order is not None
        assert result.order.id == order.id


class TestOrderServiceCompletePaymentEdgeCases:
    """OrderService.complete_payment のエッジケーステスト"""

    def test_handles_order_without_items(self, order):
        """明細がない注文でもエラーにならない"""
        result = OrderService.complete_payment(order, "pi_test123")

        assert result.success is True
        order.refresh_from_db()
        assert order.status == "paid"

    def test_saves_payment_intent_id(self, order_with_items):
        """Payment Intent IDが正しく保存される"""
        result = OrderService.complete_payment(order_with_items, "pi_unique_test_id")

        assert result.success is True
        order_with_items.refresh_from_db()
        assert order_with_items.stripe_payment_intent_id == "pi_unique_test_id"
