import uuid

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from parler.admin import TranslatableAdmin
from solo.admin import SingletonModelAdmin

from gallery.finalization import FinalizationError
from gallery.models import Image, StagedUpload
from gallery.staging_uploads import create_gallery_image_from_staged_upload
from .models import SiteConfiguration, SiteTemplate


COLOR_FIELDS = {
    "primary_color",
    "dark_color",
    "light_color",
    "body_background_color",
    "body_text_color",
    "card_box_background_color",
    "card_box_border_color",
    "home_notice_background_color",
    "home_notice_text_color",
    "category_tree_background_color",
    "category_tree_border_color",
}

SITE_CONFIGURATION_HELP_TEXTS = {
    "blog_items_per_page": _("How many posts appear in blog and category lists before pagination is shown."),
    "homepage_post_grid_columns": _("Desktop columns for the latest-posts grid on the homepage."),
    "homepage_post_grid_rows": _("Rows shown on the homepage before pagination. The total is rows multiplied by columns."),
    "search_pages_per_page": _("How many page results are shown in the Pages section of search results."),
    "search_posts_per_page": _("How many post results are shown in the Posts section of search results."),
    "search_results_per_page": _("General fallback for paginated search sections. Keep it close to the page/post values."),
    "search_importance_limit": _("How many high-priority pages are promoted before regular search matches."),
    "comment_indentation_pixels": _("Horizontal indentation used for nested comments in the admin. Larger values make replies more visually nested."),
    "auto_approve_comments": _("When enabled, comments become public immediately. Leave disabled if moderation is important."),
    "post_points_enabled": _("Turns the daily post-points system on or off across the public site."),
    "daily_post_points_budget": _("How many points each authenticated user receives per day to distribute across posts."),
    "max_points_per_post_per_day": _("Maximum number of points the same user may assign to one post during a single day."),
    "allow_author_self_points": _("Lets authors spend their daily points on their own published posts. Leave disabled for stricter editorial neutrality."),
    "post_points_min_account_age_days": _("How old an account must be before it can assign post points. Useful to reduce drive-by abuse or fresh-account manipulation."),
    "menu_cache_timeout": _("How long menus stay cached. Use 0 only while editing/testing menus; higher values are better for production."),
    "trusted_commenter_threshold": _("After this number of approved comments, a user can be treated as trusted for future comment approval."),
    "category_tree_cache_timeout": _("How long the category tree stays cached. High values are recommended because category trees change rarely."),
    "gallery_items_per_page": _("How many images appear per page in the public Media/Gallery view."),
    "user_profile_items_per_page": _("How many posts/comments appear per page in public user profiles."),
    "user_directory_items_per_page": _("How many users appear per page on the public user directory listing."),
}

SITE_TEMPLATE_HELP_TEXTS = {
    "name": _("Internal name for this visual template. Use a clear name so it is easy to identify in the admin."),
    "chosen": _("When enabled, this template becomes the active theme. Only one template should be chosen at a time."),
    "site_logo": _("Main logo shown in the top bar/header. Its displayed height is controlled by Logo Height."),
    "favicon": _("Small browser icon shown in tabs, bookmarks, and shortcuts. Square images work best."),
    "site_slogan": _("Short phrase shown beside or near the logo, depending on the active header layout."),
    "top_bar_banner_image": _("Optional image displayed in the top bar. Use it for a slim banner, not for large hero images."),
    "top_bar_banner_link": _("Destination URL when the top bar banner is clicked. Leave blank if the banner should not link anywhere."),
    "navigation_banner_image": _("Compact image displayed immediately before the shopping cart in the main navigation."),
    "navigation_banner_link": _("Destination URL when the navigation banner is clicked. Leave blank to show it without a link."),
    "footer_copyright_text": _("Text shown in the footer. Use {year} to insert the current year automatically."),
    "primary_color": _("Main accent color. Used by buttons, highlights, separators, and theme accents."),
    "dark_color": _("Dark theme color. Used by dark header areas, strong contrast elements, and dark buttons."),
    "light_color": _("Light theme color. Used by light backgrounds and subtle contrast areas."),
    "body_background_color": _("Main page background color. This affects the overall feel of the whole site."),
    "body_text_color": _("Default text color across public pages. Keep strong contrast against the body background."),
    "card_box_background_color": _("Background for cards, widget boxes, and grouped content areas."),
    "card_box_border_color": _("Border color for cards and boxed areas. Use a subtle color to avoid visual noise."),
    "home_notice_background_color": _("Background for highlighted notice/CTA sections on the homepage."),
    "home_notice_text_color": _("Text color inside homepage notice/CTA sections. Keep it readable against the notice background."),
    "font_family": _("Main CSS font stack used across the site. Use valid CSS font-family syntax."),
    "base_font_size": _("Base text size in pixels. This affects most body text across the site."),
    "slogan_font_size": _("Slogan text size in pixels. Increase only if the slogan has enough horizontal space."),
    "logo_height": _("Displayed logo height in pixels in the top/header area. Example: 40 keeps the logo compact."),
    "banner_max_height": _("Maximum banner image height in pixels in the top bar. Keeps banners from pushing the layout down."),
    "navigation_banner_height": _("Displayed height in pixels for the compact banner immediately before the shopping cart."),
    "border_radius": _("Corner rounding in pixels for buttons, cards, images, and panels that follow the theme."),
    "layout_max_width": _("Maximum page width in pixels. Larger values make content spread more on wide screens."),
    "layout_horizontal_padding": _("Horizontal padding in pixels around the main layout. Helps content breathe on small screens."),
    "content_width_percent": _("Central content column width percentage on desktop layouts."),
    "left_sidebar_width_percent": _("Left sidebar width percentage on desktop layouts. Works together with content and right sidebar widths."),
    "right_sidebar_width_percent": _("Right sidebar width percentage on desktop layouts. Works together with content and left sidebar widths."),
    "category_tree_max_width": _("Maximum width in pixels for category tree widgets and category navigation blocks."),
    "category_tree_background_color": _("Background color for category tree widgets."),
    "category_tree_border_color": _("Border color for category tree widgets."),
    "category_tree_base_padding": _("Base inner padding in pixels for category tree widgets."),
    "category_tree_indent_step": _("Indentation step in pixels for each nested category level."),
    "category_tree_row_padding_y": _("Vertical padding in pixels for each category tree row."),
}


BRANDING_MEDIA_FIELDS = {
    "site_logo": {
        "asset": "site_logo_asset",
        "staging": "site_logo_staging_id",
        "clear": "site_logo_clear_selection",
        "label": _("Site logo"),
        "slug": "logo",
        "aspect": "",
    },
    "favicon": {
        "asset": "favicon_asset",
        "staging": "favicon_staging_id",
        "clear": "favicon_clear_selection",
        "label": _("Favicon"),
        "slug": "favicon",
        "aspect": "1_1",
    },
    "top_bar_banner_image": {
        "asset": "top_bar_banner_image_asset",
        "staging": "top_bar_banner_staging_id",
        "clear": "top_bar_banner_clear_selection",
        "label": _("Top bar banner"),
        "slug": "top-bar-banner",
        "aspect": "",
    },
    "navigation_banner_image": {
        "asset": "navigation_banner_image_asset",
        "staging": "navigation_banner_staging_id",
        "clear": "navigation_banner_clear_selection",
        "label": _("Navigation banner"),
        "slug": "navigation-banner",
        "aspect": "",
    },
}


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(SingletonModelAdmin):
    fieldsets = (
        (_("Content pagination"), {
            "description": _(
                "Controls how many items are shown before pagination appears in public lists."
            ),
            "fields": (
                "blog_items_per_page",
                "homepage_post_grid_columns",
                "homepage_post_grid_rows",
                "gallery_items_per_page",
                "user_profile_items_per_page",
                "user_directory_items_per_page",
            ),
        }),
        (_("Search"), {
            "description": _(
                "Controls search result density and how many important pages are promoted before regular results."
            ),
            "fields": (
                "search_pages_per_page",
                "search_posts_per_page",
                "search_results_per_page",
                "search_importance_limit",
            ),
        }),
        (_("Comments"), {
            "description": _(
                "Controls moderation behavior and how nested conversations are displayed in the admin."
            ),
            "fields": (
                "auto_approve_comments",
                "trusted_commenter_threshold",
                "comment_indentation_pixels",
            ),
        }),
        (_("Post points"), {
            "description": _(
                "Controls the daily community points that authenticated users can assign to posts."
            ),
            "fields": (
                "post_points_enabled",
                "daily_post_points_budget",
                "max_points_per_post_per_day",
                "allow_author_self_points",
                "post_points_min_account_age_days",
            ),
        }),
        (_("Cache"), {
            "description": _(
                "Controls how long expensive menu and category tree queries are cached. Use 0 only while testing."
            ),
            "fields": (
                "menu_cache_timeout",
                "category_tree_cache_timeout",
            ),
        }),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if formfield and db_field.name in SITE_CONFIGURATION_HELP_TEXTS:
            formfield.help_text = SITE_CONFIGURATION_HELP_TEXTS[db_field.name]
        return formfield


@admin.register(SiteTemplate)
class SiteTemplateAdmin(TranslatableAdmin):
    list_display = (
        "name",
        "chosen",
        "primary_color_preview",
        "dark_color_preview",
        "font_family",
        "current_site_slogan",
    )
    list_filter = ("chosen",)
    list_editable = ("chosen",)
    search_fields = ("name", "translations__site_slogan", "translations__footer_copyright_text")
    fieldsets = (
        (_("Template identity"), {
            "description": _(
                "Only one template should be marked as chosen. The chosen template provides the active visual theme."
            ),
            "fields": ("name", "chosen")
        }),
        (_("Branding"), {
            "description": _(
                "Images and short text used in the top area of the site. Logo, favicon, and banner are independent files."
            ),
            "fields": (
                "site_logo_media_picker",
                "favicon_media_picker",
                "site_slogan",
                "top_bar_banner_media_picker",
                "top_bar_banner_link",
            )
        }),
        (_("Navigation banner"), {
            "description": _(
                "A compact optional image placed immediately before the shopping cart in the main navigation."
            ),
            "fields": (
                "navigation_banner_media_picker",
                "navigation_banner_link",
                "navigation_banner_height",
            )
        }),
        (_("Footer"), {
            "description": _(
                "Footer text shown at the bottom of the site. Use {year} to insert the current year automatically."
            ),
            "fields": ("footer_copyright_text",)
        }),
        (_("Colors"), {
            "description": _(
                "Use the color selector to open the browser palette. Colors are saved as hexadecimal values, for example #ffc107."
            ),
            "fields": (
                "primary_color",
                "dark_color",
                "light_color",
                "body_background_color",
                "body_text_color",
                "card_box_background_color",
                "card_box_border_color",
                "home_notice_background_color",
                "home_notice_text_color",
            )
        }),
        (_("Typography and Sizes"), {
            "description": _(
                "Controls base typography and common visual sizes. Numeric values are interpreted as pixels."
            ),
            "fields": ("font_family", "base_font_size", "slogan_font_size", "logo_height", "banner_max_height", "border_radius")
        }),
        (_("Layout"), {
            "description": _(
                "Controls the maximum width and the proportion of content versus sidebars. Percent fields should add up sensibly."
            ),
            "fields": ("layout_max_width", "layout_horizontal_padding", "content_width_percent", "left_sidebar_width_percent", "right_sidebar_width_percent")
        }),
        (_("Category Tree"), {
            "description": _(
                "Controls the category tree container, indentation, spacing, and colors used by category widgets."
            ),
            "fields": ("category_tree_max_width", "category_tree_background_color", "category_tree_border_color", "category_tree_base_padding", "category_tree_indent_step", "category_tree_row_padding_y")
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj) or [])
        for name in (
            "site_logo_media_picker",
            "favicon_media_picker",
            "top_bar_banner_media_picker",
            "navigation_banner_media_picker",
        ):
            if name not in readonly:
                readonly.append(name)
        return readonly

    def _branding_initial(self, obj, legacy_field, asset_field):
        if not obj:
            return "", ""
        asset = getattr(obj, asset_field, None)
        if asset:
            return (
                asset.get_image_url(),
                "{} ({})".format(asset.title or asset.slug, asset.slug),
            )
        legacy = getattr(obj, legacy_field, None)
        if legacy and getattr(legacy, "name", ""):
            try:
                return legacy.url, legacy.name
            except (OSError, ValueError):
                pass
        return "", ""

    def _branding_picker(self, obj, legacy_field):
        config = BRANDING_MEDIA_FIELDS[legacy_field]
        initial_url, initial_caption = self._branding_initial(
            obj, legacy_field, config["asset"]
        )
        selected_id = getattr(obj, f"{config['asset']}_id", "") if obj else ""
        return format_html(
            '<input type="hidden" name="{}" value="" autocomplete="off">'
            '<input type="hidden" name="{}" value="{}" autocomplete="off">'
            '<input type="hidden" name="{}" value="" autocomplete="off">'
            '<div class="gallery-picker-anchor" data-gallery-picker-root '
            'data-stage-url="{}" data-images-url="{}" '
            'data-staging-name="{}" data-fk-name="{}" data-clear-name="{}" '
            'data-upload-aspect="{}" '
            'data-initial-url="{}" data-initial-caption="{}"></div>',
            config["staging"],
            config["asset"],
            selected_id or "",
            config["clear"],
            reverse("gallery_media:stage"),
            reverse("gallery_media:image_list"),
            config["staging"],
            config["asset"],
            config["clear"],
            config["aspect"],
            initial_url,
            initial_caption,
        )

    @admin.display(description=_("Site logo — media library"))
    def site_logo_media_picker(self, obj):
        return self._branding_picker(obj, "site_logo")

    @admin.display(description=_("Favicon — media library"))
    def favicon_media_picker(self, obj):
        return self._branding_picker(obj, "favicon")

    @admin.display(description=_("Top bar banner — media library"))
    def top_bar_banner_media_picker(self, obj):
        return self._branding_picker(obj, "top_bar_banner_image")

    @admin.display(description=_("Navigation banner — media library"))
    def navigation_banner_media_picker(self, obj):
        return self._branding_picker(obj, "navigation_banner_image")

    @staticmethod
    def _staging_id(request, field_name):
        raw = (request.POST.get(field_name) or "").strip()
        if not raw:
            return None
        try:
            return uuid.UUID(raw)
        except ValueError:
            return None

    def _finalize_branding_media(self, request, obj):
        changed = False
        base_slug = slugify(obj.name) or "site"
        for legacy_field, config in BRANDING_MEDIA_FIELDS.items():
            stage_id = self._staging_id(request, config["staging"])
            clear_requested = request.POST.get(config["clear"]) == "1"
            asset_id = (request.POST.get(config["asset"]) or "").strip()

            if stage_id:
                try:
                    asset = create_gallery_image_from_staged_upload(
                        title=f"{obj.name} · {config['label']}"[:100],
                        description="",
                        language="es",
                        slug_input=(
                            f"{base_slug}-{config['slug']}-{timezone.now():%y%m%d%H%M%S}"
                        ),
                        staging_uuid=stage_id,
                    )
                except StagedUpload.DoesNotExist:
                    raise ValidationError(_("The staged upload expired or was already removed. Upload again.")) from None
                except FinalizationError as exc:
                    raise ValidationError(str(exc)) from exc
                setattr(obj, config["asset"], asset)
                setattr(obj, legacy_field, "")
                changed = True
                continue

            if clear_requested:
                setattr(obj, config["asset"], None)
                setattr(obj, legacy_field, "")
                changed = True
                continue

            if asset_id:
                asset = Image.objects.filter(pk=asset_id).first()
                if asset and getattr(obj, f"{config['asset']}_id") != asset.pk:
                    setattr(obj, config["asset"], asset)
                    changed = True
        if changed:
            obj.save()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._finalize_branding_media(request, obj)

    @admin.display(description=_("Site Slogan"))
    def current_site_slogan(self, obj):
        return obj.translated_site_slogan

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in COLOR_FIELDS and formfield:
            formfield.widget = forms.TextInput(attrs={
                "type": "color",
                "style": "width: 5rem; height: 2.25rem; padding: 0.125rem;",
            })
        if formfield and db_field.name in SITE_TEMPLATE_HELP_TEXTS:
            formfield.help_text = SITE_TEMPLATE_HELP_TEXTS[db_field.name]
            if db_field.name in COLOR_FIELDS:
                formfield.help_text = _(
                    "%(description)s Click the color box to open the palette. The value is stored as hexadecimal color."
                ) % {"description": formfield.help_text}
        return formfield

    @admin.display(description=_("Primary Color"))
    def primary_color_preview(self, obj):
        return self._color_preview(obj.primary_color)

    @admin.display(description=_("Dark Color"))
    def dark_color_preview(self, obj):
        return self._color_preview(obj.dark_color)

    def _color_preview(self, color):
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:8px;">'
            '<span style="width:22px;height:22px;border-radius:4px;border:1px solid #ccc;background:{};"></span>'
            '<span>{}</span>'
            "</span>",
            color,
            color,
        )

    class Media:
        css = {"all": ("gallery/admin/media_library_picker.css",)}
        js = ("gallery/admin/media_library_picker.js",)
