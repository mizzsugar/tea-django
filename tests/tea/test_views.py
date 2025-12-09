import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

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
