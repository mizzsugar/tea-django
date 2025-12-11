from model.models import Cart, CartItem
from shop.services.cart_service import CartService


class TestCartServiceGetOrCreateCart:
    """CartService.get_or_create_cart のテスト"""

    def test_creates_new_cart_for_user_without_cart(self, user):
        """カートがないユーザーには新しいカートを作成する"""
        assert not Cart.objects.filter(user=user).exists()

        cart = CartService.get_or_create_cart(user)

        assert cart is not None
        assert cart.user == user
        assert Cart.objects.filter(user=user).count() == 1

    def test_returns_existing_cart(self, user, cart):
        """既存のカートがあればそれを返す"""
        result = CartService.get_or_create_cart(user)

        assert result.id == cart.id
        assert Cart.objects.filter(user=user).count() == 1


class TestCartServiceAddToCart:
    """CartService.add_to_cart のテスト"""

    def test_adds_new_product_to_cart(self, user, product_100g):
        """新しい商品をカートに追加できる"""
        result = CartService.add_to_cart(user, product_100g, quantity=2)

        assert result.success is True
        assert result.message == "カートに追加しました"
        assert result.cart_item.product == product_100g
        assert result.cart_item.quantity == 2

    def test_increases_quantity_for_existing_product(self, user, cart, product_100g):
        """既存の商品は数量が加算される"""
        CartItem.objects.create(cart=cart, product=product_100g, quantity=1)

        result = CartService.add_to_cart(user, product_100g, quantity=2)

        assert result.success is True
        cart_item = CartItem.objects.get(cart=cart, product=product_100g)
        assert cart_item.quantity == 3

    def test_fails_when_stock_is_insufficient(self, user, cart, product_100g):
        """在庫不足の場合はエラーを返す"""
        # カートに49個入れる（在庫は50個）
        CartItem.objects.create(cart=cart, product=product_100g, quantity=49)

        # さらに2個追加しようとする
        result = CartService.add_to_cart(user, product_100g, quantity=2)

        assert result.success is False
        assert "在庫が不足" in result.message


class TestCartServiceUpdateCartItemQuantity:
    """CartService.update_cart_item_quantity のテスト"""

    def test_updates_quantity_successfully(self, cart, product_100g):
        """数量を正常に更新できる"""
        cart_item = CartItem.objects.create(cart=cart, product=product_100g, quantity=1)

        result = CartService.update_cart_item_quantity(cart_item, quantity=5)

        assert result.success is True
        assert result.message == "数量を更新しました"
        cart_item.refresh_from_db()
        assert cart_item.quantity == 5

    def test_fails_when_quantity_exceeds_stock(self, cart, product_100g):
        """在庫を超える数量は設定できない"""
        cart_item = CartItem.objects.create(cart=cart, product=product_100g, quantity=1)

        result = CartService.update_cart_item_quantity(cart_item, quantity=100)

        assert result.success is False
        assert "在庫が不足" in result.message


class TestCartServiceRemoveCartItem:
    """CartService.remove_cart_item のテスト"""

    def test_removes_cart_item_successfully(self, cart, product_100g):
        """カートアイテムを削除できる"""
        cart_item = CartItem.objects.create(cart=cart, product=product_100g, quantity=1)
        cart_item_id = cart_item.id

        result = CartService.remove_cart_item(cart_item)

        assert result.success is True
        assert result.message == "カートから削除しました"
        assert not CartItem.objects.filter(id=cart_item_id).exists()


class TestCartServiceClearCart:
    """CartService.clear_cart のテスト"""

    def test_clears_all_cart_items(self, user, cart_with_items):
        """カート内の全アイテムを削除する"""
        assert cart_with_items.items.count() == 2

        result = CartService.clear_cart(user)

        assert result.success is True
        assert cart_with_items.items.count() == 0

    def test_handles_user_without_cart(self, another_user):
        """カートがないユーザーでもエラーにならない"""
        result = CartService.clear_cart(another_user)

        assert result.success is True


class TestCartServiceValidateCartStock:
    """CartService.validate_cart_stock のテスト"""

    def test_returns_true_when_all_items_in_stock(self, cart_with_items):
        """全商品の在庫がある場合はTrueを返す"""
        is_valid, errors = CartService.validate_cart_stock(cart_with_items)

        assert is_valid is True
        assert errors == []

    def test_returns_false_with_errors_when_stock_insufficient(
        self, cart, out_of_stock_product
    ):
        """在庫不足の商品がある場合はFalseとエラーメッセージを返す"""
        CartItem.objects.create(cart=cart, product=out_of_stock_product, quantity=1)

        is_valid, errors = CartService.validate_cart_stock(cart)

        assert is_valid is False
        assert len(errors) == 1
        assert "在庫が不足" in errors[0]

    def test_returns_true_for_empty_cart(self, cart):
        """空のカートはTrueを返す"""
        is_valid, errors = CartService.validate_cart_stock(cart)

        assert is_valid is True
        assert errors == []

    def test_returns_multiple_errors_for_multiple_insufficient_items(
        self, cart, out_of_stock_product, product_100g
    ):
        """複数の在庫不足がある場合は複数のエラーを返す"""
        # 在庫切れ商品を追加
        CartItem.objects.create(cart=cart, product=out_of_stock_product, quantity=1)
        # 在庫を超える数量で追加
        product_100g.stock = 5
        product_100g.save()
        CartItem.objects.create(cart=cart, product=product_100g, quantity=10)

        is_valid, errors = CartService.validate_cart_stock(cart)

        assert is_valid is False
        assert len(errors) == 2


class TestCartServiceAddToCartEdgeCases:
    """CartService.add_to_cart のエッジケーステスト"""

    def test_adds_multiple_different_products(self, user, product_100g, product_200g):
        """異なる商品を複数追加できる"""
        result1 = CartService.add_to_cart(user, product_100g, quantity=1)
        result2 = CartService.add_to_cart(user, product_200g, quantity=2)

        assert result1.success is True
        assert result2.success is True
        assert result1.cart.items.count() == 2

    def test_add_exact_stock_amount(self, user, product_100g):
        """在庫数ぴったりまで追加できる"""
        result = CartService.add_to_cart(
            user, product_100g, quantity=product_100g.stock
        )

        assert result.success is True
        assert result.cart_item.quantity == product_100g.stock

    def test_returns_cart_in_result(self, user, product_100g):
        """結果にカートオブジェクトが含まれる"""
        result = CartService.add_to_cart(user, product_100g, quantity=1)

        assert result.cart is not None
        assert result.cart.user == user


class TestCartServiceUpdateCartItemEdgeCases:
    """CartService.update_cart_item_quantity のエッジケーステスト"""

    def test_updates_to_exact_stock_amount(self, cart, product_100g):
        """在庫数ぴったりに更新できる"""
        cart_item = CartItem.objects.create(cart=cart, product=product_100g, quantity=1)

        result = CartService.update_cart_item_quantity(
            cart_item, quantity=product_100g.stock
        )

        assert result.success is True
        cart_item.refresh_from_db()
        assert cart_item.quantity == product_100g.stock

    def test_updates_to_smaller_quantity(self, cart, product_100g):
        """数量を減らすことができる"""
        cart_item = CartItem.objects.create(
            cart=cart, product=product_100g, quantity=10
        )

        result = CartService.update_cart_item_quantity(cart_item, quantity=3)

        assert result.success is True
        cart_item.refresh_from_db()
        assert cart_item.quantity == 3
