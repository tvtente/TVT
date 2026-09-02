# File: posts/admin.py

import logging
import uuid
from datetime import timedelta

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.conf import settings
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Count, IntegerField, OuterRef, Subquery, Sum, Value, F
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html, format_html_join

from django_summernote.admin import SummernoteModelAdmin
from django_summernote.utils import get_config
from django_summernote.widgets import SummernoteInplaceWidget, SummernoteWidget
from parler.admin import TranslatableAdmin
from gallery.finalization import FinalizationError
from gallery.models import StagedUpload
from . import gallery_bridge
from .models import Post, PostDailyMetric, PostFavorite, PostPointAllocation
from comments.models import Comment
from tags.models import Tag, TaggedPost
from sources.models import Citation

logger = logging.getLogger(__name__)


@admin.register(PostPointAllocation)
class PostPointAllocationAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "date", "points", "post_author", "updated_at")
    list_filter = ("date", "post__author")
    search_fields = ("user__username", "post__translations__title", "post__translations__slug")
    autocomplete_fields = ("user", "post")
    date_hierarchy = "date"

    @admin.display(description=_("Post author"), ordering="post__author__username")
    def post_author(self, obj):
        return obj.post.author


@admin.register(PostFavorite)
class PostFavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "post_author", "created_at")
    list_filter = ("created_at", "post__author")
    search_fields = ("user__username", "post__translations__title", "post__translations__slug")
    autocomplete_fields = ("user", "post")
    date_hierarchy = "created_at"

    @admin.display(description=_("Post author"), ordering="post__author__username")
    def post_author(self, obj):
        return obj.post.author


class TaggedPostInline(admin.TabularInline):
    """
    🧩 Inline admin to manage tags assigned to a Post.
    Displays the related tag and optional relevance score.
    """
    model = TaggedPost
    extra = 1
    fields = ('tag', 'relevance_score')
    verbose_name = _("Assigned Tag")
    verbose_name_plural = _("Assigned Tags")

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        current_language = (
            request.GET.get('language')
            or request.POST.get('language')
            or (obj.get_current_language() if obj else None)
            or 'es'
        )

        class LanguageFilteredTaggedPostFormSet(formset):
            def __init__(self, *args, **formset_kwargs):
                super().__init__(*args, **formset_kwargs)
                self.queryset = self.queryset.filter(language=current_language)
                for form in self.forms:
                    form.instance.language = current_language

            def _construct_form(self, i, **kwargs):
                form = super()._construct_form(i, **kwargs)
                form.instance.language = current_language
                return form

            def save_new(self, form, commit=True):
                form.instance.language = current_language
                return super().save_new(form, commit=commit)

            def save_existing(self, form, instance, commit=True):
                instance.language = current_language
                return super().save_existing(form, instance, commit=commit)

        return LanguageFilteredTaggedPostFormSet

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'tag':
            kwargs['queryset'] = (
                Tag.objects.all()
                .prefetch_related('translations')
                .order_by('slug')
                .distinct()
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CitationInline(GenericTabularInline):
    """Citations for this post, reusing the central sources catalogue."""

    model = Citation
    extra = 0
    autocomplete_fields = ("source",)
    fields = ("source", "language", "order", "locator", "note")
    verbose_name = _("Citation")
    verbose_name_plural = _("Citations and sources")

def _post_admin_language(request, obj):
    return (
        request.GET.get("language")
        or request.POST.get("language")
        or (obj.get_current_language() if obj and getattr(obj, "pk", None) else None)
        or getattr(settings, "LANGUAGE_CODE", "es")
    )


def _translation_has_dedicated_social_image(post):
    asset = post.safe_translation_getter("social_image_asset", any_language=False)
    if asset is not None:
        f = getattr(asset, "image", None)
        if f and getattr(f, "name", ""):
            return True
    return False


def _translation_has_dedicated_mobile_image(post):
    asset = post.safe_translation_getter("mobile_image_asset", any_language=False)
    if asset is not None:
        f = getattr(asset, "image", None)
        if f and getattr(f, "name", ""):
            return True
    return False

@admin.register(Post)
class PostAdmin(TranslatableAdmin, SummernoteModelAdmin):
    """
    🧠 Admin for multilingual Post model using django-parler.
    Combines inline tag editing and tag badge display, and managing categories via ManyToMany.
    """

    # 📋 Columns shown in list view
    list_display = (
        'title',
        'author',
        'status',
        'published_date',
        'views_count',
        'points_today_display',
        'points_week_display',
        'community_score_display',
        'recent_views_display',
        'approved_comments_display',
        'translation_count_display',
        'content_readiness',
        'editor_rating',
        'show_in_post_grids',
        'migrated',
        'display_categories_list',
    )
    list_filter = ('status', 'show_in_post_grids', 'migrated', 'published_date', 'author')
    date_hierarchy = 'published_date'
    ordering = ('status', '-published_date')
    list_editable = ('status', 'show_in_post_grids', 'migrated', 'editor_rating')

    # 🔍 Search across translated fields
    search_fields = (
        'translations__title',
        'translations__summary',
        'translations__content',
        'translations__meta_title',
        'translations__meta_description'
    )

    # 🙈 Hidden fields in form
    # NOTE:
    # We no longer exclude "author" because we want Option A:
    # show author as readonly for non-manager users.
    exclude = ('views_count',)

    # Parler can merge form field names into admin field lists; never treat these as Post fields.
    _NON_MODEL_FORM_LEAKS = frozenset(
        {"featured_image_staging_id", "social_image_staging_id", "mobile_image_staging_id"}
    )

    summernote_fields = ('content',)

    def _is_post_manager(self, request):
        """
        Users with this capability can manage all posts.

        Regular authors can access the Post admin, but are limited to their own posts.
        """
        return (
            request.user.is_superuser
            or request.user.has_perm("site_settings.change_siteconfiguration")
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field_name in ("featured_image_asset", "social_image_asset", "mobile_image_asset"):
            field = form.base_fields.get(field_name)
            if field:
                field.widget = forms.HiddenInput()
                field.required = False
        if "content" in form.base_fields:
            summernote_widget = SummernoteWidget if get_config()["iframe"] else SummernoteInplaceWidget
            form.base_fields["content"].widget = summernote_widget()
        if "summary" in form.base_fields:
            form.base_fields["summary"].widget = forms.Textarea(attrs={
                "rows": 3,
                "maxlength": 280,
            })
        return form

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("featured_image_asset", "social_image_asset", "mobile_image_asset"):
            kwargs.setdefault("widget", forms.HiddenInput)
            kwargs.setdefault("required", False)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_fields(self, request, obj=None):
        fields = [
            f
            for f in (super().get_fields(request, obj) or [])
            if f not in self._NON_MODEL_FORM_LEAKS
        ]
        if not fields:
            return fields

        out = []
        for name in fields:
            if name in ("featured_image_picker", "social_image_picker", "mobile_image_picker"):
                continue
            if name == "featured_image_asset":
                out.append("featured_image_picker")
                continue
            elif name == "social_image_asset":
                out.append("social_image_picker")
                continue
            elif name == "mobile_image_asset":
                out.append("mobile_image_picker")
                continue
            out.append(name)

        return out

    def get_readonly_fields(self, request, obj=None):
        readonly = [
            f
            for f in (super().get_readonly_fields(request, obj) or [])
            if f not in self._NON_MODEL_FORM_LEAKS
        ]

        for name in (
            "featured_image_picker",
            "social_image_picker",
            "mobile_image_picker",
        ):
            if name not in readonly:
                readonly.append(name)

        # Option A:
        # Non-manager users can see the author field but cannot edit it.
        # Manager/superuser users can change author if needed.
        if not self._is_post_manager(request):
            if "author" not in readonly:
                readonly.append("author")

        return readonly

    def _picker_initial_attrs(self, obj, field_name):
        if not obj or not getattr(obj, "pk", None):
            return "", ""
        asset = obj.safe_translation_getter(field_name, any_language=False)
        if asset is None:
            return "", ""
        f = getattr(asset, "image", None)
        if not f or not getattr(f, "name", ""):
            return "", ""
        try:
            url = f.url
        except (OSError, ValueError, NotImplementedError):
            logger.warning(
                _("Failed to resolve the media asset preview URL in the admin."),
                exc_info=True,
            )
            url = ""
        caption = "{} ({})".format(getattr(asset, "title", "") or getattr(asset, "slug", ""), getattr(asset, "slug", ""))
        return url, caption

    @admin.display(description=_("Featured image — media library"))
    def featured_image_picker(self, obj):
        initial_url, initial_caption = self._picker_initial_attrs(obj, "featured_image_asset")
        current_fk = ""
        if obj and getattr(obj, "pk", None):
            asset = obj.safe_translation_getter("featured_image_asset", any_language=False)
            if asset and getattr(asset, "pk", None):
                current_fk = str(asset.pk)
        return format_html(
            '<input type="hidden" name="featured_image_staging_id" value="" autocomplete="off">'
            '<input type="hidden" name="featured_image_asset" value="{}" autocomplete="off">'
            '<div class="gallery-picker-anchor" data-gallery-picker-root '
            'data-stage-url="{}" data-images-url="{}" '
            'data-staging-name="featured_image_staging_id" '
            'data-fk-name="featured_image_asset" '
            'data-initial-url="{}" data-initial-caption="{}"></div>',
            current_fk,
            reverse("gallery_media:stage"),
            reverse("gallery_media:image_list"),
            initial_url,
            initial_caption,
        )

    @admin.display(description=_("Social image — media library"))
    def social_image_picker(self, obj):
        initial_url, initial_caption = self._picker_initial_attrs(obj, "social_image_asset")
        current_fk = ""
        if obj and getattr(obj, "pk", None):
            asset = obj.safe_translation_getter("social_image_asset", any_language=False)
            if asset and getattr(asset, "pk", None):
                current_fk = str(asset.pk)
        return format_html(
            '<input type="hidden" name="social_image_staging_id" value="" autocomplete="off">'
            '<input type="hidden" name="social_image_asset" value="{}" autocomplete="off">'
            '<div class="gallery-picker-anchor" data-gallery-picker-root '
            'data-stage-url="{}" data-images-url="{}" '
            'data-staging-name="social_image_staging_id" '
            'data-fk-name="social_image_asset" '
            'data-initial-url="{}" data-initial-caption="{}"></div>',
            current_fk,
            reverse("gallery_media:stage"),
            reverse("gallery_media:image_list"),
            initial_url,
            initial_caption,
        )

    @admin.display(description=_("Mobile image — media library"))
    def mobile_image_picker(self, obj):
        initial_url, initial_caption = self._picker_initial_attrs(obj, "mobile_image_asset")
        current_fk = ""
        if obj and getattr(obj, "pk", None):
            asset = obj.safe_translation_getter("mobile_image_asset", any_language=False)
            if asset and getattr(asset, "pk", None):
                current_fk = str(asset.pk)
        return format_html(
            '<input type="hidden" name="mobile_image_staging_id" value="" autocomplete="off">'
            '<input type="hidden" name="mobile_image_asset" value="{}" autocomplete="off">'
            '<div class="gallery-picker-anchor" data-gallery-picker-root '
            'data-stage-url="{}" data-images-url="{}" '
            'data-staging-name="mobile_image_staging_id" '
            'data-fk-name="mobile_image_asset" '
            'data-initial-url="{}" data-initial-caption="{}"></div>',
            current_fk,
            reverse("gallery_media:stage"),
            reverse("gallery_media:image_list"),
            initial_url,
            initial_caption,
        )

    # ManyToManyField for categories, uses a nice multi-selector interface
    filter_horizontal = ('categories',)

    # 🧩 Inline form for managing tag relations
    inlines = [TaggedPostInline, CitationInline]

    def get_queryset(self, request):
        """
        Limit regular authors to their own posts.

        The permission posts.change_post allows access to the model.
        This queryset limits the visible records inside the admin.
        """
        queryset = super().get_queryset(request)

        if not self._is_post_manager(request):
            queryset = queryset.filter(author=request.user)

        recent_start = timezone.localdate() - timedelta(days=7)

        recent_views = PostDailyMetric.objects.filter(
            post=OuterRef('pk'),
            date__gte=recent_start,
        ).order_by().values('post').annotate(total=Sum('views_count')).values('total')[:1]

        approved_comments = Comment.objects.filter(
            post=OuterRef('pk'),
            is_approved=True,
        ).order_by().values('post').annotate(total=Count('pk')).values('total')[:1]

        today = timezone.localdate()
        points_today = PostPointAllocation.objects.filter(
            post=OuterRef('pk'),
            date=today,
        ).order_by().values('post').annotate(total=Sum('points')).values('total')[:1]
        points_week = PostPointAllocation.objects.filter(
            post=OuterRef('pk'),
            date__gte=today - timedelta(days=6),
            date__lte=today,
        ).order_by().values('post').annotate(total=Sum('points')).values('total')[:1]

        return queryset.prefetch_related(
            'categories',
            'tags__translations',
            'translations',
        ).annotate(
            recent_views_7d=Coalesce(
                Subquery(recent_views, output_field=IntegerField()),
                Value(0),
            ),
            approved_comments_count=Coalesce(
                Subquery(approved_comments, output_field=IntegerField()),
                Value(0),
            ),
            points_today_total=Coalesce(
                Subquery(points_today, output_field=IntegerField()),
                Value(0),
            ),
            points_week_total=Coalesce(
                Subquery(points_week, output_field=IntegerField()),
                Value(0),
            ),
            translations_available=Count('translations', distinct=True),
        ).annotate(
            community_score_admin=(
                F('points_week_total') * Value(100, output_field=IntegerField())
                + F('editor_rating')
            ),
        )

    def has_view_permission(self, request, obj=None):
        """
        Regular authors can view only their own posts.
        Managers can view all posts.
        """
        has_perm = super().has_view_permission(request, obj)

        if not has_perm:
            return False

        if obj is None:
            return True

        if self._is_post_manager(request):
            return True

        return obj.author_id == request.user.id

    def has_change_permission(self, request, obj=None):
        """
        Regular authors can change only their own posts.
        Managers can change all posts.
        """
        has_perm = super().has_change_permission(request, obj)

        if not has_perm:
            return False

        if obj is None:
            return True

        if self._is_post_manager(request):
            return True

        return obj.author_id == request.user.id

    def has_delete_permission(self, request, obj=None):
        """
        Regular authors cannot delete posts.
        Managers/superusers follow the normal permission system.
        """
        if self._is_post_manager(request):
            return super().has_delete_permission(request, obj)

        return False

    # Custom method to display categories in the list view
    @admin.display(description=_("Categories"))
    def display_categories_list(self, obj):
        return ", ".join([cat.name for cat in obj.categories.all()])

    @admin.display(description=_("7d Views"), ordering='recent_views_7d')
    def recent_views_display(self, obj):
        return obj.recent_views_7d

    @admin.display(description=_("Points Today"), ordering='points_today_total')
    def points_today_display(self, obj):
        return obj.points_today_total

    @admin.display(description=_("7d Points"), ordering='points_week_total')
    def points_week_display(self, obj):
        return obj.points_week_total

    @admin.display(description=_("Community Score"), ordering='community_score_admin')
    def community_score_display(self, obj):
        return obj.community_score_admin

    @admin.display(description=_("Approved Comments"), ordering='approved_comments_count')
    def approved_comments_display(self, obj):
        return obj.approved_comments_count

    @admin.display(description=_("Languages"), ordering='translations_available')
    def translation_count_display(self, obj):
        language_codes = [translation.language_code for translation in obj.translations.all()]
        if not language_codes:
            return "-"
        return format_html_join(
            " ",
            '<span class="badge text-bg-secondary">{}</span>',
            ((language_code.upper(),) for language_code in sorted(language_codes)),
        )

    @admin.display(description=_("Editorial Readiness"))
    def content_readiness(self, obj):
        checks = [
            (_("Summary"), bool(obj.safe_translation_getter('summary', any_language=False))),
            (_("Featured Image"), bool(obj.get_featured_image())),
            (_("Social Image"), _translation_has_dedicated_social_image(obj)),
            (_("Mobile Image"), _translation_has_dedicated_mobile_image(obj)),
            (_("Tags"), obj.tags.exists()),
        ]
        return format_html_join(
            " ",
            '<span class="badge {}">{}</span>',
            (
                ('text-bg-success' if is_ready else 'text-bg-warning', label)
                for label, is_ready in checks
            ),
        )

    # 🏷 Visual badge list of tags
    @admin.display(description=_("Tags"))
    def list_tags(self, obj):
        tags = obj.tags.language('es').all()
        if tags:
            return format_html_join(
                " ",
                '<span class="badge text-bg-warning">{}</span>',
                ((tag.label,) for tag in tags),
            )
        return "-"

    @staticmethod
    def _uuid_from_post(raw):
        if not (raw or "").strip():
            return None
        try:
            return uuid.UUID(str(raw).strip())
        except ValueError:
            return None

    def _apply_gallery_asset_staging_to_cleaned_data(self, request, form):
        """Finalize staged uploads before ``save_form`` builds the instance (Parler + ModelAdmin order)."""
        if not getattr(form, "cleaned_data", None):
            return

        lang = _post_admin_language(request, getattr(form, "instance", None))
        cleaned = form.cleaned_data
        instance = form.instance
        instance.set_current_language(lang)
        title = (cleaned.get("title") or "").strip()
        slug = (cleaned.get("slug") or "").strip() or "post-image"
        summary = (cleaned.get("summary") or "").strip()
        meta = (cleaned.get("meta_description") or "").strip()
        description = summary or meta

        featured_stage = self._uuid_from_post(request.POST.get("featured_image_staging_id"))
        social_stage = self._uuid_from_post(request.POST.get("social_image_staging_id"))
        mobile_stage = self._uuid_from_post(request.POST.get("mobile_image_staging_id"))

        try:
            if featured_stage:
                img = gallery_bridge.create_gallery_image_from_staged_upload(
                    title=title or slug,
                    description=description,
                    language=lang,
                    slug_input=slug,
                    staging_uuid=featured_stage,
                )
                cleaned["featured_image_asset"] = img
                instance.featured_image_asset = img

            if social_stage:
                img = gallery_bridge.create_gallery_image_from_staged_upload(
                    title=title or slug,
                    description=description,
                    language=lang,
                    slug_input=f"{slug}-social",
                    staging_uuid=social_stage,
                )
                cleaned["social_image_asset"] = img
                instance.social_image_asset = img

            if mobile_stage:
                img = gallery_bridge.create_gallery_image_from_staged_upload(
                    title=title or slug,
                    description=description,
                    language=lang,
                    slug_input=f"{slug}-mobile",
                    staging_uuid=mobile_stage,
                )
                cleaned["mobile_image_asset"] = img
                instance.mobile_image_asset = img

        except StagedUpload.DoesNotExist:
            raise ValidationError(
                _("The staged upload expired or was already removed. Upload again."),
            ) from None

        except FinalizationError as exc:
            raise ValidationError(str(exc)) from exc

    def save_form(self, request, form, change):
        self._apply_gallery_asset_staging_to_cleaned_data(request, form)
        return super().save_form(request, form, change)

    # 🚀 Auto-assign author on creation and protect authorship for non-manager users
    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
            logger.info(f"🆕 New post created by 🧑‍💻 {request.user.username}: {obj}")

        elif not self._is_post_manager(request):
            # Non-manager users cannot transfer posts to another author.
            obj.author = request.user
            logger.info(f"✏️ Own post updated by 🧑‍💻 {request.user.username}: {obj}")

        else:
            logger.info(f"✏️ Post updated by 🧑‍💻 {request.user.username}: {obj}")

        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        language_codes = [language_code for language_code, _ in settings.LANGUAGES]

        for deleted_object in formset.deleted_objects:
            if isinstance(deleted_object, TaggedPost):
                TaggedPost.objects.filter(
                    post=deleted_object.post,
                    tag=deleted_object.tag,
                ).delete()
            else:
                deleted_object.delete()

        for instance in instances:
            if isinstance(instance, TaggedPost):
                for language_code in language_codes:
                    TaggedPost.objects.update_or_create(
                        post=instance.post,
                        tag=instance.tag,
                        language=language_code,
                        defaults={'relevance_score': instance.relevance_score},
                    )
            else:
                instance.save()

        formset.save_m2m()

    class Media:
        css = {"all": ("gallery/admin/media_library_picker.css",)}
        js = ("gallery/admin/media_library_picker.js",)

@admin.register(PostDailyMetric)
class PostDailyMetricAdmin(admin.ModelAdmin):
    list_display = ('post', 'date', 'views_count')
    list_filter = ('date',)
    search_fields = ('post__translations__title',)
    date_hierarchy = 'date'
    ordering = ('-date', '-views_count')
