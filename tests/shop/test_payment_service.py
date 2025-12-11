from unittest.mock import MagicMock, patch

import pytest
import stripe

from shop.services.payment_service import PaymentService


class TestPaymentServiceBuildLineItems:
    """PaymentService.build_line_items のテスト"""

    def test_builds_line_items_for_cart_items(self, cart_with_items, order_with_items):
        """カートアイテムからline_itemsを構築する"""
        cart_items = cart_with_items.items.select_related("product__tea").all()

        line_items = PaymentService.build_line_items(cart_items, order_with_items)

        # 商品2つ + 送料1つ = 3つのline_items
        assert len(line_items) == 3

        # 商品のline_itemsを確認
        product_items = [
            item
            for item in line_items
            if "送料" not in item["price_data"]["product_data"]["name"]
        ]
        assert len(product_items) == 2

    def test_includes_shipping_fee_when_present(
        self, cart_with_items, order_with_items
    ):
        """送料がある場合はline_itemsに含める"""
        cart_items = cart_with_items.items.select_related("product__tea").all()
        order_with_items.shipping_fee = 800

        line_items = PaymentService.build_line_items(cart_items, order_with_items)

        shipping_items = [
            item
            for item in line_items
            if item["price_data"]["product_data"]["name"] == "送料"
        ]
        assert len(shipping_items) == 1
        assert shipping_items[0]["price_data"]["unit_amount"] == 800

    def test_excludes_shipping_fee_when_zero(self, cart_with_items, order_with_items):
        """送料が0の場合はline_itemsに含めない"""
        cart_items = cart_with_items.items.select_related("product__tea").all()
        order_with_items.shipping_fee = 0

        line_items = PaymentService.build_line_items(cart_items, order_with_items)

        shipping_items = [
            item
            for item in line_items
            if item["price_data"]["product_data"]["name"] == "送料"
        ]
        assert len(shipping_items) == 0


class TestPaymentServiceCreateCheckoutSession:
    """PaymentService.create_checkout_session のテスト"""

    @patch("shop.services.payment_service.stripe.checkout.Session.create")
    def test_creates_checkout_session_successfully(
        self, mock_create, cart_with_items, order_with_items
    ):
        """Checkout Sessionを正常に作成できる"""
        mock_session = MagicMock()
        mock_session.id = "cs_test123"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_create.return_value = mock_session

        cart_items = cart_with_items.items.select_related("product__tea").all()

        result = PaymentService.create_checkout_session(
            order=order_with_items,
            cart_items=cart_items,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            customer_email="test@example.com",
        )

        assert result.success is True
        assert result.checkout_url == "https://checkout.stripe.com/test"
        assert result.session_id == "cs_test123"

    @patch("shop.services.payment_service.stripe.checkout.Session.create")
    def test_handles_stripe_error(self, mock_create, cart_with_items, order_with_items):
        """Stripeエラーを適切に処理する"""
        mock_create.side_effect = stripe.error.StripeError("Test error")

        cart_items = cart_with_items.items.select_related("product__tea").all()

        result = PaymentService.create_checkout_session(
            order=order_with_items,
            cart_items=cart_items,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            customer_email="test@example.com",
        )

        assert result.success is False
        assert "Stripeエラー" in result.message


class TestPaymentServiceVerifySessionPayment:
    """PaymentService.verify_session_payment のテスト"""

    @patch("shop.services.payment_service.stripe.checkout.Session.retrieve")
    def test_returns_true_when_paid(self, mock_retrieve):
        """支払い完了の場合はTrueを返す"""
        mock_session = MagicMock()
        mock_session.payment_status = "paid"
        mock_session.payment_intent = "pi_test123"
        mock_retrieve.return_value = mock_session

        is_paid, payment_intent_id = PaymentService.verify_session_payment("cs_test123")

        assert is_paid is True
        assert payment_intent_id == "pi_test123"

    @patch("shop.services.payment_service.stripe.checkout.Session.retrieve")
    def test_returns_false_when_not_paid(self, mock_retrieve):
        """未払いの場合はFalseを返す"""
        mock_session = MagicMock()
        mock_session.payment_status = "unpaid"
        mock_retrieve.return_value = mock_session

        is_paid, payment_intent_id = PaymentService.verify_session_payment("cs_test123")

        assert is_paid is False
        assert payment_intent_id is None

    @patch("shop.services.payment_service.stripe.checkout.Session.retrieve")
    def test_returns_false_on_error(self, mock_retrieve):
        """エラー時はFalseを返す"""
        mock_retrieve.side_effect = Exception("Test error")

        is_paid, payment_intent_id = PaymentService.verify_session_payment("cs_test123")

        assert is_paid is False
        assert payment_intent_id is None


@pytest.mark.django_db
class TestPaymentServiceProcessWebhook:
    """PaymentService.process_webhook のテスト"""

    @patch("shop.services.payment_service.stripe.Webhook.construct_event")
    def test_returns_400_for_invalid_payload(self, mock_construct):
        """不正なペイロードには400を返す"""
        mock_construct.side_effect = ValueError("Invalid payload")

        result = PaymentService.process_webhook(b"invalid", "sig")

        assert result.success is False
        assert result.status_code == 400

    @patch("shop.services.payment_service.stripe.Webhook.construct_event")
    def test_returns_400_for_invalid_signature(self, mock_construct):
        """不正な署名には400を返す"""
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "sig"
        )

        result = PaymentService.process_webhook(b"payload", "invalid_sig")

        assert result.success is False
        assert result.status_code == 400

    @patch("shop.services.payment_service.stripe.Webhook.construct_event")
    def test_processes_checkout_session_completed(
        self, mock_construct, order_with_items, product_100g, product_200g
    ):
        """checkout.session.completedイベントを処理する"""
        original_stock_100g = product_100g.stock
        original_stock_200g = product_200g.stock

        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"order_id": str(order_with_items.id)},
                    "payment_intent": "pi_test123",
                }
            },
        }

        result = PaymentService.process_webhook(b"payload", "sig")

        assert result.success is True
        assert result.status_code == 200

        order_with_items.refresh_from_db()
        assert order_with_items.status == "paid"
        assert order_with_items.stripe_payment_intent_id == "pi_test123"

        # 在庫が減っていることを確認
        product_100g.refresh_from_db()
        product_200g.refresh_from_db()
        assert product_100g.stock == original_stock_100g - 2
        assert product_200g.stock == original_stock_200g - 1

    @patch("shop.services.payment_service.stripe.Webhook.construct_event")
    def test_skips_already_paid_order(self, mock_construct, order_with_items):
        """既に支払い済みの注文は処理をスキップする"""
        order_with_items.status = "paid"
        order_with_items.save()

        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"order_id": str(order_with_items.id)},
                    "payment_intent": "pi_test123",
                }
            },
        }

        result = PaymentService.process_webhook(b"payload", "sig")

        assert result.success is True
        assert "Already processed" in result.message

    @patch("shop.services.payment_service.stripe.Webhook.construct_event")
    def test_handles_nonexistent_order(self, mock_construct):
        """存在しない注文IDの場合でも200を返す"""
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"order_id": "99999"},
                    "payment_intent": "pi_test123",
                }
            },
        }

        result = PaymentService.process_webhook(b"payload", "sig")

        # Stripeには200を返す（リトライを防ぐため）
        assert result.status_code == 200
        assert "Order not found" in result.message

    @patch("shop.services.payment_service.stripe.Webhook.construct_event")
    def test_handles_other_event_types(self, mock_construct):
        """他のイベントタイプは正常に処理される"""
        mock_construct.return_value = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test123",
                }
            },
        }

        result = PaymentService.process_webhook(b"payload", "sig")

        assert result.success is True
        assert result.status_code == 200

    @patch("shop.services.payment_service.stripe.Webhook.construct_event")
    def test_handles_missing_order_id_in_metadata(self, mock_construct):
        """metadataにorder_idがない場合も正常に処理される"""
        mock_construct.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {},
                    "payment_intent": "pi_test123",
                }
            },
        }

        result = PaymentService.process_webhook(b"payload", "sig")

        assert result.status_code == 200


class TestPaymentServiceBuildLineItemsEdgeCases:
    """PaymentService.build_line_items のエッジケーステスト"""

    def test_truncates_long_description(self, cart_with_items, order_with_items, tea):
        """長い説明文は100文字に切り詰められる"""
        # 長い説明文を設定
        tea.description = "あ" * 200
        tea.save()

        cart_items = cart_with_items.items.select_related("product__tea").all()
        line_items = PaymentService.build_line_items(cart_items, order_with_items)

        product_items = [
            item
            for item in line_items
            if "送料" not in item["price_data"]["product_data"]["name"]
        ]
        for item in product_items:
            description = item["price_data"]["product_data"]["description"]
            assert len(description) <= 100

    def test_handles_empty_description(self, cart_with_items, order_with_items, tea):
        """説明文が空の場合も正常に処理される"""
        tea.description = ""
        tea.save()

        cart_items = cart_with_items.items.select_related("product__tea").all()
        line_items = PaymentService.build_line_items(cart_items, order_with_items)

        product_items = [
            item
            for item in line_items
            if "送料" not in item["price_data"]["product_data"]["name"]
        ]
        assert len(product_items) > 0

    def test_includes_correct_product_name_format(
        self, cart_with_items, order_with_items
    ):
        """商品名が正しい形式で設定される"""
        cart_items = cart_with_items.items.select_related("product__tea").all()
        line_items = PaymentService.build_line_items(cart_items, order_with_items)

        product_items = [
            item
            for item in line_items
            if "送料" not in item["price_data"]["product_data"]["name"]
        ]

        for item in product_items:
            name = item["price_data"]["product_data"]["name"]
            # "お茶名 (重量g)" の形式
            assert "(" in name
            assert "g)" in name


class TestPaymentServiceCreateCheckoutSessionEdgeCases:
    """PaymentService.create_checkout_session のエッジケーステスト"""

    @patch("shop.services.payment_service.stripe.checkout.Session.create")
    def test_saves_session_id_to_order(
        self, mock_create, cart_with_items, order_with_items
    ):
        """セッションIDが注文に保存される"""
        mock_session = MagicMock()
        mock_session.id = "cs_saved_test123"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_create.return_value = mock_session

        cart_items = cart_with_items.items.select_related("product__tea").all()

        PaymentService.create_checkout_session(
            order=order_with_items,
            cart_items=cart_items,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            customer_email="test@example.com",
        )

        order_with_items.refresh_from_db()
        assert order_with_items.stripe_checkout_session_id == "cs_saved_test123"

    @patch("shop.services.payment_service.stripe.checkout.Session.create")
    def test_handles_general_exception(
        self, mock_create, cart_with_items, order_with_items
    ):
        """一般的な例外を適切に処理する"""
        mock_create.side_effect = Exception("Unexpected error")

        cart_items = cart_with_items.items.select_related("product__tea").all()

        result = PaymentService.create_checkout_session(
            order=order_with_items,
            cart_items=cart_items,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            customer_email="test@example.com",
        )

        assert result.success is False
        assert "エラーが発生しました" in result.message

    @patch("shop.services.payment_service.stripe.checkout.Session.create")
    def test_passes_correct_parameters_to_stripe(
        self, mock_create, cart_with_items, order_with_items
    ):
        """Stripeに正しいパラメータが渡される"""
        mock_session = MagicMock()
        mock_session.id = "cs_test123"
        mock_session.url = "https://checkout.stripe.com/test"
        mock_create.return_value = mock_session

        cart_items = cart_with_items.items.select_related("product__tea").all()

        PaymentService.create_checkout_session(
            order=order_with_items,
            cart_items=cart_items,
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
            customer_email="customer@example.com",
        )

        # Stripeに渡されたパラメータを確認
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["payment_method_types"] == ["card"]
        assert call_kwargs["mode"] == "payment"
        assert call_kwargs["success_url"] == "https://example.com/success"
        assert call_kwargs["cancel_url"] == "https://example.com/cancel"
        assert call_kwargs["customer_email"] == "customer@example.com"
        assert call_kwargs["metadata"]["order_id"] == order_with_items.id
