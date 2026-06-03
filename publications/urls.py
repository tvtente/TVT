# File: publications/urls.py

from django.urls import path

from . import views


app_name = "publications"


urlpatterns = [
    path("", views.publication_list_view, name="publication_list"),
    path("<slug:slug>/", views.publication_detail_view, name="publication_detail"),
    path("<slug:slug>/document/", views.publication_document_view, name="publication_document"),
]