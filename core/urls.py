from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('privacy/cookies/', views.cookie_preferences, name='cookie_preferences'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('checkout/', views.checkout_detail, name='checkout_detail'),
    path('checkout/create-order/', views.checkout_create_order, name='checkout_create_order'),
    path('checkout/order/<uuid:reference>/', views.checkout_order_pending, name='checkout_order_pending'),
    path('checkout/pay/', views.checkout_payment_placeholder, name='checkout_pay'),
]
