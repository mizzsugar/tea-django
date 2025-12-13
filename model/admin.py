from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm

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
    User,
)

# Register your models here.
admin.site.register(Tea)
admin.site.register(FavoriteTea)
admin.site.register(TeaReview)


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm

    list_display = [
        "email",
        "username",
        "nickname",
        "tea_preference",
        "is_staff",
        "is_superuser",
        "date_joined",
    ]
    list_filter = ["is_staff", "is_superuser", "is_active", "tea_preference"]
    search_fields = ["email", "username", "nickname"]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("個人情報", {"fields": ("username", "nickname", "first_name", "last_name")}),
        ("お茶の好み", {"fields": ("tea_preference",)}),
        (
            "メール確認",
            {
                "fields": (
                    "is_email_verified",
                    "email_verification_token",
                    "email_verification_sent_at",
                )
            },
        ),
        (
            "権限",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("重要な日付", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "nickname",
                    "password1",
                    "password2",
                    "tea_preference",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    readonly_fields = (
        "last_login",
        "date_joined",
        "email_verification_token",
    )


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ["rate", "start_date", "is_active", "created_at"]
    list_filter = ["is_active", "start_date"]
    ordering = ["-start_date"]


@admin.register(ShippingFee)
class ShippingFeeAdmin(admin.ModelAdmin):
    list_display = [
        "fee",
        "free_shipping_threshold",
        "start_date",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "start_date"]
    ordering = ["-start_date"]


@admin.register(TeaProduct)
class TeaProductAdmin(admin.ModelAdmin):
    list_display = [
        "tea",
        "weight",
        "price",
        "get_price_with_tax",
        "stock",
        "is_available",
    ]
    list_filter = ["weight", "is_available"]
    search_fields = ["tea__name"]

    def get_price_with_tax(self, obj):
        return f"¥{obj.get_price_with_tax():,}"

    get_price_with_tax.short_description = "税込価格"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "quantity", "price", "subtotal"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "user",
        "status",
        "subtotal",
        "tax_amount",
        "shipping_fee",
        "total_amount",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["order_number", "user__email"]
    readonly_fields = [
        "order_number",
        "subtotal",
        "tax_amount",
        "shipping_fee",
        "total_amount",
        "tax_rate",
        "stripe_checkout_session_id",
        "stripe_payment_intent_id",
    ]
    inlines = [OrderItemInline]

    fieldsets = (
        ("注文情報", {"fields": ("order_number", "user", "status")}),
        (
            "金額",
            {
                "fields": (
                    "subtotal",
                    "tax_rate",
                    "tax_amount",
                    "shipping_fee",
                    "total_amount",
                )
            },
        ),
        (
            "配送先",
            {
                "fields": (
                    "shipping_name",
                    "shipping_postal_code",
                    "shipping_address",
                    "shipping_phone",
                )
            },
        ),
        (
            "Stripe情報",
            {"fields": ("stripe_checkout_session_id", "stripe_payment_intent_id")},
        ),
    )


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "item_count", "subtotal", "total_amount", "updated_at"]
    search_fields = ["user__email"]
    inlines = [CartItemInline]
