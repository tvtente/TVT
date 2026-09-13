# File: categories/views.py
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import get_language, gettext

from posts.models import Post

from .models import Category


def get_category_by_slug(category_slug):
    language = get_language()
    category = (
        Category.objects.language(language)
        .translated(language, slug=category_slug)
        .filter(is_visible=True)
        .distinct()
        .first()
    )
    if category:
        return category

    return get_object_or_404(
        Category.objects.filter(is_visible=True).prefetch_related("translations").distinct(),
        translations__slug=category_slug,
    )


def category_tree_view(request):
    """
    Provides the root nodes for rendering a full category tree.
    """
    # We fetch ONLY the top-level categories.
    root_nodes = (
        Category.objects.language(get_language())
        .filter(parent__isnull=True, is_visible=True)
        .distinct()
    )

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": "", "label": gettext("Categories")},
    ]

    context = {
        'categories': root_nodes,
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'categories/category_tree.html', context)

def build_category_breadcrumbs(category):
    path = []
    current = category
    language = get_language()

    while current:
        translated_slug = (
            current.safe_translation_getter(
                "slug",
                language_code=language,
                any_language=False,
            )
            or current.safe_translation_getter("slug", any_language=True)
        )
        translated_name = (
            current.safe_translation_getter(
                "name",
                language_code=language,
                any_language=False,
            )
            or current.safe_translation_getter("name", any_language=True)
        )
        path.append({
            "url": reverse("posts:posts_by_category", args=[translated_slug]),
            "label": translated_name,
        })
        current = current.parent
    return reversed(path)

def posts_by_category_view(request, category_slug):
    category = get_category_by_slug(category_slug)

    posts = Post.objects.filter(categories=category, status='published').order_by('-published_date')

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": reverse("posts:post_list"), "label": gettext("Posts")},
    ]
    breadcrumbs += list(build_category_breadcrumbs(category))

    return render(request, "posts/posts_by_category.html", {
        "category": category,
        "posts": posts,
        "breadcrumbs": breadcrumbs,
    })
