# File: categories/admin.py
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.utils.translation import gettext, gettext_lazy as _
from django.utils.translation import ngettext
from mptt.admin import DraggableMPTTAdmin
from mptt.forms import MPTTAdminForm
from parler.admin import TranslatableAdmin, TranslatableModelForm

from .models import Category
from posts.models import Post


class CategoryAdminForm(MPTTAdminForm, TranslatableModelForm):
    pass


@admin.register(Category)
class CategoryAdmin(TranslatableAdmin, DraggableMPTTAdmin):
    form = CategoryAdminForm
    change_form_template = "admin/categories/category/change_form.html"
    delete_confirmation_template = "admin/categories/category/delete_confirmation.html"
    delete_selected_confirmation_template = (
        "admin/categories/category/delete_selected_confirmation.html"
    )
    list_display = (
        "tree_actions",
        "indented_title",
        "is_visible",
        "current_slug",
        "menu_icon_class",
    )
    list_display_links = ("indented_title",)
    list_filter = ("is_visible",)
    search_fields = (
        "translations__name",
        "translations__description",
        "translations__slug",
    )
    mptt_level_indent = 20

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """Expose the affected visible descendants to the confirmation UI."""
        extra_context = extra_context or {}
        extra_context["visible_descendant_names"] = []
        category = self.get_object(request, object_id) if object_id else None
        if category is not None:
            extra_context["visible_descendant_names"] = [
                descendant.safe_translation_getter("name", any_language=True)
                for descendant in category.get_descendants().filter(is_visible=True)
            ]
        return super().changeform_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        """Hiding a parent also hides every visible category below it."""
        previously_visible = None
        if change and obj.pk:
            previously_visible = Category.objects.filter(pk=obj.pk).values_list(
                "is_visible",
                flat=True,
            ).first()

        super().save_model(request, obj, form, change)

        if previously_visible and not obj.is_visible:
            descendants = list(obj.get_descendants().filter(is_visible=True))
            if not descendants:
                return

            descendant_names = [
                descendant.safe_translation_getter("name", any_language=True)
                for descendant in descendants
            ]
            Category.objects.filter(pk__in=[descendant.pk for descendant in descendants]).update(
                is_visible=False
            )
            from categories.signals import clear_category_tree_cache

            clear_category_tree_cache(sender=Category, instance=obj)
            self.message_user(
                request,
                gettext(
                    "The following child categories were also hidden: %(categories)s."
                ) % {"categories": ", ".join(descendant_names)},
                level=messages.WARNING,
            )

    def get_prepopulated_fields(self, request, obj=None):
        return {"slug": ("name",)}

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            actions["delete_selected"] = (
                CategoryAdmin.delete_selected_with_impact_warning,
                "delete_selected",
                actions["delete_selected"][2],
            )
        return actions

    def _get_deletion_impact(self, queryset):
        category_ids = list(queryset.values_list("pk", flat=True))
        if not category_ids:
            return {
                "category_count": 0,
                "related_posts_count": 0,
                "uncategorized_posts_count": 0,
            }

        related_posts = Post.objects.filter(categories__in=category_ids).distinct()
        remaining_categories = Category.objects.exclude(pk__in=category_ids)
        uncategorized_posts_count = (
            related_posts.exclude(categories__in=remaining_categories).distinct().count()
        )

        return {
            "category_count": len(category_ids),
            "related_posts_count": related_posts.count(),
            "uncategorized_posts_count": uncategorized_posts_count,
        }

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        extra_context = extra_context or {}
        if obj is not None:
            extra_context["deletion_impact"] = self._get_deletion_impact(
                Category.objects.filter(pk=obj.pk)
            )
        return super().delete_view(request, object_id, extra_context=extra_context)

    @admin.action(
        permissions=["delete"],
        description=_("Delete selected %(verbose_name_plural)s"),
    )
    def delete_selected_with_impact_warning(self, request, queryset):
        (
            deletable_objects,
            model_count,
            perms_needed,
            protected,
        ) = self.get_deleted_objects(queryset, request)

        if request.POST.get("post") and not protected:
            if perms_needed:
                raise PermissionDenied
            n = len(queryset)
            if n:
                self.log_deletions(request, queryset)
                self.delete_queryset(request, queryset)
                self.message_user(
                    request,
                    _("Successfully deleted %(count)d %(items)s.")
                    % {
                        "count": n,
                        "items": ngettext("category", "categories", n),
                    },
                    level=messages.SUCCESS,
                )
            return None

        objects_name = str(self.model._meta.verbose_name_plural)
        if perms_needed or protected:
            title = _("Cannot delete %(name)s") % {"name": objects_name}
        else:
            title = _("Delete multiple objects")

        context = {
            **self.admin_site.each_context(request),
            "title": title,
            "subtitle": None,
            "objects_name": objects_name,
            "deletable_objects": [deletable_objects],
            "model_count": dict(model_count).items(),
            "queryset": queryset,
            "perms_lacking": perms_needed,
            "protected": protected,
            "opts": self.model._meta,
            "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            "media": self.media,
            "deletion_impact": self._get_deletion_impact(queryset),
        }

        request.current_app = self.admin_site.name
        return TemplateResponse(
            request,
            self.delete_selected_confirmation_template,
            context,
        )

    @admin.display(description=_("Slug"))
    def current_slug(self, obj):
        return obj.safe_translation_getter("slug", any_language=True) or ""
