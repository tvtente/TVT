# File: tags/admin.py

from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.contrib.admin.options import IS_POPUP_VAR
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max, Q
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _, ngettext
from parler.admin import TranslatableAdmin
from .models import Tag, TagDailyMetric
from posts.models import Post


TRANSLATION_FLOW_VAR = '_tag_translation_flow'

@admin.register(Tag)
class TagAdmin(TranslatableAdmin):
    delete_confirmation_template = "admin/tags/tag/delete_confirmation.html"
    delete_selected_confirmation_template = "admin/tags/tag/delete_selected_confirmation.html"
    list_display = (
        '__str__',
        'slug',
        'translated_slug',
        'click_count',
        'published_posts_count',
        'last_used_at',
    )
    list_filter = ('click_count',)
    readonly_fields = ('click_count',)
    search_fields = ['translations__label', 'slug', 'translations__translated_slug']
    ordering = ('-click_count', 'translations__label')
    actions = ('reset_selected_click_counts', 'reset_all_click_counts')

    def _popup_translation_url(self, obj, language_code):
        return (
            reverse('admin:tags_tag_change', args=[obj.pk])
            + f'?{IS_POPUP_VAR}=1&language={language_code}&{TRANSLATION_FLOW_VAR}=1'
        )

    def get_queryset(self, request):
        language = request.GET.get('language') or request.POST.get('language') or 'es'
        return (
            super().get_queryset(request)
            .language(language)
            .annotate(
                published_posts_total=Count(
                    'post_links__post',
                    filter=Q(post_links__post__status='published'),
                    distinct=True,
                ),
                last_used=Max('post_links__created_at'),
            )
            .distinct()
            .order_by('translations__label')
        )

    def response_add(self, request, obj, post_url_continue=None):
        if IS_POPUP_VAR in request.POST:
            return HttpResponseRedirect(self._popup_translation_url(obj, 'en'))
        return super().response_add(request, obj, post_url_continue=post_url_continue)

    def response_change(self, request, obj):
        if request.GET.get(TRANSLATION_FLOW_VAR):
            current_language = request.GET.get('language') or request.POST.get('language')
            if current_language == 'en':
                return HttpResponseRedirect(self._popup_translation_url(obj, 'ca'))
        return super().response_change(request, obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            actions["delete_selected"] = (
                TagAdmin.delete_selected_with_impact_warning,
                "delete_selected",
                actions["delete_selected"][2],
            )
        return actions

    def _get_deletion_impact(self, queryset):
        tag_ids = list(queryset.values_list("pk", flat=True))
        if not tag_ids:
            return {
                "tag_count": 0,
                "related_posts_count": 0,
                "untagged_posts_count": 0,
            }

        related_posts = Post.objects.filter(tags__in=tag_ids).distinct()
        remaining_tags = Tag.objects.exclude(pk__in=tag_ids)
        untagged_posts_count = (
            related_posts.exclude(tags__in=remaining_tags).distinct().count()
        )

        return {
            "tag_count": len(tag_ids),
            "related_posts_count": related_posts.count(),
            "untagged_posts_count": untagged_posts_count,
        }

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        extra_context = extra_context or {}
        if obj is not None:
            extra_context["deletion_impact"] = self._get_deletion_impact(
                Tag.objects.filter(pk=obj.pk)
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
                        "items": ngettext("tag", "tags", n),
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

    @admin.display(description=_("Published Posts"), ordering='published_posts_total')
    def published_posts_count(self, obj):
        return obj.published_posts_total

    @admin.display(description=_("Last Used"), ordering='last_used')
    def last_used_at(self, obj):
        return obj.last_used or "-"

    @admin.action(description=_("Reset click score for selected tags"))
    def reset_selected_click_counts(self, request, queryset):
        updated = queryset.update(click_count=0)
        self.message_user(
            request,
            _("Click score reset for %(count)d selected tags.") % {'count': updated},
        )

    @admin.action(description=_("Reset click score for all tags"))
    def reset_all_click_counts(self, request, queryset):
        updated = Tag.objects.update(click_count=0)
        TagDailyMetric.objects.all().delete()
        self.message_user(
            request,
            _("Click score reset for all %(count)d tags.") % {'count': updated},
        )


@admin.register(TagDailyMetric)
class TagDailyMetricAdmin(admin.ModelAdmin):
    list_display = ('tag', 'date', 'click_count')
    list_filter = ('date',)
    search_fields = ('tag__translations__label', 'tag__slug')
    date_hierarchy = 'date'
    ordering = ('-date', '-click_count')
