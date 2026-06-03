# File: testimonials/admin.py
from django.contrib import admin
from parler.admin import TranslatableAdmin
from .models import Testimonial

@admin.register(Testimonial)
class TestimonialAdmin(TranslatableAdmin):
    list_display = ('__str__', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')