import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
class TestTeaList:
    """お茶一覧のテスト"""

    def test_product_list_authenticated(self, client, tea, product_100g):
        """未ログインでもお茶一覧を表示できる"""
        url = reverse("published_tea_list")
        response = client.get(url)
        assert response.status_code == 200
        assert tea in response.context["teas"]

    def test_product_list_excludes_unpublished(
        self, authenticated_client, tea, unpublished_tea, product_100g
    ):
        """未公開のお茶は表示されない"""
        url = reverse("published_tea_list")
        response = authenticated_client.get(url)
        assert tea in response.context["teas"]
        assert unpublished_tea not in response.context["teas"]
