from django.urls import path

from . import views


app_name = "books"


urlpatterns = [
    path("", views.book_list_view, name="book_list"),
    path("cart/add/<int:book_id>/", views.cart_add_view, name="cart_add"),
    path("cart/remove/<int:book_id>/", views.cart_remove_view, name="cart_remove"),
    path("<slug:slug>/", views.book_detail_view, name="book_detail"),
    path("<slug:slug>/preview/", views.book_reader_view, name="book_reader"),
    path("<slug:slug>/document/", views.book_document_view, name="book_document"),
]
