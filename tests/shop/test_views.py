from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from model.models import Cart, CartItem, Order, OrderItem

User = get_user_model()


@pytest.mark.django_db
class TestAddToCart:
    """カートに追加のテスト"""

    def test_add_to_cart_success(self, authenticated_client, product_100g):
        """認証済みユーザーが商品をカートに追加できる"""
        client = authenticated_client()
        url = reverse("shop:add_to_cart", args=[product_100g.id])
        response = client.post(url, {"quantity": 2})

        assert response.status_code == 302
        assert response.url == reverse("shop:cart")

        # カートに商品が追加されている
        cart = Cart.objects.get(user=client.user)
        cart_item = cart.items.get(product=product_100g)
        assert cart_item.quantity == 2

    def test_add_to_cart_ajax_success(self, authenticated_client, product_100g):
        """AJAXリクエストでカートに追加できる"""
        client = authenticated_client()
        url = reverse("shop:add_to_cart", args=[product_100g.id])
        response = client.post(
            url, {"quantity": 1}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cart_count"] == 1
        assert data["message"] == "カートに追加しました"

    def test_add_to_cart_increases_quantity(self, authenticated_client, product_100g):
        """既存のカートアイテムに数量を追加できる"""
        client = authenticated_client()
        # カートを作成
        cart = Cart.objects.create(user=client.user)
        CartItem.objects.create(cart=cart, product=product_100g, quantity=2)

        url = reverse("shop:add_to_cart", args=[product_100g.id])
        response = client.post(url, {"quantity": 3})

        assert response.status_code == 302
        cart_item = cart.items.get(product=product_100g)
        assert cart_item.quantity == 5  # 2 + 3

    def test_add_to_cart_exceeds_stock(self, authenticated_client, product_100g):
        """在庫を超える数量は追加できない"""
        client = authenticated_client()
        # カートを作成
        cart = Cart.objects.create(user=client.user)
        CartItem.objects.create(cart=cart, product=product_100g, quantity=48)

        url = reverse("shop:add_to_cart", args=[product_100g.id])
        # 在庫50に対して48 + 5 = 53
        response = client.post(
            url, {"quantity": 5}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "在庫が不足しています" in data["error"]

    def test_add_to_cart_requires_authentication(self, client, product_100g):
        """未認証ユーザーはログインページにリダイレクトされる"""
        url = reverse("shop:add_to_cart", args=[product_100g.id])
        response = client.post(url, {"quantity": 1})

        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_add_to_cart_invalid_quantity(self, authenticated_client, product_100g):
        """無効な数量でエラーになる"""
        client = authenticated_client()
        url = reverse("shop:add_to_cart", args=[product_100g.id])
        response = client.post(
            url, {"quantity": 0}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_add_to_cart_unavailable_product(self, authenticated_client, tea):
        """販売停止中の商品は追加できない"""
        from model.models import TeaProduct

        product = TeaProduct.objects.create(
            tea=tea, weight=100, price=700, stock=50, is_available=False
        )
        client = authenticated_client()
        url = reverse("shop:add_to_cart", args=[product.id])
        response = client.post(url, {"quantity": 1})

        assert response.status_code == 404


@pytest.mark.django_db
class TestCartView:
    """カート表示のテスト"""

    def test_cart_view_empty(self, authenticated_client):
        """空のカートが表示される"""
        client = authenticated_client()
        url = reverse("shop:cart")
        response = client.get(url)

        assert response.status_code == 200
        assert "cart" in response.context
        assert response.context["cart"].items.count() == 0

    def test_cart_view_with_items(self, authenticated_client, cart_with_items):
        """商品入りカートが表示される"""
        client = authenticated_client()
        url = reverse("shop:cart")
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["cart"].items.count() == 2

    def test_cart_view_requires_authentication(self, client):
        """未認証ユーザーはログインページにリダイレクトされる"""
        url = reverse("shop:cart")
        response = client.get(url)

        assert response.status_code == 302
        assert "/accounts/login/" in response.url


@pytest.mark.django_db
class TestUpdateCartItem:
    """カートアイテム更新のテスト"""

    def test_update_cart_item_success(self, authenticated_client, cart_with_items):
        """カートアイテムの数量を更新できる"""
        client = authenticated_client()
        cart_item = cart_with_items.items.first()
        url = reverse("shop:update_cart_item", args=[cart_item.id])

        response = client.post(url, {"quantity": 5})

        assert response.status_code == 302
        cart_item.refresh_from_db()
        assert cart_item.quantity == 5

    def test_update_cart_item_exceeds_stock(self, authenticated_client, cart_with_items):
        """在庫を超える数量には更新できない"""
        client = authenticated_client()
        cart_item = cart_with_items.items.first()
        url = reverse("shop:update_cart_item", args=[cart_item.id])

        # 在庫50を超える数量
        response = client.post(url, {"quantity": 100})

        assert response.status_code == 302
        cart_item.refresh_from_db()
        # 数量は変更されない
        assert cart_item.quantity != 100

    def test_update_cart_item_requires_authentication(self, client, cart_with_items):
        """未認証ユーザーはログインページにリダイレクトされる"""
        cart_item = cart_with_items.items.first()
        url = reverse("shop:update_cart_item", args=[cart_item.id])
        response = client.post(url, {"quantity": 5})

        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_update_other_users_cart_item(
        self, authenticated_client, another_user, product_100g
    ):
        """他のユーザーのカートアイテムは更新できない"""
        # 別のユーザーのカートを作成
        other_cart = Cart.objects.create(user=another_user)
        other_cart_item = CartItem.objects.create(
            cart=other_cart, product=product_100g, quantity=2
        )

        client = authenticated_client()
        url = reverse("shop:update_cart_item", args=[other_cart_item.id])
        response = client.post(url, {"quantity": 5})

        assert response.status_code == 404


@pytest.mark.django_db
class TestRemoveCartItem:
    """カートからの削除テスト"""

    def test_remove_cart_item_success(self, authenticated_client, cart_with_items):
        """カートから商品を削除できる"""
        client = authenticated_client()
        cart_item = cart_with_items.items.first()
        item_id = cart_item.id
        url = reverse("shop:remove_cart_item", args=[item_id])

        response = client.post(url)

        assert response.status_code == 302
        assert not CartItem.objects.filter(id=item_id).exists()

    def test_remove_cart_item_requires_authentication(self, client, cart_with_items):
        """未認証ユーザーはログインページにリダイレクトされる"""
        cart_item = cart_with_items.items.first()
        url = reverse("shop:remove_cart_item", args=[cart_item.id])
        response = client.post(url)

        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_remove_other_users_cart_item(
        self, authenticated_client, another_user, product_100g
    ):
        """他のユーザーのカートアイテムは削除できない"""
        # 別のユーザーのカートを作成
        other_cart = Cart.objects.create(user=another_user)
        other_cart_item = CartItem.objects.create(
            cart=other_cart, product=product_100g, quantity=2
        )

        client = authenticated_client()
        url = reverse("shop:remove_cart_item", args=[other_cart_item.id])
        response = client.post(url)

        assert response.status_code == 404


@pytest.mark.django_db
class TestCheckout:
    """チェックアウトのテスト"""

    def test_checkout_get_with_items(
        self, authenticated_client, cart_with_items, tax_rate, shipping_fee
    ):
        """商品入りカートでチェックアウト画面が表示される"""
        client = authenticated_client()
        url = reverse("shop:checkout")
        response = client.get(url)

        assert response.status_code == 200
        assert "cart" in response.context
        assert "form" in response.context

    def test_checkout_empty_cart(self, authenticated_client):
        """空のカートではチェックアウトできない"""
        client = authenticated_client()
        # 空のカートを作成
        Cart.objects.create(user=client.user)
        url = reverse("shop:checkout")
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("shop:product_list")

    def test_checkout_no_cart(self, authenticated_client):
        """カートがない場合は404"""
        client = authenticated_client()
        url = reverse("shop:checkout")
        response = client.get(url)

        assert response.status_code == 404

    def test_checkout_out_of_stock(
        self, authenticated_client, cart, out_of_stock_product, tax_rate, shipping_fee
    ):
        """在庫切れ商品があるとカートにリダイレクトされる"""
        # 在庫切れ商品をカートに追加
        CartItem.objects.create(cart=cart, product=out_of_stock_product, quantity=1)

        client = authenticated_client()
        url = reverse("shop:checkout")
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("shop:cart")

    @patch("shop.views.stripe.checkout.Session.create")
    def test_checkout_post_success(
        self, mock_stripe, authenticated_client, cart_with_items, tax_rate, shipping_fee
    ):
        """チェックアウトフォーム送信でStripeセッションが作成される"""
        mock_stripe.return_value = MagicMock(
            id="cs_test_123", url="https://checkout.stripe.com/test"
        )

        client = authenticated_client()
        url = reverse("shop:checkout")
        response = client.post(
            url,
            {
                "shipping_name": "山田太郎",
                "shipping_postal_code": "123-4567",
                "shipping_address": "東京都渋谷区1-2-3",
                "shipping_phone": "090-1234-5678",
            },
        )

        assert response.status_code == 302
        assert response.url == "https://checkout.stripe.com/test"
        mock_stripe.assert_called_once()

        # 注文が作成されている
        order = Order.objects.get(user=client.user)
        assert order.shipping_name == "山田太郎"
        assert order.stripe_checkout_session_id == "cs_test_123"

    def test_checkout_requires_authentication(self, client):
        """未認証ユーザーはログインページにリダイレクトされる"""
        url = reverse("shop:checkout")
        response = client.get(url)

        assert response.status_code == 302
        assert "/accounts/login/" in response.url


@pytest.mark.django_db
class TestPaymentSuccess:
    """支払い成功のテスト"""

    @patch("shop.views.stripe.checkout.Session.retrieve")
    def test_payment_success(
        self, mock_stripe, authenticated_client, order_with_items, cart_with_items
    ):
        """支払い成功で注文ステータスが更新される"""
        mock_stripe.return_value = MagicMock(
            payment_status="paid", payment_intent="pi_test_123"
        )

        client = authenticated_client()
        url = reverse("shop:payment_success")
        response = client.get(
            url, {"session_id": "cs_test_123", "order_id": order_with_items.id}
        )

        assert response.status_code == 302
        assert response.url == reverse(
            "shop:order_detail", args=[order_with_items.id]
        )

        order_with_items.refresh_from_db()
        assert order_with_items.status == "paid"
        assert order_with_items.stripe_payment_intent_id == "pi_test_123"

    def test_payment_success_requires_authentication(self, client, order):
        """未認証ユーザーはログインページにリダイレクトされる"""
        url = reverse("shop:payment_success")
        response = client.get(url, {"session_id": "cs_test_123", "order_id": order.id})

        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_payment_success_other_users_order(
        self, authenticated_client, another_user, tax_rate, shipping_fee
    ):
        """他のユーザーの注文は表示できない"""
        # 別のユーザーの注文を作成
        other_order = Order.objects.create(
            user=another_user,
            order_number="ORD-OTHER123",
            shipping_name="他のユーザー",
            shipping_postal_code="123-4567",
            shipping_address="東京都渋谷区1-2-3",
            shipping_phone="090-1234-5678",
            subtotal=0,
            tax_amount=0,
            shipping_fee=0,
            total_amount=0,
            tax_rate=10,
        )

        client = authenticated_client()
        url = reverse("shop:payment_success")
        response = client.get(
            url, {"session_id": "cs_test_123", "order_id": other_order.id}
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestPaymentCancel:
    """支払いキャンセルのテスト"""

    def test_payment_cancel(self, authenticated_client, order):
        """支払いキャンセルで注文ステータスが更新される"""
        client = authenticated_client()
        url = reverse("shop:payment_cancel")
        response = client.get(url, {"order_id": order.id})

        assert response.status_code == 302
        assert response.url == reverse("shop:cart")

        order.refresh_from_db()
        assert order.status == "cancelled"

    def test_payment_cancel_requires_authentication(self, client, order):
        """未認証ユーザーはログインページにリダイレクトされる"""
        url = reverse("shop:payment_cancel")
        response = client.get(url, {"order_id": order.id})

        assert response.status_code == 302
        assert "/accounts/login/" in response.url


@pytest.mark.django_db
class TestStripeWebhook:
    """Stripe Webhookのテスト"""

    @patch("shop.views.stripe.Webhook.construct_event")
    def test_stripe_webhook_checkout_completed(
        self, mock_construct, client, order_with_items, product_100g, product_200g
    ):
        """checkout.session.completedイベントで注文が更新される"""
        initial_stock_100g = product_100g.stock
        initial_stock_200g = product_200g.stock

        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"order_id": str(order_with_items.id)},
                    "payment_intent": "pi_test_webhook",
                }
            },
        }

        url = reverse("shop:stripe_webhook")
        response = client.post(
            url,
            data=b"test_payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_signature",
        )

        assert response.status_code == 200

        order_with_items.refresh_from_db()
        assert order_with_items.status == "paid"
        assert order_with_items.stripe_payment_intent_id == "pi_test_webhook"

        # 在庫が減っている
        product_100g.refresh_from_db()
        product_200g.refresh_from_db()
        assert product_100g.stock == initial_stock_100g - 2  # quantity 2
        assert product_200g.stock == initial_stock_200g - 1  # quantity 1

    @patch("shop.views.stripe.Webhook.construct_event")
    def test_stripe_webhook_invalid_signature(self, mock_construct, client):
        """無効な署名でエラーになる"""
        import stripe

        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "sig_header"
        )

        url = reverse("shop:stripe_webhook")
        response = client.post(
            url,
            data=b"test_payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="invalid_signature",
        )

        assert response.status_code == 400

    @patch("shop.views.stripe.Webhook.construct_event")
    def test_stripe_webhook_invalid_payload(self, mock_construct, client):
        """無効なペイロードでエラーになる"""
        mock_construct.side_effect = ValueError("Invalid payload")

        url = reverse("shop:stripe_webhook")
        response = client.post(
            url,
            data=b"invalid_payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_signature",
        )

        assert response.status_code == 400


@pytest.mark.django_db
class TestOrderList:
    """注文履歴のテスト"""

    def test_order_list_empty(self, authenticated_client):
        """注文がない場合も表示される"""
        client = authenticated_client()
        url = reverse("shop:order_list")
        response = client.get(url)

        assert response.status_code == 200
        assert list(response.context["orders"]) == []

    def test_order_list_with_orders(self, authenticated_client, order_with_items):
        """注文履歴が表示される"""
        client = authenticated_client()
        url = reverse("shop:order_list")
        response = client.get(url)

        assert response.status_code == 200
        assert order_with_items in response.context["orders"]

    def test_order_list_only_own_orders(
        self, authenticated_client, order_with_items, another_user, tax_rate, shipping_fee
    ):
        """自分の注文のみ表示される"""
        # 別のユーザーの注文を作成
        other_order = Order.objects.create(
            user=another_user,
            order_number="ORD-OTHER456",
            shipping_name="他のユーザー",
            shipping_postal_code="123-4567",
            shipping_address="東京都渋谷区1-2-3",
            shipping_phone="090-1234-5678",
            subtotal=0,
            tax_amount=0,
            shipping_fee=0,
            total_amount=0,
            tax_rate=10,
        )

        client = authenticated_client()
        url = reverse("shop:order_list")
        response = client.get(url)

        assert order_with_items in response.context["orders"]
        assert other_order not in response.context["orders"]

    def test_order_list_requires_authentication(self, client):
        """未認証ユーザーはログインページにリダイレクトされる"""
        url = reverse("shop:order_list")
        response = client.get(url)

        assert response.status_code == 302
        assert "/accounts/login/" in response.url


@pytest.mark.django_db
class TestOrderDetail:
    """注文詳細のテスト"""

    def test_order_detail_success(self, authenticated_client, order_with_items):
        """注文詳細が表示される"""
        client = authenticated_client()
        url = reverse("shop:order_detail", args=[order_with_items.id])
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["order"] == order_with_items

    def test_order_detail_other_users_order(
        self, authenticated_client, another_user, tax_rate, shipping_fee
    ):
        """他のユーザーの注文は表示できない"""
        other_order = Order.objects.create(
            user=another_user,
            order_number="ORD-OTHER789",
            shipping_name="他のユーザー",
            shipping_postal_code="123-4567",
            shipping_address="東京都渋谷区1-2-3",
            shipping_phone="090-1234-5678",
            subtotal=0,
            tax_amount=0,
            shipping_fee=0,
            total_amount=0,
            tax_rate=10,
        )

        client = authenticated_client()
        url = reverse("shop:order_detail", args=[other_order.id])
        response = client.get(url)

        assert response.status_code == 404

    def test_order_detail_requires_authentication(self, client, order):
        """未認証ユーザーはログインページにリダイレクトされる"""
        url = reverse("shop:order_detail", args=[order.id])
        response = client.get(url)

        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_order_detail_not_found(self, authenticated_client):
        """存在しない注文は404"""
        client = authenticated_client()
        url = reverse("shop:order_detail", args=[99999])
        response = client.get(url)

        assert response.status_code == 404

