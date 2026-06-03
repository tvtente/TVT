# File: gallery/urls.py
from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.gallery_view, name='gallery_view'),
    path('image/<int:pk>/', views.image_detail_view, name='image_detail'), # NEW: for individual image detail
]