from django.urls import path

from . import views


app_name = "notebooks"


urlpatterns = [
    path("", views.notebook_list_view, name="notebook_list"),
    path("<slug:slug>/", views.notebook_detail_view, name="notebook_detail"),
]

