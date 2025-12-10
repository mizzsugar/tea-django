from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from model.models import Cart, CartItem, Order, TeaProduct

from .forms import AddToCartForm, CheckoutForm, UpdateCartItemForm
from .services.cart_service import CartService
from .services.order_service import OrderService, ShippingInfo
from .services.payment_service import PaymentService


@login_required
@require_POST
def add_to_cart(request, product_id):
    """カートに追加"""
    product = get_object_or_404(TeaProduct, id=product_id, is_available=True)
    form = AddToCartForm(request.POST, product=product)

    if form.is_valid():
        quantity = form.cleaned_data["quantity"]
        result = CartService.add_to_cart(request.user, product, quantity)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            if result.success:
                return JsonResponse(
                    {
                        "success": True,
                        "cart_count": result.cart.item_count,
                        "message": result.message,
                    }
                )
            return JsonResponse(
                {"success": False, "error": result.message}, status=400
            )

        if result.success:
            messages.success(request, result.message)
            return redirect("shop:cart")
        else:
            messages.error(request, result.message)
            return redirect("published_tea_detail", tea_id=product.tea.id)
    else:
        # バリデーションエラー
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(error)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "error": "、".join(error_messages)}, status=400
            )

        for error in error_messages:
            messages.error(request, error)
        return redirect("published_tea_detail", tea_id=product.tea.id)


@login_required
@require_GET
def cart_view(request):
    """カート表示"""
    cart = CartService.get_or_create_cart(request.user)
    cart_items = cart.items.select_related("product__tea").all()

    # 各カートアイテムに更新フォームを追加
    for item in cart_items:
        item.form = UpdateCartItemForm(cart_item=item)

    context = {
        "cart": cart,
        "cart_items": cart_items,
    }
    return render(request, "shop/cart.html", context)


@login_required
@require_POST
def update_cart_item(request, item_id):
    """カートアイテムの数量更新"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    form = UpdateCartItemForm(request.POST, cart_item=cart_item)

    if form.is_valid():
        quantity = form.cleaned_data["quantity"]
        result = CartService.update_cart_item_quantity(cart_item, quantity)

        if result.success:
            messages.success(request, result.message)
        else:
            messages.error(request, result.message)
    else:
        for error in form.errors.get("quantity", []):
            messages.error(request, error)

    return redirect("shop:cart")


@login_required
@require_POST
def remove_cart_item(request, item_id):
    """カートから削除"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    result = CartService.remove_cart_item(cart_item)
    messages.success(request, result.message)
    return redirect("shop:cart")


@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    """チェックアウト画面"""
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.select_related("product__tea").all()

    if not cart_items:
        messages.warning(request, "カートが空です")
        return redirect("shop:product_list")

    # 在庫チェック
    is_valid, errors = CartService.validate_cart_stock(cart)
    if not is_valid:
        for error in errors:
            messages.error(request, error)
        return redirect("shop:cart")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            return _process_checkout(request, cart, cart_items, form.cleaned_data)
    else:
        # セッションにデータがあれば初期値として設定
        initial_data = request.session.get("checkout_data", {})
        form = CheckoutForm(initial=initial_data)

    from django.conf import settings as django_settings

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "form": form,
        "STRIPE_PUBLIC_KEY": django_settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "shop/checkout.html", context)


def _process_checkout(request, cart, cart_items, checkout_data):
    """チェックアウト処理（内部関数）"""
    # 配送情報を作成
    shipping_info = ShippingInfo(
        name=checkout_data["shipping_name"],
        postal_code=checkout_data["shipping_postal_code"],
        address=checkout_data["shipping_address"],
        phone=checkout_data["shipping_phone"],
    )

    # 注文を作成
    order_result = OrderService.create_order_from_cart(
        request.user, cart, shipping_info
    )

    if not order_result.success:
        messages.error(request, order_result.message)
        return redirect("shop:checkout")

    order = order_result.order

    # Stripe Checkout Session を作成
    success_url = (
        request.build_absolute_uri(reverse("shop:payment_success"))
        + f"?session_id={{CHECKOUT_SESSION_ID}}&order_id={order.id}"
    )
    cancel_url = (
        request.build_absolute_uri(reverse("shop:payment_cancel"))
        + f"?order_id={order.id}"
    )

    payment_result = PaymentService.create_checkout_session(
        order=order,
        cart_items=cart_items,
        success_url=success_url,
        cancel_url=cancel_url,
        customer_email=request.user.email,
    )

    if not payment_result.success:
        # エラー時は注文を削除
        order.delete()
        messages.error(request, payment_result.message)
        return redirect("shop:checkout")

    # セッションデータをクリア
    if "checkout_data" in request.session:
        del request.session["checkout_data"]

    # Stripeの支払いページにリダイレクト
    return redirect(payment_result.checkout_url)


@login_required
@require_GET
def payment_success(request):
    """支払い成功"""
    session_id = request.GET.get("session_id")
    order_id = request.GET.get("order_id")

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Stripeのセッション情報を検証
    is_paid, payment_intent_id = PaymentService.verify_session_payment(session_id)

    if is_paid and payment_intent_id:
        # 支払い完了処理
        result = OrderService.complete_payment(order, payment_intent_id)

        if result.success:
            # カートを空にする
            CartService.clear_cart(request.user)
            messages.success(request, "お支払いが完了しました")
        else:
            messages.error(request, result.message)
    else:
        messages.error(request, "支払いの確認中にエラーが発生しました")

    return redirect("shop:order_detail", order_id=order.id)


@login_required
@require_GET
def payment_cancel(request):
    """支払いキャンセル"""
    order_id = request.GET.get("order_id")
    order = get_object_or_404(Order, id=order_id, user=request.user)

    result = OrderService.cancel_order(order)
    messages.warning(request, "お支払いがキャンセルされました")
    return redirect("shop:cart")


@csrf_exempt
def stripe_webhook(request):
    """Stripeからのwebhook"""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    result = PaymentService.process_webhook(payload, sig_header)
    return HttpResponse(status=result.status_code)


@login_required
@require_GET
def order_list(request):
    """注文履歴"""
    orders = OrderService.get_user_orders(request.user)

    context = {
        "orders": orders,
    }
    return render(request, "shop/order_list.html", context)


@login_required
@require_GET
def order_detail(request, order_id):
    """注文詳細"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    context = {
        "order": order,
    }
    return render(request, "shop/order_detail.html", context)
