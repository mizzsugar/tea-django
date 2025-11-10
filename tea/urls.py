from django.urls import path

from tea import views

urlpatterns = [
    path("", views.published_tea_list, name="published_tea_list"),
]