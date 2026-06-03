from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "book",
        "title_snapshot",
        "subtitle_snapshot",
        "quantity",
        "unit_price",
        "line_total",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "email",
        "status",
        "currency",
        "total",
        "created_at",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = ("reference", "email", "full_name")
    readonly_fields = ("reference", "created_at", "updated_at", "subtotal", "total")
    inlines = [OrderItemInline]

