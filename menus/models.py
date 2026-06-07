# File: menus/models.py
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group

# Third-party imports
from mptt.models import MPTTModel, TreeForeignKey
from parler.models import TranslatableModel, TranslatedFields

# Local application imports (ensure these models exist in pages.models and categories.models)
from pages.models import Page # For linking to specific internal pages
from categories.models import Category
from .managers import MenuItemManager


class Menu(TranslatableModel):
    """
    Represents a container for menu items, defining a specific menu location.
    Examples: 'Main Menu', 'Footer Menu', 'Social Media Links'.
    """
    translations = TranslatedFields(
        title=models.CharField(
            max_length=100,
            verbose_name=_("Menu Title"),
        ),
        meta={
            "unique_together": [("language_code", "title")],
        },
    )
    slug = models.SlugField(max_length=100, unique=True, verbose_name=_("Slug"))

    class Meta:
        verbose_name = _("Menu")
        verbose_name_plural = _("Menus")

    def __str__(self):
        return self.safe_translation_getter("title", any_language=True) or self.slug

    @property
    def translated_title(self):
        return self.safe_translation_getter("title", any_language=True) or self.slug


class MenuItem(MPTTModel, TranslatableModel):
    """
    Represents a single, hierarchical item within a specific Menu.
    It can be a simple link, or a dynamic placeholder that generates sub-items
    (e.g., a "Post Categories" dropdown).

    Visibility rule:
    - If allowed_groups is empty, the item is visible to everyone.
    - If allowed_groups has one or more groups, only authenticated users
      belonging to at least one of those groups can see the item.
    """

    # Enum for defining the type of link this menu item represents.
    class LinkType(models.TextChoices):
        URL = 'url', _('Manual URL')
        HOME = 'home', _('Home Page')
        PAGE = 'page', _('Single Page')
        NOTEBOOK_LIST = 'notebook_list', _('Notebook List')
        PROFILE_EDIT = 'profile_edit', _('Edit Profile')
        PROFILE_CV = 'profile_cv', _('Edit CV')
        PUBLIC_PROFILE = 'public_profile', _('Public Profile')
        INBOX = 'inbox', _('Inbox')
        FOLLOWING = 'following', _('Following Posts')
        FAVORITES = 'favorites', _('Favorite Posts')
        MY_ORDERS = 'my_orders', _('My Orders')
        CHANGE_PASSWORD = 'change_password', _('Change Password')
        CATEGORY = 'category', _('Single Category')
        POST_LIST = 'post_list', _('Post List (Dropdown)')
        # These types are placeholders for dynamic content generation in the frontend.
        ALL_BLOG_CATEGORIES = 'all_blog_categories', _('Post Categories Tree (Dropdown)')
        IMPORTANT_PAGES = 'important_pages', _('Important Pages List (Dropdown)')

    class PostListType(models.TextChoices):
        LATEST = 'latest', _('Latest Posts')
        NEW = 'new', _('New Posts Today')
        MOST_DISCUSSED = 'most_discussed', _('Most Discussed Posts')
        TRENDING = 'trending', _('Trending Posts')
        RECOMMENDED = 'recommended', _('Recommended Posts')

    # --- Core Relationships ---
    # The Menu container this item belongs to.
    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Menu")
    )

    # The 'parent' field enables hierarchical (nested) menu structures,
    # provided by django-mptt.
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        db_index=True,
        verbose_name=_("Parent Menu Item"),
        help_text=_("Select a parent item to nest this menu item within it.")
    )

    # --- Visibility by Django Groups / Roles ---
    allowed_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="visible_menu_items",
        verbose_name=_("Visible for groups"),
        help_text=_(
            "Leave empty to show this menu item to everyone. "
            "Select one or more groups to restrict visibility."
        ),
    )

    # --- Item Content and Order ---
    translations = TranslatedFields(
        title=models.CharField(
            max_length=100,
            verbose_name=_("Link Text"),
        ),
    )
    order = models.PositiveIntegerField(default=0, verbose_name=_("Display Order"))

    # --- Link Configuration ---
    # Specifies how the menu item will generate its URL or dynamic content.
    link_type = models.CharField(
        max_length=50,
        choices=LinkType.choices,
        default=LinkType.URL,
        verbose_name=_("Link Type"),
        help_text=_("Determines how this menu item behaves: a direct link, or a dynamic content generator.")
    )

    # Conditional link fields. Only one of these should typically be filled.
    link_page = models.ForeignKey(
        Page,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Page Link"),
        help_text=_("Link to a specific internal page. Only used if Link Type is 'Single Page'.")
    )

    link_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Category Link"),
        help_text=_("Link to a specific category. Only used if Link Type is 'Single Category'.")
    )

    link_url = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Manual URL"),
        help_text=_(
            "Use for external URLs (e.g., 'https://google.com') or custom internal paths "
            "(e.g., '/blog/'). Only used if Link Type is 'Manual URL'."
        )
    )

    post_list_type = models.CharField(
        max_length=50,
        choices=PostListType.choices,
        blank=True,
        verbose_name=_("Post List Type"),
        help_text=_("Determines which posts are shown when Link Type is 'Post List'.")
    )

    dynamic_items_limit = models.PositiveIntegerField(
        default=5,
        verbose_name=_("Dynamic Items Limit"),
        help_text=_("Maximum number of generated items for dynamic dropdowns.")
    )

    icon_class = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Icon Class"),
        help_text=_("FontAwesome class (e.g., 'fas fa-home') to display an icon next to the link.")
    )

    objects = MenuItemManager()

    class MPTTMeta:
        """
        MPTT-specific options for ordering nodes within the tree.

        Include `menu` before `order` so root items from different menus are not
        treated as siblings during MPTT automatic ordering.
        """
        order_insertion_by = ['menu', 'order']

    class Meta:
        verbose_name = _("Menu Item")
        verbose_name_plural = _("Menu Items")
        ordering = ['menu', 'tree_id', 'lft', 'order']

    def __str__(self):
        """Returns an indented string representation useful for admin display."""
        title = self.translated_title
        return f"{'--' * self.level} {title}"

    @property
    def translated_title(self):
        return self.safe_translation_getter("title", any_language=True) or str(_("Untitled"))

    @property
    def is_account_management_menu(self):
        """
        Detect the legacy top-level account dropdown so the UI can relocate it
        to the authenticated avatar menu without depending on translated titles.
        """
        if self.parent_id:
            return False

        account_url_suffixes = {
            "/accounts/profile/edit/",
            "/accounts/profile/cv/",
        }

        for child in self.children.all():
            child_url = (child.get_url() or "").strip()
            if not child_url:
                continue
            if any(child_url.endswith(suffix) for suffix in account_url_suffixes):
                return True
        return False

    def clean(self):
        super().clean()

        errors = {}

        if self.link_type == self.LinkType.URL and not self.link_url:
            errors['link_url'] = _("Manual URL is required for this link type.")
        elif self.link_type == self.LinkType.PAGE and not self.link_page:
            errors['link_page'] = _("Page Link is required for this link type.")
        elif self.link_type == self.LinkType.CATEGORY and not self.link_category:
            errors['link_category'] = _("Category Link is required for this link type.")
        elif self.link_type == self.LinkType.POST_LIST and not self.post_list_type:
            errors['post_list_type'] = _("Post List Type is required for this link type.")

        if errors:
            raise ValidationError(errors)

    def is_visible_for_user(self, user):
        """
        Returns whether this menu item should be visible for the given user.

        Rule:
        - No allowed groups selected: visible to everyone.
        - Allowed groups selected: visible only to authenticated users who belong
          to at least one selected group.
        """
        if self.link_type in {
            self.LinkType.PROFILE_EDIT,
            self.LinkType.PROFILE_CV,
            self.LinkType.PUBLIC_PROFILE,
            self.LinkType.INBOX,
            self.LinkType.FOLLOWING,
            self.LinkType.FAVORITES,
            self.LinkType.MY_ORDERS,
            self.LinkType.CHANGE_PASSWORD,
        }:
            if not user or not user.is_authenticated:
                return False
            if self.link_type == self.LinkType.PUBLIC_PROFILE and not user.has_perm("accounts.list_public_profile"):
                return False

        allowed_group_ids = self.allowed_groups.values_list("pk", flat=True)

        if not allowed_group_ids.exists():
            return True

        if not user or not user.is_authenticated:
            return False

        return user.groups.filter(pk__in=allowed_group_ids).exists()

    def get_url_for_user(self, user=None):
        """
        Generates the actual URL for the menu item based on its link_type.
        Returns a placeholder '#' if no valid URL is configured.
        """
        if self.link_type == self.LinkType.HOME:
            return reverse('home')

        elif self.link_type == self.LinkType.PAGE and self.link_page:
            return self.link_page.get_absolute_url()

        elif self.link_type == self.LinkType.NOTEBOOK_LIST:
            return reverse('notebooks:notebook_list')

        elif self.link_type == self.LinkType.PROFILE_EDIT:
            return reverse('accounts:profile_edit')

        elif self.link_type == self.LinkType.PROFILE_CV:
            return reverse('accounts:profile_cv_edit')

        elif self.link_type == self.LinkType.PUBLIC_PROFILE:
            if user and getattr(user, "is_authenticated", False):
                return reverse('accounts:public_profile', kwargs={'username': user.username})
            return "#"

        elif self.link_type == self.LinkType.INBOX:
            return reverse('accounts:inbox')

        elif self.link_type == self.LinkType.FOLLOWING:
            return reverse('posts:following_posts')

        elif self.link_type == self.LinkType.FAVORITES:
            return reverse('posts:favorite_posts')

        elif self.link_type == self.LinkType.MY_ORDERS:
            return reverse('shop:my_orders')

        elif self.link_type == self.LinkType.CHANGE_PASSWORD:
            return reverse('account_change_password')

        elif self.link_type == self.LinkType.CATEGORY and self.link_category:
            return self.link_category.get_posts_url()

        elif self.link_type == self.LinkType.URL and self.link_url:
            return self.link_url

        elif self.link_type == self.LinkType.POST_LIST and self.post_list_type:
            return reverse('posts:post_list_by_type', kwargs={'list_type': self.post_list_type})

        elif self.link_type == self.LinkType.ALL_BLOG_CATEGORIES and self.link_category:
            return self.link_category.get_posts_url()
        elif self.link_type == self.LinkType.ALL_BLOG_CATEGORIES:
            return reverse("categories:category_list")

        # For dynamic link types the URL is often '#'
        # as clicking the top-level item expands the dropdown, not navigates.
        return "#"

    def get_url(self):
        return self.get_url_for_user()
