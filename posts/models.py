from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields
from django.urls import reverse
from django.utils.text import get_valid_filename, slugify
from django.utils import timezone
from django.utils.translation import get_language, override
from categories.models import Category 
from tags.models import Tag, TaggedPost

User = get_user_model()


# ---------------------------------------------------------------------------
# Legacy migration compatibility helpers.
# These are intentionally kept so historical migrations that import
# `posts.models.post_featured_image_upload_to` and
# `posts.models.post_social_image_upload_to` remain importable forever.
# They are NOT used by the active Post model architecture anymore.
# ---------------------------------------------------------------------------
def _post_image_upload_path(instance, filename, suffix=''):
    extension = ''
    if '.' in filename:
        extension = f".{filename.rsplit('.', 1)[1].lower()}"

    slug = (
        getattr(instance, 'slug', '')
        or slugify(getattr(instance, 'title', ''))
        or 'post-image'
    )
    basename = get_valid_filename(slug)
    max_basename_length = max(20, 100 - len('gallery/') - len(suffix) - len(extension))
    basename = basename[:max_basename_length]
    return f'gallery/{basename}{suffix}{extension}'


def post_featured_image_upload_to(instance, filename):
    return _post_image_upload_path(instance, filename)


def post_social_image_upload_to(instance, filename):
    return _post_image_upload_path(instance, filename, suffix='-social')


class Post(TranslatableModel):
    """
    Represents a blog post with multilingual support using django-parler.
    This model is the central content unit in the 'posts' app.
    """

    translations = TranslatedFields(
        title=models.CharField(
            max_length=250,
            verbose_name=_("Title")
        ),
        slug=models.SlugField(
            max_length=250,
            unique=False,  # Parler handles uniqueness per language
            verbose_name=_("Slug")
        ),
        summary=models.CharField(
            max_length=280,
            blank=True,
            verbose_name=_("Summary"),
            help_text=_("Short text used as the social sharing description.")
        ),
        content=models.TextField(
            verbose_name=_("Content")
        ),
        meta_title=models.CharField(
            max_length=70,
            blank=True,
            null=True,
            verbose_name=_("Meta Title")
        ),
        meta_description=models.CharField(
            max_length=160,
            blank=True,
            null=True,
            verbose_name=_("Meta Description")
        ),
        featured_image_asset=models.ForeignKey(
            "gallery.Image",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="+",
            verbose_name=_("Featured image (library)"),
            help_text=_("Optional gallery row for the featured image; overrides the upload below when set."),
        ),
        featured_image_alt=models.CharField(
            max_length=250,
            blank=True,
            verbose_name=_("Featured image alternative text"),
            help_text=_("Describe the image. If empty, the post title is used."),
        ),
        social_image_asset=models.ForeignKey(
            "gallery.Image",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="+",
            verbose_name=_("Social image (library)"),
            help_text=_("Optional gallery row for the square social image; overrides the upload below when set."),
        ),
        social_image_alt=models.CharField(
            max_length=250,
            blank=True,
            verbose_name=_("Social image alternative text"),
            help_text=_("Describe the image. If empty, the post title is used."),
        ),
        mobile_image_asset=models.ForeignKey(
            "gallery.Image",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="+",
            verbose_name=_("Mobile image (library)"),
            help_text=_("Optional gallery row for a vertical 9:16 image used in mobile-first widgets."),
        ),
        mobile_image_alt=models.CharField(
            max_length=250,
            blank=True,
            verbose_name=_("Mobile image alternative text"),
            help_text=_("Describe the image. If empty, the post title is used."),
        ),
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="translated_posts",
        verbose_name=_("Author")
    )

    published_date = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Published Date")
    )

    status = models.CharField(
        max_length=10,
        choices=[
            ('draft', _("Draft")),
            ('published', _("Published")),
            ('archived', _("Archived")),
        ],
        default='draft',
        verbose_name=_("Status")
    )

    views_count = models.PositiveIntegerField(default=0, verbose_name=_("View Count"))
    editor_rating = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Editor's Rating"),
        help_text=_("A score from 0-100. Higher numbers can be used for ordering or editor’s picks.")
    )
    show_in_post_grids = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Show in Post Grids"),
        help_text=_("Controls whether this post can appear in homepage/category grid widgets.")
    )
    migrated = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Migrated"),
        help_text=_("Internal admin flag used to avoid exporting or importing this post more than once.")
    )
    short_code = models.SlugField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        verbose_name=_("Short link code"),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    tags = models.ManyToManyField(
        Tag,
        through=TaggedPost,
        related_name="posts",
        verbose_name=_("Tags"),
        blank=True,
        help_text=_("Tags assigned to this post. Managed via TaggedPost intermediate model."),
    )

    # --- CORRECTED CATEGORY RELATIONSHIP ---
    # Using a ManyToManyField is simpler and more efficient for querying than GenericRelation.
    categories = models.ManyToManyField(
        Category,
        blank=True,
        verbose_name=_("Categories"),
        related_name="posts_posts"
    )

    class Meta:
        verbose_name = _("Post")
        verbose_name_plural = _("Posts")
        ordering = ['-published_date']

    def __str__(self):
        return str(self.safe_translation_getter("title", any_language=True) or _("(No title)"))

    def save(self, *args, **kwargs):
        """Assign a stable, non-editable short code once the post has an ID."""
        super().save(*args, **kwargs)
        if self.short_code:
            return

        short_code = f"p-{self.pk}"
        type(self).objects.filter(pk=self.pk).filter(
            models.Q(short_code__isnull=True) | models.Q(short_code="")
        ).update(short_code=short_code)
        self.short_code = short_code

    def get_short_path(self):
        if not self.short_code:
            return ""
        return reverse("short_post_redirect", kwargs={"short_code": self.short_code})

    def get_short_url(self):
        short_path = self.get_short_path()
        if not short_path:
            return ""
        base_url = str(getattr(settings, "PUBLIC_SITE_URL", "https://tvtente.com")).rstrip("/")
        return f"{base_url}{short_path}"

    @staticmethod
    def _file_from_gallery_asset(asset):
        if asset is None:
            return None
        f = getattr(asset, "image", None)
        if f and getattr(f, "name", ""):
            return f
        return None

    def get_featured_image(self, language_code=None):
        asset = self.safe_translation_getter(
            "featured_image_asset",
            language_code=language_code,
            any_language=False,
        )
        return self._file_from_gallery_asset(asset)

    def _image_alt(self, field_name, language_code=None):
        return (
            self.safe_translation_getter(field_name, language_code=language_code, any_language=False)
            or self.safe_translation_getter("title", language_code=language_code, any_language=True)
            or ""
        )

    def get_featured_image_alt(self, language_code=None):
        return self._image_alt("featured_image_alt", language_code)

    def get_social_image(self, language_code=None):
        asset = self.safe_translation_getter(
            "social_image_asset",
            language_code=language_code,
            any_language=False,
        )
        from_asset = self._file_from_gallery_asset(asset)
        if from_asset:
            return from_asset
        return self.get_featured_image(language_code=language_code)

    def get_social_image_alt(self, language_code=None):
        return self._image_alt("social_image_alt", language_code)

    def get_mobile_image(self, language_code=None):
        asset = self.safe_translation_getter(
            "mobile_image_asset",
            language_code=language_code,
            any_language=False,
        )
        from_asset = self._file_from_gallery_asset(asset)
        if from_asset:
            return from_asset
        return self.get_featured_image(language_code=language_code)

    def get_mobile_image_alt(self, language_code=None):
        return self._image_alt("mobile_image_alt", language_code)

    def has_dedicated_square_image(self, language_code=None):
        """True when a dedicated square social asset exists."""
        asset = self.safe_translation_getter(
            "social_image_asset",
            language_code=language_code,
            any_language=False,
        )
        return bool(self._file_from_gallery_asset(asset))

    def get_tags_for_language(self, language_code=None):
        language_code = language_code or get_language()
        return Tag.objects.filter(
            post_links__post=self,
            post_links__language=language_code,
        ).distinct()

    def get_absolute_url(self):
        slug = (
            self.safe_translation_getter('slug', any_language=False)
        )
        return reverse('posts:post_detail', kwargs={
            'year': self.published_date.year,
            'month': self.published_date.month,
            'day': self.published_date.day,
            'slug': slug,
        })

    def get_absolute_url_for_language(self, language_code):
        slug = (
            self.safe_translation_getter('slug', language_code=language_code, any_language=False)
        )
        with override(language_code):
            return reverse('posts:post_detail', kwargs={
                'year': self.published_date.year,
                'month': self.published_date.month,
                'day': self.published_date.day,
                'slug': slug,
            })


class PostContentBlock(models.Model):
    """An ordered visual section of a post, or a reference to another post."""

    class BlockType(models.TextChoices):
        CONTENT = "content", _("Content with image")
        RELATED_POST = "related_post", _("Reference to another post")

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="content_blocks",
        verbose_name=_("Post"),
    )
    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default="es",
        verbose_name=_("Content language"),
    )
    order = models.PositiveSmallIntegerField(default=1, verbose_name=_("Display order"))
    block_type = models.CharField(
        max_length=20,
        choices=BlockType.choices,
        default=BlockType.CONTENT,
        verbose_name=_("Block type"),
    )
    anchor = models.SlugField(
        max_length=120,
        blank=True,
        verbose_name=_("Section anchor"),
        help_text=_("Optional URL fragment for linking directly to this section."),
    )
    heading = models.CharField(max_length=250, blank=True, verbose_name=_("Section title"))
    content = models.TextField(blank=True, verbose_name=_("Section content"))
    image_asset = models.ForeignKey(
        "gallery.Image",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="post_content_blocks",
        verbose_name=_("16:9 image from media library"),
    )
    image_alt = models.CharField(
        max_length=250,
        blank=True,
        verbose_name=_("Image alternative text"),
        help_text=_("Describe the image. If empty, the section title or post title is used."),
    )
    show_in_listings = models.BooleanField(
        default=False,
        verbose_name=_("Show in listings and search"),
        help_text=_(
            "Show this complete visual section as a mini-post in latest entries "
            "and search results."
        ),
    )
    related_post = models.ForeignKey(
        Post,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="referenced_by_content_blocks",
        verbose_name=_("Referenced post"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("language", "order", "pk")
        verbose_name = _("Post content block")
        verbose_name_plural = _("Post content blocks")

    def __str__(self):
        return self.heading or f"{self.post} · {self.order}"

    def clean(self):
        super().clean()
        if self.heading and not self.anchor:
            self.anchor = slugify(self.heading)
        errors = {}
        if self.block_type == self.BlockType.CONTENT:
            if not self.content.strip():
                errors["content"] = _("A content block needs text.")
            if not self.image_asset_id and not getattr(self, "_has_staged_image", False):
                errors["image_asset"] = _("A content block needs a 16:9 image.")
            if self.related_post_id:
                errors["related_post"] = _("Content blocks cannot also reference another post.")
        elif self.block_type == self.BlockType.RELATED_POST:
            if not self.related_post_id:
                errors["related_post"] = _("Select the post to reference.")
            elif self.related_post_id == self.post_id:
                errors["related_post"] = _("A post cannot reference itself.")
            if self.image_asset_id:
                errors["image_asset"] = _("Referenced posts use their own featured image.")
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Programmatic and direct-model saves get the same sensible default
        # as the Admin form. Editors may always replace it before saving.
        if self.heading and not self.anchor:
            self.anchor = slugify(self.heading)
        super().save(*args, **kwargs)

    @property
    def image_url(self):
        if not self.image_asset:
            return ""
        return self.image_asset.get_image_url()

    @property
    def image_alt_or_default(self):
        return self.image_alt or self.heading or self.post.safe_translation_getter("title", any_language=True) or ""

    @property
    def is_renderable(self):
        """Keep incomplete records (including direct DB imports) off public pages."""
        if self.block_type == self.BlockType.CONTENT:
            return bool(self.content.strip() and self.image_url)
        if self.block_type == self.BlockType.RELATED_POST:
            return bool(self.related_post_id)
        return False

    @property
    def is_listable(self):
        """A public mini-post must be complete and explicitly enabled."""
        return bool(
            self.show_in_listings
            and self.block_type == self.BlockType.CONTENT
            and self.heading.strip()
            and self.anchor_or_default
            and self.is_renderable
        )

    @property
    def anchor_or_default(self):
        return self.anchor or f"post-block-{self.pk}"


class PostDailyMetric(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='daily_metrics',
        verbose_name=_("Post")
    )
    date = models.DateField(verbose_name=_("Date"))
    views_count = models.PositiveIntegerField(default=0, verbose_name=_("Daily View Count"))

    class Meta:
        verbose_name = _("Post Daily Metric")
        verbose_name_plural = _("Post Daily Metrics")
        unique_together = ('post', 'date')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['post', 'date']),
        ]

    def __str__(self):
        return f"{self.post} — {self.date}: {self.views_count}"


class PostPointAllocation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="post_point_allocations",
        verbose_name=_("User"),
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="point_allocations",
        verbose_name=_("Post"),
    )
    date = models.DateField(
        default=timezone.localdate,
        verbose_name=_("Date"),
    )
    points = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Points"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Post point allocation")
        verbose_name_plural = _("Post point allocations")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post", "date"],
                name="unique_post_point_allocation_per_day",
            )
        ]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["post", "date"]),
            models.Index(fields=["user", "date"]),
        ]

    def __str__(self):
        return f"{self.user} -> {self.post} ({self.points}) [{self.date}]"


class PostFavorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="post_favorites",
        verbose_name=_("User"),
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name=_("Post"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Post favorite")
        verbose_name_plural = _("Post favorites")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_post_favorite",
            )
        ]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["post", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user} ❤ {self.post}"
