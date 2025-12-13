from django.urls import path

from tea import views

urlpatterns = [
    path("", views.published_tea_list, name="published_tea_list"),
    path("teas/<int:tea_id>/", views.published_tea_detail, name="published_tea_detail"),
    path(
        "teas/<int:tea_id>/favorite/", views.add_favorite_tea, name="add_favorite_tea"
    ),
    path(
        "teas/<int:tea_id>/cancel_favorite/",
        views.cancel_favorite_tea,
        name="cancel_favorite_tea",
    ),
    path("teas/<int:tea_id>/review/", views.add_review, name="add_review"),
    # お茶の好み診断
    path("preference/", views.tea_preference_quiz, name="tea_preference_quiz"),
    path(
        "preference/result/", views.tea_preference_result, name="tea_preference_result"
    ),
]
