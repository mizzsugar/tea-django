from dataclasses import dataclass
from typing import Optional

import stripe
from django.conf import settings
from django.db.models import QuerySet

from model.models import CartItem, Order

stripe.api_key = settings.STRIPE_SECRET_KEY


@dataclass
class PaymentSessionResult:
    """Stripe Session作成の結果"""

    success: bool
    message: str
    checkout_url: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class WebhookResult:
    """Webhook処理の結果"""

    success: bool
    message: str
    status_code: int = 200


class PaymentService:
    """Stripe決済関連のビジネスロジック"""

    @staticmethod
    def build_line_items(cart_items: QuerySet[CartItem], order: Order) -> list[dict]:
        """
        Stripe Checkout用のline_itemsを構築

        Args:
            cart_items: カートアイテム
            order: 注文

        Returns:
            list[dict]: Stripe line_items
        """
        line_items = []

        # 商品
        for cart_item in cart_items:
            description = ""
            if cart_item.product.tea.description:
                description = cart_item.product.tea.description[:100]

            line_items.append(
                {
                    "price_data": {
                        "currency": "jpy",
                        "product_data": {
                            "name": f"{cart_item.product.tea.name} ({cart_item.product.weight}g)",
                            "description": description,
                        },
                        "unit_amount": cart_item.product.get_price_with_tax(),  # 税込価格
                    },
                    "quantity": cart_item.quantity,
                }
            )

        # 送料
        if order.shipping_fee > 0:
            line_items.append(
                {
                    "price_data": {
                        "currency": "jpy",
                        "product_data": {
                            "name": "送料",
                        },
                        "unit_amount": order.shipping_fee,
                    },
                    "quantity": 1,
                }
            )

        return line_items

    @staticmethod
    def create_checkout_session(
        order: Order,
        cart_items: QuerySet[CartItem],
        success_url: str,
        cancel_url: str,
        customer_email: str,
    ) -> PaymentSessionResult:
        """
        Stripe Checkout Sessionを作成

        Args:
            order: 注文
            cart_items: カートアイテム
            success_url: 成功時のリダイレクトURL
            cancel_url: キャンセル時のリダイレクトURL
            customer_email: 顧客メールアドレス

        Returns:
            PaymentSessionResult: 操作結果
        """
        line_items = PaymentService.build_line_items(cart_items, order)

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=customer_email,
                metadata={
                    "order_id": order.id,
                },
            )

            # Checkout Session IDを保存
            order.stripe_checkout_session_id = checkout_session.id
            order.save()

            return PaymentSessionResult(
                success=True,
                message="Checkout Sessionを作成しました",
                checkout_url=checkout_session.url,
                session_id=checkout_session.id,
            )

        except stripe.error.StripeError as e:
            return PaymentSessionResult(
                success=False,
                message=f"Stripeエラー: {str(e)}",
            )
        except Exception as e:
            return PaymentSessionResult(
                success=False,
                message=f"エラーが発生しました: {str(e)}",
            )

    @staticmethod
    def verify_session_payment(session_id: str) -> tuple[bool, Optional[str]]:
        """
        Stripeセッションの支払い状態を確認

        Args:
            session_id: Stripe Session ID

        Returns:
            tuple[bool, Optional[str]]: (支払い完了か, Payment Intent ID)
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                return True, session.payment_intent
            return False, None
        except Exception:
            return False, None

    @staticmethod
    def process_webhook(payload: bytes, sig_header: str) -> WebhookResult:
        """
        Stripeからのwebhookを処理

        Args:
            payload: リクエストボディ
            sig_header: Stripe署名ヘッダー

        Returns:
            WebhookResult: 処理結果
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return WebhookResult(
                success=False,
                message="Invalid payload",
                status_code=400,
            )
        except stripe.error.SignatureVerificationError:
            return WebhookResult(
                success=False,
                message="Invalid signature",
                status_code=400,
            )

        # イベント処理
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            order_id = session["metadata"].get("order_id")

            if order_id:
                try:
                    order = Order.objects.get(id=order_id)

                    # 既に処理済みの場合はスキップ
                    if order.status == "paid":
                        return WebhookResult(
                            success=True,
                            message="Already processed",
                            status_code=200,
                        )

                    order.status = "paid"
                    order.stripe_payment_intent_id = session.get("payment_intent")
                    order.save()

                    # 在庫を減らす
                    for item in order.items.all():
                        product = item.product
                        product.stock -= item.quantity
                        product.save()

                except Order.DoesNotExist:
                    return WebhookResult(
                        success=False,
                        message="Order not found",
                        status_code=200,  # Stripeには200を返す
                    )

        return WebhookResult(
            success=True,
            message="Webhook processed",
            status_code=200,
        )
