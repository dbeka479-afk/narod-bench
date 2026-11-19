from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("top/", views.top, name="top"),
    path("r/<int:pk>/", views.detail, name="detail"),
    path("api/save/", views.api_save, name="api_save"),
]
