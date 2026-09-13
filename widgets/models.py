# widgets/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields
from categories.models import Category

class WidgetZone(models.Model):
    """
    Defines a specific area in a template where widgets can be placed.
    e.g., 'Blog Sidebar', 'Footer Column 1', 'Homepage Sidebar'.
    """
    name = models.CharField(max_length=100, verbose_name=_("Zone Name"))
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_("Slug (used in templates)"))

    class Meta:
        verbose_name = _("Widget Zone")
        verbose_name_plural = _("Widget Zones")
        ordering = ['name']

    def __str__(self):
        return self.name


class Widget(TranslatableModel):
    """
    Represents a single, configurable widget that can be placed in a WidgetZone.
    """
    class WidgetType(models.TextChoices):
        RECENT_POSTS = 'recent_posts', _('Recent Blog Posts')
        MOST_VIEWED_POSTS = 'most_viewed_posts', _('Most Viewed Blog Posts')
        MOST_COMMENTED_POSTS = 'most_commented_posts', _('Most Commented Blog Posts')
        BLOG_CATEGORIES = 'blog_categories', _('Blog Category List')
        FEATURED_TAGS = 'featured_tags', _('Featured Tags')
        CATEGORY_TAG_CLOUD = 'category_tag_cloud', _('Category Tag Cloud')
        EDITOR_PICKS_POSTS = 'editor_picks_posts', _("Editor's Picks (Blog Posts)")
        
        # --- NEW WIDGET TYPES FOR FLEXIBLE POST GRIDS ---
        POST_GRID_RECENT = 'post_grid_recent', _("Post Grid: Recent Posts")
        POST_GRID_CATEGORY = 'post_grid_category', _("Post Grid: Category")
        POST_GRID_POPULAR = 'post_grid_popular', _("Post Grid: Most Viewed")
        POST_GRID_COMMENTED = 'post_grid_commented', _("Post Grid: Most Commented")
        POST_GRID_EDITOR = 'post_grid_editor', _("Post Grid: Editor's Picks")
        POST_GRID_TOP_RATED_TODAY = 'post_grid_top_rated_today', _("Post Grid: Top Rated Today")
        POST_GRID_TOP_RATED_WEEK = 'post_grid_top_rated_week', _("Post Grid: Top Rated This Week")
        POST_GRID_MOST_FAVORITED = 'post_grid_most_favorited', _("Post Grid: Most Favorited")
        POST_GRID_COMMUNITY_PICKS = 'post_grid_community_picks', _("Post Grid: Community Picks")
        POST_GRID_TOP_TAGS = 'post_grid_top_tags', _("Post Grid: Top Tags")
        POST_INTENT_REFLECTION = 'post_intent_reflection', _("Intent: For Reflection")
        POST_INTENT_QUICK_READS = 'post_intent_quick_reads', _("Intent: Quick Reads")
        POST_INTENT_WELLBEING = 'post_intent_wellbeing', _("Intent: Well-being")
        POST_INTENT_DEBATE = 'post_intent_debate', _("Intent: Debate Starters")

        POST_CAROUSEL = 'post_carousel', _("Post Carousel")
        POST_CAROUSEL_COMMENTED = 'post_carousel_commented', _("Post Carousel: Most Commented")
        POST_CAROUSEL_VIEWED = 'post_carousel_viewed', _("Post Carousel: Most Viewed")
        HERO_CAROUSEL = "hero_carousel", _("Hero Carousel")
        BOOK_GRID_RECENT = "book_grid_recent", _("Book Grid: Recent Books")
        PUBLICATION_GRID_RECENT = "publication_grid_recent", _("Publication Grid: Recent Publications")
        PAGE_CARD = "page_card", _("Page Card")
        USER_DIRECTORY = 'user_directory', _("User Directory")
        TESTIMONIALS = 'testimonials', _("Testimonials")

        # We can easily add more types in the future:
        # PAGE_LIST = 'page_list', _('List of Pages')
        # HTML_CONTENT = 'html_content', _('Custom HTML Content')

    class ImageFormat(models.TextChoices):
        AUTO = "auto", _("Auto")
        SQUARE = "square", _("Square / Social")
        LANDSCAPE = "landscape", _("Landscape / Featured")
        MOBILE = "mobile", _("Mobile / 9:16")

    zone = models.ForeignKey(
        WidgetZone, 
        on_delete=models.CASCADE, 
        related_name="widgets", 
        verbose_name=_("Widget Zone")
    )
    widget_type = models.CharField(
        max_length=50, 
        choices=WidgetType.choices, 
        verbose_name=_("Widget Type")
    )
    translations = TranslatedFields(
        title=models.CharField(
            max_length=100,
            verbose_name=_("Widget Title"),
            help_text=_("The title that will be displayed above the widget."),
        ),
        section_title=models.CharField(
            max_length=200,
            blank=True,
            null=True,
            verbose_name=_("Section Title (Optional)"),
            help_text=_("A main title for this grid section (e.g., 'Latest Posts', 'Our Bestsellers')."),
        ),
        view_all_link_text=models.CharField(
            max_length=100,
            blank=True,
            null=True,
            verbose_name=_("View All Link Text"),
            help_text=_("Text for the 'View All' link below the grid (e.g., 'View All Posts')."),
        ),
    )
    order = models.PositiveIntegerField(
        default=0, 
        verbose_name=_("Display Order")
    )
    
    # --- Configuration Fields (optional, used by specific widget types) ---
    item_count = models.PositiveIntegerField(
        default=5, 
        verbose_name=_("Number of items to show"),
        # Texto mejorado para reflejar su uso dual
        help_text=_("Used by widgets that display a list of items, like 'Recent Posts' or 'Blog Categories'.")
    )
    top_tag_count = models.PositiveIntegerField(
        default=3,
        verbose_name=_("Number of top tags"),
        help_text=_("For the Top Tags grid, how many leading cloud tags are used to select posts."),
    )
    
    cache_timeout = models.PositiveIntegerField(
        default=900, # Default to 15 minutes (900 seconds)
        verbose_name=_("Cache Timeout (in seconds)"),
        help_text=_("How long the results of this widget should be stored in cache. 0 to disable caching for this widget.")
    )
    
    category_filter = models.ForeignKey(
        Category,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Filter by Category (optional)"),
        help_text=_("If selected, the widget will only show items from this specific category.")
    )
    page_filter = models.ForeignKey(
        "pages.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Featured Page (optional)"),
        help_text=_("The page displayed by the Page Card widget."),
    )
    link_to_author_cv = models.BooleanField(
        default=False,
        verbose_name=_("Prefer the author's public CV"),
        help_text=_(
            "For a featured profile page, link to the author's public CV when it is available in the selected language."
        ),
    )

    # --- NEW: Grid/Column Configuration ---
    column_count = models.PositiveIntegerField(
        default=3,
        verbose_name=_("Column Count"),
        help_text=_("Number of columns for grid display (e.g., 2, 3, 4).")
    )
    image_format = models.CharField(
        max_length=20,
        choices=ImageFormat.choices,
        default=ImageFormat.AUTO,
        verbose_name=_("Image Format"),
        help_text=_("Choose which visual format this widget should prefer: landscape, square/social, or mobile 9:16."),
    )
    
    view_all_link_url = models.CharField( # Storing as CharField to allow direct URLs or URL names
        max_length=255,
        blank=True, null=True,
        verbose_name=_("View All Link URL"),
        help_text=_("URL for the 'View All' link (e.g., '/blog/').")
    )
    carousel_interval_ms = models.PositiveIntegerField(
        default=5000, # 5 seconds in milliseconds
        verbose_name=_("Carousel Interval (ms)"),
        help_text=_("Time in milliseconds between slides for 'Post Carousel' widget.")
    )
    
    class Meta:
        ordering = ['zone', 'order']
        verbose_name = _("Widget")
        verbose_name_plural = _("Widgets")

    def __str__(self):
        return f"{self.translated_title} ({self.get_widget_type_display()}) in {self.zone.name}"

    @property
    def translated_title(self):
        return self.safe_translation_getter("title", any_language=True) or str(_("Untitled"))

    @property
    def translated_section_title(self):
        return self.safe_translation_getter("section_title", any_language=True) or ""

    @property
    def translated_view_all_link_text(self):
        return self.safe_translation_getter("view_all_link_text", any_language=True) or ""
