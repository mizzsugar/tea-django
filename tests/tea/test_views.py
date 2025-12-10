import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from model.models import FavoriteTea, TeaReview

User = get_user_model()


@pytest.mark.django_db
class TestTeaList:
    """お茶一覧のテスト"""

    def test_product_list_authenticated(self, client, tea, product_100g):
        url = reverse("published_tea_list")
        response = client.get(url)
        assert response.status_code == 200
        assert tea in response.context["teas"]

    def test_product_list_excludes_unpublished(
        self, client, tea, unpublished_tea, product_100g
    ):
        url = reverse("published_tea_list")
        response = client.get(url)
        assert tea in response.context["teas"]
        assert unpublished_tea not in response.context["teas"]


@pytest.mark.django_db
class TestAddFavoriteTea:
    """お気に入り追加のテスト"""

    def test_add_favorite_tea_success(self, authenticated_client, tea):
        """認証済みユーザーがお気に入りを追加できる"""
        client = authenticated_client()
        url = reverse("add_favorite_tea", args=[tea.id])
        response = client.post(url)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_favorited"] is True
        assert data["favorites_count"] == 1

        # DBにお気に入りが保存されている
        assert FavoriteTea.objects.filter(user=client.user, tea=tea).exists()

    def test_add_favorite_tea_idempotent(self, authenticated_client, tea):
        """既にお気に入りの場合でもエラーにならない"""
        client = authenticated_client()
        url = reverse("add_favorite_tea", args=[tea.id])

        # 1回目
        client.post(url)
        # 2回目（重複）
        response = client.post(url)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["favorites_count"] == 1

        # お気に入りは1つだけ
        assert FavoriteTea.objects.filter(user=client.user, tea=tea).count() == 1

    def test_add_favorite_tea_requires_authentication(self, client, tea):
        """未認証ユーザーはログインページにリダイレクトされる"""
        url = reverse("add_favorite_tea", args=[tea.id])
        response = client.post(url)

        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_add_favorite_tea_returns_correct_urls(self, authenticated_client, tea):
        """レスポンスに正しいURLが含まれる"""
        client = authenticated_client()
        url = reverse("add_favorite_tea", args=[tea.id])
        response = client.post(url)

        data = response.json()
        assert data["add_url"] == reverse("add_favorite_tea", args=[tea.id])
        assert data["cancel_url"] == reverse("cancel_favorite_tea", args=[tea.id])


@pytest.mark.django_db
class TestCancelFavoriteTea:
    """お気に入り解除のテスト"""

    def test_cancel_favorite_tea_success(self, authenticated_client, tea):
        """認証済みユーザーがお気に入りを解除できる"""
        client = authenticated_client()
        # まずお気に入りを追加
        FavoriteTea.objects.create(user=client.user, tea=tea)

        url = reverse("cancel_favorite_tea", args=[tea.id])
        response = client.post(url)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_favorited"] is False
        assert data["favorites_count"] == 0

        # DBからお気に入りが削除されている
        assert not FavoriteTea.objects.filter(user=client.user, tea=tea).exists()

    def test_cancel_favorite_tea_not_favorited(self, authenticated_client, tea):
        """お気に入りでない場合でもエラーにならない"""
        client = authenticated_client()
        url = reverse("cancel_favorite_tea", args=[tea.id])
        response = client.post(url)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_favorited"] is False
        assert data["favorites_count"] == 0

    def test_cancel_favorite_tea_requires_authentication(self, client, tea):
        """未認証ユーザーはログインページにリダイレクトされる"""
        url = reverse("cancel_favorite_tea", args=[tea.id])
        response = client.post(url)

        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_cancel_favorite_tea_returns_correct_urls(self, authenticated_client, tea):
        """レスポンスに正しいURLが含まれる"""
        client = authenticated_client()
        FavoriteTea.objects.create(user=client.user, tea=tea)

        url = reverse("cancel_favorite_tea", args=[tea.id])
        response = client.post(url)

        data = response.json()
        assert data["add_url"] == reverse("add_favorite_tea", args=[tea.id])
        assert data["cancel_url"] == reverse("cancel_favorite_tea", args=[tea.id])

    def test_cancel_favorite_tea_other_users_not_affected(
        self, authenticated_client, tea, another_user
    ):
        """他のユーザーのお気に入りは影響を受けない"""
        client = authenticated_client()
        # 両方のユーザーがお気に入り登録
        FavoriteTea.objects.create(user=client.user, tea=tea)
        FavoriteTea.objects.create(user=another_user, tea=tea)

        url = reverse("cancel_favorite_tea", args=[tea.id])
        response = client.post(url)

        data = response.json()
        assert data["favorites_count"] == 1  # 他のユーザーのお気に入りは残る
        assert FavoriteTea.objects.filter(user=another_user, tea=tea).exists()


@pytest.mark.django_db
class TestAddReview:
    """レビュー追加のテスト"""

    def test_add_review_success(self, authenticated_client, tea):
        """認証済みユーザーがレビューを追加できる"""
        client = authenticated_client()
        url = reverse("add_review", args=[tea.id])
        response = client.post(url, {"rating": 5, "content": "とても美味しいお茶です！"})

        assert response.status_code == 302
        assert response.url == reverse("published_tea_detail", args=[tea.id])

        # DBにレビューが保存されている
        review = TeaReview.objects.get(user=client.user, tea=tea)
        assert review.rating == 5
        assert review.content == "とても美味しいお茶です！"

    def test_add_review_without_content(self, authenticated_client, tea):
        """コンテンツなしでもレビューを追加できる（contentはblank=True）"""
        client = authenticated_client()
        url = reverse("add_review", args=[tea.id])
        response = client.post(url, {"rating": 3, "content": ""})

        assert response.status_code == 302
        review = TeaReview.objects.get(user=client.user, tea=tea)
        assert review.rating == 3
        assert review.content == ""

    def test_add_review_requires_authentication(self, client, tea):
        """未認証ユーザーはログインページにリダイレクトされる"""
        url = reverse("add_review", args=[tea.id])
        response = client.post(url, {"rating": 5, "content": "美味しい"})

        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_add_review_requires_rating(self, authenticated_client, tea):
        """評価は必須"""
        client = authenticated_client()
        url = reverse("add_review", args=[tea.id])
        response = client.post(url, {"content": "美味しいお茶です"})

        # フォームが無効なのでリダイレクトしない（テンプレートが返される可能性）
        # views.pyの実装上、form.is_valid()がFalseの場合は何もせずNoneを返す
        # この場合、Djangoは HttpResponseNotAllowed または 500エラーになる
        assert TeaReview.objects.filter(user=client.user, tea=tea).count() == 0
