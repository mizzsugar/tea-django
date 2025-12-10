from dataclasses import dataclass
from typing import Optional

from model.models import Cart, CartItem, TeaProduct, User


@dataclass
class CartOperationResult:
    """カート操作の結果"""

    success: bool
    message: str
    cart_item: Optional[CartItem] = None
    cart: Optional[Cart] = None


class CartService:
    """カート操作のビジネスロジック"""

    @staticmethod
    def get_or_create_cart(user: User) -> Cart:
        """ユーザーのカートを取得または作成"""
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    @staticmethod
    def add_to_cart(
        user: User, product: TeaProduct, quantity: int
    ) -> CartOperationResult:
        """
        カートに商品を追加

        Args:
            user: ユーザー
            product: 追加する商品
            quantity: 追加する数量

        Returns:
            CartOperationResult: 操作結果
        """
        cart = CartService.get_or_create_cart(user)

        # カートアイテムを取得または作成
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={"quantity": quantity}
        )

        if not created:
            # 既存のアイテムの場合は数量を追加
            new_quantity = cart_item.quantity + quantity

            # 在庫チェック
            if product.stock < new_quantity:
                return CartOperationResult(
                    success=False,
                    message=f"在庫が不足しています（在庫: {product.stock}個、カート内: {cart_item.quantity}個）",
                    cart=cart,
                )

            cart_item.quantity = new_quantity
            cart_item.save()

        return CartOperationResult(
            success=True,
            message="カートに追加しました",
            cart_item=cart_item,
            cart=cart,
        )

    @staticmethod
    def update_cart_item_quantity(
        cart_item: CartItem, quantity: int
    ) -> CartOperationResult:
        """
        カートアイテムの数量を更新

        Args:
            cart_item: 更新するカートアイテム
            quantity: 新しい数量

        Returns:
            CartOperationResult: 操作結果
        """
        # 在庫チェック
        if cart_item.product.stock < quantity:
            return CartOperationResult(
                success=False,
                message=f"在庫が不足しています（在庫: {cart_item.product.stock}個）",
                cart_item=cart_item,
            )

        cart_item.quantity = quantity
        cart_item.save()

        return CartOperationResult(
            success=True,
            message="数量を更新しました",
            cart_item=cart_item,
        )

    @staticmethod
    def remove_cart_item(cart_item: CartItem) -> CartOperationResult:
        """
        カートからアイテムを削除

        Args:
            cart_item: 削除するカートアイテム

        Returns:
            CartOperationResult: 操作結果
        """
        cart_item.delete()

        return CartOperationResult(
            success=True,
            message="カートから削除しました",
        )

    @staticmethod
    def clear_cart(user: User) -> CartOperationResult:
        """
        カートを空にする

        Args:
            user: ユーザー

        Returns:
            CartOperationResult: 操作結果
        """
        cart = Cart.objects.filter(user=user).first()
        if cart:
            cart.items.all().delete()

        return CartOperationResult(
            success=True,
            message="カートを空にしました",
            cart=cart,
        )

    @staticmethod
    def validate_cart_stock(cart: Cart) -> tuple[bool, list[str]]:
        """
        カート内の全商品の在庫をチェック

        Args:
            cart: チェックするカート

        Returns:
            tuple[bool, list[str]]: (全て在庫あり, エラーメッセージリスト)
        """
        errors = []
        cart_items = cart.items.select_related("product__tea").all()

        for item in cart_items:
            if item.product.stock < item.quantity:
                errors.append(f"{item.product}の在庫が不足しています")

        return len(errors) == 0, errors

