from django.urls import path
from . import views

app_name = "testimonials"

urlpatterns = [
    path('', views.testimonial_list_view, name='testimonial_list'),
]