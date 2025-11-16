from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from tea.models import User, Tea, FavoriteTea, TeaReview

# Register your models here.
admin.site.register(Tea)
admin.site.register(FavoriteTea)
admin.site.register(TeaReview)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'nickname', 'is_staff', 'is_superuser', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['email', 'username', 'nickname']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('個人情報', {'fields': ('username', 'nickname', 'first_name', 'last_name')}),
        ('権限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要な日付', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'nickname', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )
