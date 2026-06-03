from django.shortcuts import render
from .models import Testimonial
from django.utils.translation import gettext as _

def testimonial_list_view(request):
    testimonials = Testimonial.objects.filter(is_active=True).order_by('-created_at')
    
    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": "", "label": _("Testimonials")},
    ]

    return render(request, "testimonials/testimonial_list.html", {
        "testimonials": testimonials,
        "breadcrumbs": breadcrumbs,
    })