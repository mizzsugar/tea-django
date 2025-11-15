from django.urls import path

from tea import views

urlpatterns = [
    path("", views.published_tea_list, name="published_tea_list"),
    path("teas/<int:tea_id>/", views.published_tea_detail, name="published_tea_detail"),
    path('signup/', views.signup_view, name='signup'),
    path('signin/', views.signin_view, name='signin'),
    path('signout/', views.signout_view, name='signout'),
    path('home/', views.home_view, name='home'),
    path("teas/<int:tea_id>/favorite/", views.add_favorite_tea, name="add_favorite_tea"),
    path("teas/<int:tea_id>/cancel_favorite/", views.cancel_favorite_tea, name="cancel_favorite_tea"),
]
