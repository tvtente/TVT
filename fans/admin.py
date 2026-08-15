from django.contrib import admin
from .models import Fan, FanRule

@admin.register(Fan)
class FanAdmin(admin.ModelAdmin):
    list_display = ("display_name", "username", "platform", "profile_type", "is_vip")
    search_fields = ("display_name", "username", "platform_user_id")
    list_filter = ("platform", "profile_type", "is_vip")

@admin.register(FanRule)
class FanRuleAdmin(admin.ModelAdmin):
    list_display = ("fan", "tone", "human_review_required")
    search_fields = ("fan__display_name", "fan__username")
