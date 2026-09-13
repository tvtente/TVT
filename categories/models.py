# File: categories/models.py
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language, override
from mptt.models import MPTTModel, TreeForeignKey
from parler.models import TranslatableModel, TranslatedFields

from .managers import CategoryManager


class Category(MPTTModel, TranslatableModel):
    """
    A universal, hierarchical category model using a simple self-referencing
    ForeignKey to handle nesting.
    """
    translations = TranslatedFields(
        name=models.CharField(
            max_length=100,
            verbose_name=_("Name"),
        ),
        slug=models.SlugField(
            max_length=100,
            verbose_name=_("Slug"),
        ),
        description=models.TextField(
            blank=True,
            verbose_name=_("Description"),
            help_text=_("An optional description for the category."),
        ),
        meta_title=models.CharField(
            max_length=70,
            blank=True,
            null=True,
            verbose_name=_("Meta Title (SEO)"),
            help_text=_("A precise title for search engine results (max 70 chars)."),
        ),
        meta_description=models.CharField(
            max_length=160,
            blank=True,
            null=True,
            verbose_name=_("Meta Description (SEO)"),
            help_text=_("A short description for search engine previews (max 160 chars)."),
        ),
        meta={
            "unique_together": [("language_code", "slug")],
        },
    )
    
    # Simple hierarchy field
    parent = TreeForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name=_("Parent Category"),
        help_text=_("Select a parent to create a sub-category.")
    )
    menu_icon_class = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Menu icon class"),
        help_text=_(
            "Optional Font Awesome classes, for example: fas fa-shield-alt."
        ),
    )
    is_visible = models.BooleanField(
        default=True,
        verbose_name=_("Show"),
        help_text=_(
            "Show this category and its associated posts in public category trees, menus, and listings."
        ),
    )
    
    objects = CategoryManager()

    class Meta:
        """ Standard Django model metadata. """
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["tree_id", "lft"]

    class MPTTMeta:
        order_insertion_by = []

    def __str__(self):
        """ Provides a clear representation in the admin, showing hierarchy. """
        name = self.safe_translation_getter("name", any_language=True) or str(_("Untitled"))
        if self.parent:
            parent_name = self.parent.safe_translation_getter("name", any_language=True) or str(_("Untitled"))
            return f"{parent_name} -> {name}"
        return name

    @property
    def translated_title(self):
        return self.safe_translation_getter("name", any_language=True) or str(_("Untitled"))
    
    @property
    def is_blog_category(self):
        """Checks if this category or any child category is used for posts."""
        if not hasattr(self, 'posts_posts'):
            return False
        return self.get_descendants(include_self=True).filter(
            posts_posts__status='published',
        ).exists()

    def get_absolute_url(self):
        """
        Generates the correct URL for the category's list page.
        """
        language = get_language()

        if self.is_blog_category:
            return self.get_posts_url()
        else:
            # Fallback to the pages category list view
            translated_slug = (
                self.safe_translation_getter("slug", language_code=language, any_language=False)
                or self.safe_translation_getter("slug", any_language=True)
            )
            return reverse('pages:pages_by_category', args=[translated_slug])

    def get_posts_url(self):
        """
        Generates the post-list URL for this category in the active language.
        Used by menus that explicitly link to post categories.
        """
        language = get_language()
        translated_slug = (
            self.safe_translation_getter("slug", language_code=language, any_language=False)
            or self.safe_translation_getter("slug", any_language=True)
        )
        return reverse('posts:posts_by_category', args=[translated_slug])

    def get_absolute_url_for_language(self, language_code):
        translated_slug = (
            self.safe_translation_getter("slug", language_code=language_code, any_language=False)
            or self.safe_translation_getter("slug", any_language=True)
        )
        with override(language_code):
            if self.is_blog_category:
                return reverse('posts:posts_by_category', args=[translated_slug])
            return reverse('pages:pages_by_category', args=[translated_slug])
