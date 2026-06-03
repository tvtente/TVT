from django.urls import path

from . import views


app_name = "shop"


urlpatterns = [
    path("orders/", views.my_orders, name="my_orders"),
]
