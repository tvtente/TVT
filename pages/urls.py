# pages/urls.py
from django.urls import path
from . import views

app_name = 'pages' # <-- AÑADIMOS ESTA LÍNEA

urlpatterns = [
    path("directory/", views.pages_with_category_view, name="directory"),  # primero
    path("category/<slug:category_slug>/", views.pages_by_category_view, name="pages_by_category"),
    path("<slug:slug>/", views.page_detail_view, name="page_detail"),  # último
]