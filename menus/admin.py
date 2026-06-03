from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from mptt.forms import MPTTAdminForm
from parler.admin import TranslatableAdmin, TranslatableModelForm

from .models import Menu, MenuItem


@admin.register(Menu)
class MenuAdmin(TranslatableAdmin):
    list_display = ("current_title", "slug")
    search_fields = ("translations__title", "slug")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    @admin.display(description=_("Menu Title"))
    def current_title(self, obj):
        return obj.safe_translation_getter("title", any_language=True) or obj.slug


class MenuItemAdminForm(MPTTAdminForm, TranslatableModelForm):
    pass


@admin.register(MenuItem)
class MenuItemAdmin(TranslatableAdmin):
    form = MenuItemAdminForm
    list_display = (
        "display_title",
        "menu",
        "parent",
        "link_type",
        "order",
        "visible_for_groups",
    )
    list_display_links = ("display_title",)
    list_filter = (
        "menu",
        "link_type",
        "allowed_groups",
    )
    list_editable = ("order",)
    search_fields = ("translations__title",)
    filter_horizontal = ("allowed_groups",)
    fields = (
        "menu",
        "parent",
        "title",
        "order",
        "allowed_groups",
        "link_type",
        "link_page",
        "link_category",
        "link_url",
        "post_list_type",
        "dynamic_items_limit",
        "icon_class",
    )

    class Media:
        js = ("menus/admin/js/hide_fields.js",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return (
            qs.select_related("menu", "parent", "link_page", "link_category")
            .prefetch_related("allowed_groups", "translations")
            .order_by("menu_id", "tree_id", "lft", "order", "id")
        )

    @admin.display(description=_("Menu Item"))
    def display_title(self, obj):
        indent = obj.level * 24
        title = obj.safe_translation_getter("title", any_language=True) or str(_("Untitled"))

        if obj.icon_class:
            return format_html(
                '<span style="display:inline-block; padding-left:{}px;">'
                '<i class="{}" style="margin-right:6px;"></i>{}'
                "</span>",
                indent,
                obj.icon_class,
                title,
            )

        return format_html(
            '<span style="display:inline-block; padding-left:{}px;">{}</span>',
            indent,
            title,
        )

    @admin.display(description=_("Visible for"))
    def visible_for_groups(self, obj):
        groups = list(obj.allowed_groups.all())

        if not groups:
            return _("Everyone")

        return ", ".join(group.name for group in groups)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)

        if db_field.name == "link_type":
            formfield.widget.attrs["class"] = (
                f"{formfield.widget.attrs.get('class', '')} admin-link-type-select"
            ).strip()

        return formfield
