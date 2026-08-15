from django.urls import path
from .views import meta_instagram_webhook

urlpatterns = [
    path("meta/instagram/", meta_instagram_webhook, name="meta-instagram-webhook"),
]
