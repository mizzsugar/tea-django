import uuid
from dataclasses import dataclass
from typing import Optional

from django.db import transaction

from model.models import Cart, Order, OrderItem, User


@dataclass
class ShippingInfo:
    """配送情報"""

    name: str
    postal_code: str
    address: str
    phone: str


@dataclass
class OrderOperationResult:
    """注文操作の結果"""

    success: bool
    message: str
    order: Optional[Order] = None


class OrderService:
    """注文関連のビジネスロジック"""

    @staticmethod
    def generate_order_number() -> str:
        """ユニークな注文番号を生成"""
        return f"ORD-{uuid.uuid4().hex[:12].upper()}"

    @staticmethod
    @transaction.atomic
    def create_order_from_cart(
        user: User, cart: Cart, shipping_info: ShippingInfo
    ) -> OrderOperationResult:
        """
        カートから注文を作成

        Args:
            user: ユーザー
            cart: カート
            shipping_info: 配送情報

        Returns:
            OrderOperationResult: 操作結果
        """
        cart_items = cart.items.select_related("product__tea").all()

        if not cart_items:
            return OrderOperationResult(
                success=False,
                message="カートが空です",
            )

        # 在庫の最終チェック
        for item in cart_items:
            if item.product.stock < item.quantity:
                return OrderOperationResult(
                    success=False,
                    message=f"{item.product}の在庫が不足しています",
                )

        # 注文を作成（金額フィールドは後で設定）
        order = Order.objects.create(
            user=user,
            order_number=OrderService.generate_order_number(),
            shipping_name=shipping_info.name,
            shipping_postal_code=shipping_info.postal_code,
            shipping_address=shipping_info.address,
            shipping_phone=shipping_info.phone,
            # 一時的にデフォルト値を設定
            subtotal=0,
            tax_amount=0,
            shipping_fee=0,
            total_amount=0,
            tax_rate=0,
        )

        # 注文明細を作成
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price,  # 税抜価格を保存
            )

        # 金額を計算（注文明細作成後に実行）
        order.calculate_amounts()
        order.save()

        return OrderOperationResult(
            success=True,
            message="注文を作成しました",
            order=order,
        )

    @staticmethod
    @transaction.atomic
    def complete_payment(order: Order, payment_intent_id: str) -> OrderOperationResult:
        """
        支払い完了処理

        Args:
            order: 注文
            payment_intent_id: Stripe Payment Intent ID

        Returns:
            OrderOperationResult: 操作結果
        """
        if order.status == "paid":
            return OrderOperationResult(
                success=True,
                message="既に支払い完了しています",
                order=order,
            )

        # 注文ステータスを更新
        order.status = "paid"
        order.stripe_payment_intent_id = payment_intent_id
        order.save()

        # 在庫を減らす
        for item in order.items.all():
            product = item.product
            product.stock -= item.quantity
            product.save()

        return OrderOperationResult(
            success=True,
            message="支払いが完了しました",
            order=order,
        )

    @staticmethod
    def cancel_order(order: Order) -> OrderOperationResult:
        """
        注文をキャンセル

        Args:
            order: キャンセルする注文

        Returns:
            OrderOperationResult: 操作結果
        """
        if order.status in ["shipped", "delivered"]:
            return OrderOperationResult(
                success=False,
                message="発送済みの注文はキャンセルできません",
                order=order,
            )

        order.status = "cancelled"
        order.save()

        return OrderOperationResult(
            success=True,
            message="注文をキャンセルしました",
            order=order,
        )

    @staticmethod
    def get_user_orders(user: User):
        """
        ユーザーの注文一覧を取得

        Args:
            user: ユーザー

        Returns:
            QuerySet[Order]: 注文一覧
        """
        return Order.objects.filter(user=user).prefetch_related("items__product__tea")
