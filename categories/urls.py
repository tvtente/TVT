# File: categories/urls.py
from django.urls import path
from . import views

app_name = 'categories'

urlpatterns = [
    # La URL raíz de esta app mostrará el árbol de categorías
    path('', views.category_tree_view, name='category_list'),
]