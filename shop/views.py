from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.translation import gettext

from .models import Order


@login_required
def my_orders(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items", "items__book")
        .order_by("-created_at")
    )

    context = {
        "orders": orders,
        "breadcrumbs": [
            {"url": "/", "label": gettext("Home")},
            {"url": "", "label": gettext("My orders")},
        ],
        "title": gettext("My orders"),
        "meta_title": gettext("My orders"),
        "meta_description": gettext(
            "Review the orders you have created from the checkout flow."
        ),
    }

    return render(request, "shop/my_orders.html", context)
