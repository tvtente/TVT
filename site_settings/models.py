from django.db import models
from django.core.exceptions import SuspiciousFileOperation
from django.utils.translation import gettext_lazy as _, gettext
from parler.models import TranslatableModel, TranslatedFields
from solo.models import SingletonModel

class SiteConfiguration(SingletonModel):
    """
    Singleton model to store site-wide configuration settings.
    Only one instance of this model will ever exist.
    """

    # --- Pagination Settings ---
    blog_items_per_page = models.PositiveIntegerField(
        default=9, 
        verbose_name=_("Items per Page in Blog/Category lists"),
        help_text=_("Number of posts to show on the main blog page and on category pages.")
    )
    search_pages_per_page = models.PositiveIntegerField(
        default=5, 
        verbose_name=_("Pages per Page in Search Results")
    )
    search_posts_per_page = models.PositiveIntegerField(
        default=5, 
        verbose_name=_("Posts per Page in Search Results")
    )
    search_results_per_page = models.PositiveIntegerField(
        default=5, 
        verbose_name=_("Results per Page in Search"),
        help_text=_("Number of items to show per section (Pages/Posts) on the search results page.")
    )
    # --- Search Settings ---
    search_importance_limit = models.PositiveIntegerField(
        default=3,
        verbose_name=_("Number of 'Important' Pages to show first in search"),
        help_text=_("How many top-priority pages to display before regular search results.")
    )

    # --- Admin Display Settings ---
    comment_indentation_pixels = models.PositiveIntegerField(
        default=20,
        verbose_name=_("Comment Indentation (in pixels)"),
        help_text=_("Controls the visual indentation for nested comments in the admin.")
    )

    # --- Comment Moderation Settings ---
    auto_approve_comments = models.BooleanField(
        default=False,
        verbose_name=_("Auto-approve comments"),
        help_text=_("If checked, new comments will be published immediately without moderation.")
    )
    post_points_enabled = models.BooleanField(
        default=True,
        verbose_name=_("Enable post points"),
        help_text=_("Allows authenticated users to distribute a limited number of points to posts each day.")
    )
    daily_post_points_budget = models.PositiveIntegerField(
        default=10,
        verbose_name=_("Daily post points budget"),
        help_text=_("How many points each authenticated user can distribute across posts per day.")
    )
    max_points_per_post_per_day = models.PositiveIntegerField(
        default=5,
        verbose_name=_("Max points per post per day"),
        help_text=_("Upper limit a user can assign to a single post within the same day.")
    )
    allow_author_self_points = models.BooleanField(
        default=False,
        verbose_name=_("Allow authors to rate their own posts"),
        help_text=_("If enabled, authors may spend their daily points on their own published posts.")
    )
    post_points_min_account_age_days = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Minimum account age for post points"),
        help_text=_("Number of days a user account must exist before it can assign points to posts. Use 0 to disable this restriction.")
    )

    # --- Caching Settings ---
    menu_cache_timeout = models.PositiveIntegerField(
        default=3600, # Default to 1 hour (3600 seconds)
        verbose_name=_("Menu Cache Timeout (in seconds)"),
        help_text=_("How long the site menus should be stored in cache. Set to 0 to disable menu caching (not recommended).")
    )
    trusted_commenter_threshold = models.PositiveIntegerField(
        default=3,
        verbose_name=_("Trusted Commenter Threshold"),
        help_text=_("The number of approved comments a user needs to post before their future comments are auto-approved.")
    )
    category_tree_cache_timeout = models.PositiveIntegerField(
        default=43200, # Default to 12 hours
        verbose_name=_("Category Tree Cache Timeout (in seconds)"),
        help_text=_("How long the full category tree should be stored in cache. High values are recommended.")
    )
    gallery_items_per_page = models.PositiveIntegerField(
        default=9,
        verbose_name=_("Items per Page in Gallery"),
        help_text=_("Number of images to show on the image gallery page.")
    )
    user_profile_items_per_page = models.PositiveIntegerField(
        default=5,
        verbose_name=_("Items per Page on Public Profile"),
        help_text=_("Number of posts/comments to show per page on a user's public profile.")
    )
    user_directory_items_per_page = models.PositiveIntegerField(
        default=25,
        verbose_name=_("Items per Page in User Directory"),
        help_text=_("Number of users listed per page on the public user directory.")
    )

    class Meta:
        verbose_name = _("Site Configuration")
        verbose_name_plural = _("Site Configuration")

    def __str__(self):
        return gettext("Site Configuration")


class SiteTemplate(TranslatableModel):
    """
    Visual template configuration for branding and theme variables.
    Exactly one template should be marked as chosen.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Template Name"))
    chosen = models.BooleanField(default=False, db_index=True, verbose_name=_("Chosen"))

    site_logo = models.ImageField(
        upload_to='site_branding/',
        blank=True,
        null=True,
        verbose_name=_("Site Logo"),
        help_text=_("The main logo displayed in the top bar.")
    )
    favicon = models.ImageField(
        upload_to='site_branding/favicons/',
        blank=True,
        null=True,
        verbose_name=_("Favicon"),
        help_text=_("Small icon used by browser tabs, bookmarks, and shortcuts.")
    )
    translations = TranslatedFields(
        site_slogan=models.CharField(
            max_length=150,
            blank=True,
            verbose_name=_("Site Slogan"),
            help_text=_("A short tagline displayed next to the logo.")
        ),
        footer_copyright_text=models.TextField(
            blank=True,
            verbose_name=_("Footer Copyright Text"),
            help_text=_("Optional footer copyright text. Use {year} where the current year should appear.")
        ),
    )
    top_bar_banner_image = models.ImageField(
        upload_to='site_branding/banners/',
        blank=True,
        null=True,
        verbose_name=_("Top Bar Banner Image"),
        help_text=_("An optional banner image displayed in the top bar.")
    )
    top_bar_banner_link = models.URLField(
        max_length=255,
        blank=True,
        verbose_name=_("Top Bar Banner Link"),
        help_text=_("The URL the banner image will link to.")
    )
    primary_color = models.CharField(max_length=7, default="#ffc107", verbose_name=_("Primary Color"))
    dark_color = models.CharField(max_length=7, default="#212529", verbose_name=_("Dark Color"))
    light_color = models.CharField(max_length=7, default="#f8f9fa", verbose_name=_("Light Color"))
    body_background_color = models.CharField(max_length=7, default="#f8f9fa", verbose_name=_("Body Background Color"))
    body_text_color = models.CharField(max_length=7, default="#212529", verbose_name=_("Body Text Color"))
    card_box_background_color = models.CharField(max_length=7, default="#f1f3f5", verbose_name=_("Card Box Background Color"))
    card_box_border_color = models.CharField(max_length=7, default="#dee2e6", verbose_name=_("Card Box Border Color"))
    home_notice_background_color = models.CharField(max_length=7, default="#eef2f5", verbose_name=_("Home Notice Background Color"))
    home_notice_text_color = models.CharField(max_length=7, default="#495057", verbose_name=_("Home Notice Text Color"))

    font_family = models.CharField(
        max_length=160,
        default="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        verbose_name=_("Font Family")
    )
    base_font_size = models.PositiveIntegerField(default=16, verbose_name=_("Base Font Size"))
    slogan_font_size = models.PositiveIntegerField(default=28, verbose_name=_("Slogan Font Size"))
    logo_height = models.PositiveIntegerField(default=50, verbose_name=_("Logo Height"))
    banner_max_height = models.PositiveIntegerField(default=50, verbose_name=_("Banner Max Height"))
    border_radius = models.PositiveIntegerField(default=4, verbose_name=_("Border Radius"))
    layout_max_width = models.PositiveIntegerField(default=1440, verbose_name=_("Layout Max Width"))
    layout_horizontal_padding = models.PositiveIntegerField(default=16, verbose_name=_("Layout Horizontal Padding"))
    content_width_percent = models.PositiveIntegerField(default=64, verbose_name=_("Content Width Percent"))
    left_sidebar_width_percent = models.PositiveIntegerField(default=18, verbose_name=_("Left Sidebar Width Percent"))
    right_sidebar_width_percent = models.PositiveIntegerField(default=18, verbose_name=_("Right Sidebar Width Percent"))
    category_tree_max_width = models.PositiveIntegerField(default=860, verbose_name=_("Category Tree Max Width"))
    category_tree_background_color = models.CharField(max_length=7, default="#ffffff", verbose_name=_("Category Tree Background Color"))
    category_tree_border_color = models.CharField(max_length=7, default="#dee2e6", verbose_name=_("Category Tree Border Color"))
    category_tree_base_padding = models.PositiveIntegerField(default=8, verbose_name=_("Category Tree Base Padding"))
    category_tree_indent_step = models.PositiveIntegerField(default=24, verbose_name=_("Category Tree Indent Step"))
    category_tree_row_padding_y = models.PositiveIntegerField(default=8, verbose_name=_("Category Tree Row Vertical Padding"))

    class Meta:
        db_table = 'site_settings_templates'
        verbose_name = _("Site Template")
        verbose_name_plural = _("Site Templates")

    def __str__(self):
        marker = gettext("chosen") if self.chosen else gettext("available")
        return f"{self.name} ({marker})"

    @property
    def translated_site_slogan(self):
        return self.safe_translation_getter("site_slogan", any_language=True) or ""

    @property
    def translated_footer_copyright_text(self):
        return self.safe_translation_getter("footer_copyright_text", any_language=True) or ""

    def _safe_file_url(self, field_name):
        field = getattr(self, field_name, None)
        if not field or not getattr(field, "name", ""):
            return ""
        try:
            storage = field.storage
            if not storage.exists(field.name):
                return ""
            return field.url
        except (ValueError, OSError, SuspiciousFileOperation):
            return ""

    @property
    def site_logo_url(self):
        return self._safe_file_url("site_logo")

    @property
    def favicon_url(self):
        return self._safe_file_url("favicon")

    @property
    def top_bar_banner_image_url(self):
        return self._safe_file_url("top_bar_banner_image")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.chosen:
            SiteTemplate.objects.exclude(pk=self.pk).update(chosen=False)

    @classmethod
    def get_chosen(cls):
        template = cls.objects.filter(chosen=True).first()
        if template:
            return template
        template = cls.objects.first()
        if template:
            return template
        return cls.objects.create(name=gettext("Default"), chosen=True)
