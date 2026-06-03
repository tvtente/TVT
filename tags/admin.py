# File: tags/admin.py

from django.contrib import admin
from django.contrib.admin.options import IS_POPUP_VAR
from django.db.models import Count, Max, Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin
from .models import Tag, TagDailyMetric


TRANSLATION_FLOW_VAR = '_tag_translation_flow'

@admin.register(Tag)
class TagAdmin(TranslatableAdmin):
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
