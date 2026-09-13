from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation
from categories.models import Category
from django.utils.translation import get_language, override 
from widgets.models import WidgetZone
from parler.models import TranslatableModel, TranslatedFields

class Page(TranslatableModel):
    """ Represents a single static page in the CMS, like 'About Us'. """
    
    STATUS_CHOICES = (
        ('draft', _('Draft')),
        ('published', _('Published')),
    )
    translations = TranslatedFields(
        title=models.CharField(max_length=250, verbose_name=_("Title")),
        slug=models.SlugField(max_length=250, verbose_name=_("Slug (URL friendly)")),
        content=models.TextField(verbose_name=_("Content")),
        meta_title=models.CharField(max_length=70, blank=True, null=True, verbose_name=_("Meta Title (SEO)")),
        meta_description=models.CharField(max_length=160, blank=True, null=True, verbose_name=_("Meta Description (SEO)")),
        abstract=models.TextField(blank=True, verbose_name=_("Abstract")),
        keywords=models.CharField(
            max_length=300,
            blank=True,
            verbose_name=_("Keywords"),
            help_text=_("Optional comma-separated keywords."),
        ),
        meta={
            "unique_together": [("language_code", "slug")],
        },
    )
    
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="pages", verbose_name=_("Author"))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name=_("Status"))
    
    categories = models.ManyToManyField(
        Category,
        blank=True,
        verbose_name=_("Categories"),
        related_name="pages"
    )
    
    is_homepage = models.BooleanField(
        default=False,
        verbose_name=_("Is Homepage?"),
        help_text=_("Only one page can be the homepage. Saving this page as homepage will unset the previous one.")
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Creation Date"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Last Updated"))

    importance_order = models.PositiveIntegerField(
        default=99,
        verbose_name=_("Importance Order"),
        help_text=_("A lower number means higher priority in search results. E.g., 1 for 'About Us', 2 for 'Contact', 99 for others.")
    )
    # Explicit per-locale gallery.Image FKs kept as dedicated fields for visual assets.
    featured_image_asset = models.ForeignKey(
        "gallery.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Featured image (library, default column)"),
        help_text=_("Optional gallery row for the unsuffixed featured_image column (usually default locale)."),
    )
    featured_image_asset_es = models.ForeignKey(
        "gallery.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Featured image (library, ES)"),
    )
    featured_image_asset_en = models.ForeignKey(
        "gallery.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Featured image (library, EN)"),
    )
    featured_image_asset_ca = models.ForeignKey(
        "gallery.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Featured image (library, CA)"),
    )

    class Meta:
        verbose_name = _("page")
        verbose_name_plural = _("pages")
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=("is_homepage",),
                condition=Q(is_homepage=True),
                name="unique_active_homepage",
            ),
        ]

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True) or str(_("Untitled"))

    def save(self, *args, **kwargs):
        if self.is_homepage:
            Page.objects.exclude(pk=self.pk).filter(is_homepage=True).update(is_homepage=False)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        # Uses the 'pages' namespace to generate the correct URL.
        if self.is_homepage:
            return reverse('home')
        translated_slug = (
            self.safe_translation_getter("slug", language_code=get_language(), any_language=False)
        )
        return reverse('pages:page_detail', kwargs={'slug': translated_slug})

    @staticmethod
    def _file_from_gallery_asset(asset):
        if asset is None:
            return None
        f = getattr(asset, "image", None)
        if f and getattr(f, "name", ""):
            return f
        return None

    def get_featured_image(self, language_code=None):
        """
        Asset-only: per-language gallery asset, then base asset fallback.
        """
        language_code = language_code or get_language()
        asset = self._file_from_gallery_asset(
            getattr(self, f"featured_image_asset_{language_code}", None),
        )
        if asset:
            return asset
        base_asset = self._file_from_gallery_asset(getattr(self, "featured_image_asset", None))
        if base_asset:
            return base_asset
        return None

    def get_abstract(self, language_code=None):
        language_code = language_code or get_language()
        return (
            self.safe_translation_getter("abstract", language_code=language_code, any_language=False)
            or self.safe_translation_getter("meta_description", language_code=language_code, any_language=False)
            or ''
        )

    def get_keywords(self, language_code=None):
        language_code = language_code or get_language()
        return (
            self.safe_translation_getter("keywords", language_code=language_code, any_language=False)
            or ''
        )

    def get_keywords_list(self, language_code=None):
        keywords = self.get_keywords(language_code)
        return [keyword.strip() for keyword in keywords.split(',') if keyword.strip()]

    def get_absolute_url_for_language(self, language_code):
        with override(language_code):
            # The homepage is routed at the language root (e.g. /es/), not
            # through the generic page-detail URL.  This also keeps the
            # language selector on the home view, which provides its dynamic
            # sections such as the latest-posts list.
            if self.is_homepage:
                return reverse('home')
            translated_slug = (
                self.safe_translation_getter("slug", language_code=language_code, any_language=False)
            )
            return reverse('pages:page_detail', kwargs={'slug': translated_slug})

    @property
    def translated_title(self):
        return self.safe_translation_getter("title", any_language=False) or str(_("Untitled"))

    @property
    def translated_content(self):
        return self.safe_translation_getter("content", any_language=False) or ""

    @property
    def translated_meta_title(self):
        return self.safe_translation_getter("meta_title", any_language=False) or ""

    @property
    def translated_meta_description(self):
        return self.safe_translation_getter("meta_description", any_language=False) or ""


class HomeSection(TranslatableModel):
    class BackgroundStyle(models.TextChoices):
        DEFAULT = 'default', _("Default")
        MUTED = 'muted', _("Muted")
        NOTICE = 'notice', _("Notice")
        SURFACE = 'surface', _("Surface")

    translations = TranslatedFields(
        title=models.CharField(
            max_length=160,
            verbose_name=_("Internal Title"),
            help_text=_("Internal name for organizing this home section in the admin.")
        ),
        content=models.TextField(
            blank=True,
            verbose_name=_("Content"),
            help_text=_("Optional HTML/WYSIWYG content shown for this section.")
        ),
    )
    enabled = models.BooleanField(default=True, db_index=True, verbose_name=_("Enabled"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Display Order"))
    widget_zone = models.ForeignKey(
        WidgetZone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='home_sections',
        verbose_name=_("Widget Zone After Content"),
        help_text=_("Optional widget zone rendered after this section content.")
    )
    show_separator_after = models.BooleanField(
        default=True,
        verbose_name=_("Show Separator After"),
        help_text=_("Displays a separator after this section.")
    )
    background_style = models.CharField(
        max_length=20,
        choices=BackgroundStyle.choices,
        default=BackgroundStyle.DEFAULT,
        verbose_name=_("Background Style")
    )
    full_width = models.BooleanField(
        default=False,
        verbose_name=_("Full Width"),
        help_text=_("If enabled, the section content can span the full content column width.")
    )

    class Meta:
        ordering = ('order', 'id')
        verbose_name = _("Home Section")
        verbose_name_plural = _("Home Sections")

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True) or str(_("Untitled"))

    @property
    def translated_title(self):
        return self.safe_translation_getter("title", any_language=True) or str(_("Untitled"))

    @property
    def translated_content(self):
        return self.safe_translation_getter("content", any_language=True) or ""


class PageSection(TranslatableModel):
    class SectionType(models.TextChoices):
        CONTENT = "content", _("Content block")
        WIDGET_ZONE = "widget_zone", _("Widget zone")
        HERO = "hero", _("Hero")
        PAGE = "page", _("Embedded page")

    class BackgroundStyle(models.TextChoices):
        DEFAULT = "default", _("Default")
        MUTED = "muted", _("Muted")
        NOTICE = "notice", _("Notice")
        SURFACE = "surface", _("Surface")
        DARK = "dark", _("Dark")

    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="page_sections",
        verbose_name=_("Page"),
    )
    translations = TranslatedFields(
        internal_title=models.CharField(
            max_length=160,
            verbose_name=_("Internal Title"),
            help_text=_("Internal name for organizing this page section in the admin."),
        ),
        heading=models.CharField(
            max_length=250,
            blank=True,
            verbose_name=_("Visible Heading"),
        ),
        content=models.TextField(
            blank=True,
            verbose_name=_("Content"),
            help_text=_("Optional HTML/WYSIWYG content shown for this page section."),
        ),
        button_text=models.CharField(
            max_length=120,
            blank=True,
            verbose_name=_("Button Text"),
        ),
        button_url=models.CharField(
            max_length=300,
            blank=True,
            verbose_name=_("Button URL"),
            help_text=_("Optional internal or external URL for the section button."),
        ),
    )
    section_type = models.CharField(
        max_length=30,
        choices=SectionType.choices,
        default=SectionType.CONTENT,
        verbose_name=_("Section Type"),
    )
    widget_zone = models.ForeignKey(
        WidgetZone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="page_sections",
        verbose_name=_("Widget Zone"),
        help_text=_("Optional widget zone rendered inside this page section."),
    )
    linked_page = models.ForeignKey(
        Page,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="embedded_in_sections",
        verbose_name=_("Linked Page"),
        help_text=_("Optional page rendered inside this section when using the embedded page type."),
    )
    background_image = models.ForeignKey(
        "gallery.Image",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Background Image"),
    )
    enabled = models.BooleanField(default=True, db_index=True, verbose_name=_("Enabled"))
    allowed_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="visible_page_sections",
        verbose_name=_("Visible for groups"),
        help_text=_(
            "Leave empty to show this section to everyone. Select groups to restrict it to authenticated members."
        ),
    )
    order = models.PositiveIntegerField(default=0, verbose_name=_("Display Order"))
    background_style = models.CharField(
        max_length=20,
        choices=BackgroundStyle.choices,
        default=BackgroundStyle.DEFAULT,
        verbose_name=_("Background Style"),
    )
    full_width = models.BooleanField(
        default=False,
        verbose_name=_("Full Width"),
        help_text=_("If enabled, the section content can span the full content column width."),
    )
    show_separator_after = models.BooleanField(
        default=False,
        verbose_name=_("Show Separator After"),
        help_text=_("Displays a separator after this section."),
    )

    class Meta:
        ordering = ("order", "id")
        verbose_name = _("Page Section")
        verbose_name_plural = _("Page Sections")
        indexes = [
            models.Index(fields=["page", "order"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(section_type="page", linked_page__isnull=False)
                | ~Q(section_type="page"),
                name="pagesection_page_type_requires_linked_page",
            ),
            models.CheckConstraint(
                condition=Q(section_type__in=["hero", "widget_zone"], widget_zone__isnull=False)
                | ~Q(section_type__in=["hero", "widget_zone"]),
                name="pagesection_widget_types_require_widget_zone",
            ),
            models.CheckConstraint(
                condition=Q(linked_page__isnull=True) | ~Q(page=F("linked_page")),
                name="pagesection_linked_page_not_self",
            ),
        ]

    def __str__(self):
        return self.translated_internal_title

    def is_visible_for_user(self, user):
        """Return whether this section can be displayed to ``user``."""
        if not self.allowed_groups.exists():
            return True
        if not user or not user.is_authenticated:
            return False
        return self.allowed_groups.filter(user=user).exists()

    def clean(self):
        errors = {}

        if self.section_type == self.SectionType.PAGE and not self.linked_page_id:
            errors["linked_page"] = _(
                "Embedded page sections must select a linked page.",
            )

        if self.section_type in {self.SectionType.HERO, self.SectionType.WIDGET_ZONE} and not self.widget_zone_id:
            errors["widget_zone"] = _(
                "Hero and widget-zone sections must select a widget zone.",
            )

        if self.linked_page_id and self.page_id and self.linked_page_id == self.page_id:
            errors["linked_page"] = _(
                "A page section cannot embed its own page.",
            )

        if errors:
            raise ValidationError(errors)

    @property
    def translated_internal_title(self):
        return self.safe_translation_getter("internal_title", any_language=True) or str(_("Untitled"))

    @property
    def translated_heading(self):
        return self.safe_translation_getter("heading", any_language=True) or ""

    @property
    def translated_content(self):
        return self.safe_translation_getter("content", any_language=True) or ""

    @property
    def translated_button_text(self):
        return self.safe_translation_getter("button_text", any_language=True) or ""

    @property
    def translated_button_url(self):
        return self.safe_translation_getter("button_url", any_language=True) or ""

    @property
    def embedded_page_heading(self):
        if self.translated_heading:
            return self.translated_heading
        if self.linked_page:
            return self.linked_page.translated_title
        return ""
