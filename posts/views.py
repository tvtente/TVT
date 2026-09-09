# File: posts/views.py

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import F, Q
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _, gettext, get_language, override
from parler.utils.context import switch_language

from core.pagination import get_site_config_int, paginate_queryset
from .models import Post, PostContentBlock, PostDailyMetric
from .forms import PostPointAllocationForm
from .selectors import (
    POST_LIST_TYPES,
    get_posts_for_list_type,
    get_published_posts_queryset,
    get_untranslated_post_cards,
)
from .services import (
    can_user_assign_post_points,
    get_max_points_per_post,
    get_post_favorites_total,
    get_post_points_summary,
    get_post_points_total,
    is_post_favorited_by_user,
    set_post_points_for_day,
    toggle_post_favorite,
)
from categories.views import get_category_by_slug
from accounts.models import UserFollow
from accounts.services import create_post_favorited_notification
from comments.forms import CommentForm
from comments.models import Comment
from site_settings.models import SiteConfiguration
from tags.models import Tag, TagDailyMetric
from sources.models import Citation


logger = logging.getLogger(__name__)


def _post_points_anchor(post):
    return f"{post.get_absolute_url()}#post-points"


def _is_ajax_request(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def post_list_view(request, list_type=None):
    """
    📚 Lists published posts with pagination and optional dynamic ordering.
    """
    if list_type and list_type not in POST_LIST_TYPES:
        raise Http404(gettext("Post list not found."))

    all_posts = get_posts_for_list_type(list_type, language_code=get_language())

    posts_per_page = get_site_config_int(
        "blog_items_per_page",
        6,
        logger=logger,
        warning_message="⚠️ SiteConfiguration missing. Using default of 6 posts per page.",
    )
    posts = paginate_queryset(all_posts, request.GET.get("page"), posts_per_page)

    list_config = POST_LIST_TYPES.get(list_type)
    page_title = list_config["title"] if list_config else _("Published Posts")
    page_description = (
        list_config["description"]
        if list_config
        else _("Latest news and articles from the Tavata platform.")
    )

    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": reverse("posts:post_list") if list_type else "", "label": _("Posts")},
    ]

    if list_type:
        breadcrumbs.append({"url": "", "label": page_title})

    return render(
        request,
        "posts/post_list.html",
        {
            "posts": posts,
            "breadcrumbs": breadcrumbs,
            "page_title": page_title,
            "page_description": page_description,
            "post_list_type": list_type,
            "untranslated_post_cards": get_untranslated_post_cards(),
        },
    )


@login_required
def following_posts_view(request):
    followed_user_ids = UserFollow.objects.filter(
        follower=request.user,
    ).values_list("followed_id", flat=True)

    all_posts = (
        get_published_posts_queryset().filter(
            author_id__in=followed_user_ids,
        )
        .select_related("author", "author__profile")
        .order_by("-published_date")
    )

    posts_per_page = get_site_config_int(
        "blog_items_per_page",
        6,
        logger=logger,
        warning_message="⚠️ SiteConfiguration missing. Using default of 6 posts per page.",
    )
    posts = paginate_queryset(all_posts, request.GET.get("page"), posts_per_page)

    page_title = _("Following")
    page_description = _("Latest posts from authors you follow.")
    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": reverse("posts:post_list"), "label": _("Posts")},
        {"url": "", "label": page_title},
    ]

    return render(
        request,
        "posts/post_list.html",
        {
            "posts": posts,
            "breadcrumbs": breadcrumbs,
            "page_title": page_title,
            "page_description": page_description,
            "post_list_type": "following",
        },
    )


@login_required
def favorite_posts_view(request):
    all_posts = (
        get_published_posts_queryset().filter(
            favorites__user=request.user,
        )
        .select_related("author", "author__profile")
        .distinct()
        .order_by("-favorites__created_at", "-published_date")
    )

    posts_per_page = get_site_config_int(
        "blog_items_per_page",
        6,
        logger=logger,
        warning_message="⚠️ SiteConfiguration missing. Using default of 6 posts per page.",
    )
    posts = paginate_queryset(all_posts, request.GET.get("page"), posts_per_page)

    page_title = _("My favorites")
    page_description = _("Posts you saved to revisit later.")
    breadcrumbs = [
        {"url": "/", "label": _("Home")},
        {"url": reverse("posts:post_list"), "label": _("Posts")},
        {"url": "", "label": page_title},
    ]

    return render(
        request,
        "posts/post_list.html",
        {
            "posts": posts,
            "breadcrumbs": breadcrumbs,
            "page_title": page_title,
            "page_description": page_description,
            "post_list_type": "favorites",
        },
    )


@login_required
def toggle_post_favorite_view(request, year, month, day, slug):
    if request.method != "POST":
        raise Http404(gettext("Post not found."))

    language = get_language()
    post = get_object_or_404(
        Post.objects.language(language).filter(
            translations__language_code=language,
            translations__slug=slug,
            published_date__year=year,
            published_date__month=month,
            published_date__day=day,
            status="published",
        ).distinct()
    )

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or f"{post.get_absolute_url()}#post-points"
    )

    try:
        is_favorited = toggle_post_favorite(request.user, post)
    except ValidationError as exc:
        message = exc.messages[0]
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "error": message}, status=400)
        messages.error(request, message)
        return HttpResponseRedirect(next_url)

    total_favorites = get_post_favorites_total(post)
    if is_favorited:
        create_post_favorited_notification(post=post, actor=request.user)
        message = gettext("You added this post to your favorites.")
    else:
        message = gettext("You removed this post from your favorites.")

    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "is_favorited": is_favorited,
                "favorites_total": total_favorites,
                "message": message,
            }
        )

    messages.success(request, message)
    return HttpResponseRedirect(next_url)


def get_category_depth(category):
    depth = 0
    current = category

    while current.parent:
        depth += 1
        current = current.parent

    return depth
def build_category_breadcrumbs(category):
    path = []
    current = category
    lang = get_language()

    while current:
        translated_slug = (
            current.safe_translation_getter(
                "slug",
                language_code=lang,
                any_language=False,
            )
            or current.safe_translation_getter("slug", any_language=True)
        )
        translated_name = (
            current.safe_translation_getter(
                "name",
                language_code=lang,
                any_language=False,
            )
            or current.safe_translation_getter("name", any_language=True)
        )
        path.append({
            "url": reverse(
                "posts:posts_by_category",
                args=[translated_slug],
            ),
            "label": translated_name,
        })
        current = current.parent

    return reversed(path)


def get_available_translation_urls(obj):
    """
    Returns translated URLs for all languages where the object has a translation.
    """
    available = []

    for language_code, language_label in settings.LANGUAGES:
        if not obj.has_translation(language_code):
            continue

        with override(language_code):
            with switch_language(obj, language_code):
                available.append({
                    "code": language_code,
                    "label": language_label,
                    "url": obj.get_absolute_url(),
                })

    return available


def post_detail_view(request, year, month, day, slug):
    """
    🌐 Displays a single multilingual post, handles view count increment,
    comment submission, and breadcrumb generation including categories.

    If the post exists in another language but not in the current one,
    renders a friendly language-unavailable page instead of a raw 404.
    """
    language = get_language()
    logger.debug(f"🌐 Language: {language} | Slug: {slug} | 📅 {year}-{month}-{day}")

    # 1. Retrieve post in current language
    try:
        post = (
            Post.objects
            .language(language)
            .prefetch_related(
                "categories",
                "translations",
                "tags__translations",
            )
            .get(
                translations__language_code=language,
                translations__slug=slug,
                published_date__year=year,
                published_date__month=month,
                published_date__day=day,
                status="published",
            )
        )

    except Post.DoesNotExist:
        candidate = (
            Post.objects
            .filter(
                translations__slug=slug,
                published_date__year=year,
                published_date__month=month,
                published_date__day=day,
                status="published",
            )
            .prefetch_related(
                "categories",
                "translations",
                "tags__translations",
            )
            .distinct()
            .first()
        )

        if not candidate:
            raise Http404(gettext("Post not found."))

        # If the requested language exists but uses a different slug,
        # redirect to the canonical translated URL.
        if candidate.has_translation(language):
            with override(language):
                with switch_language(candidate, language):
                    return redirect(candidate.get_absolute_url())

        return render(
            request,
            "core/translation_unavailable.html",
            {
                "content_kind": "post",
                "object": candidate,
                "available_translations": get_available_translation_urls(candidate),
                "title": gettext("Post not available in this language"),
                "meta_title": gettext("Post not available in this language"),
                "meta_description": gettext(
                    "This post exists, but it has not been translated into the selected language yet."
                ),
            },
            status=404,
        )

    # 2. Increment view count
    Post.objects.filter(pk=post.pk).update(
        views_count=F("views_count") + 1,
    )

    metric, _ = PostDailyMetric.objects.get_or_create(
        post=post,
        date=timezone.localdate(),
    )

    PostDailyMetric.objects.filter(pk=metric.pk).update(
        views_count=F("views_count") + 1,
    )

    post.refresh_from_db()

    # 3. Retrieve site config for comment approval
    try:
        config = SiteConfiguration.get_solo()
    except SiteConfiguration.DoesNotExist:
        logger.warning("⚠️ SiteConfiguration not found. Fallback approval=False.")

        class ConfigFallback:
            auto_approve_comments = False
            trusted_commenter_threshold = 3
            post_points_enabled = True
            daily_post_points_budget = 10
            max_points_per_post_per_day = 5
            allow_author_self_points = False
            post_points_min_account_age_days = 0

        config = ConfigFallback()

    # 4. Handle approved comments
    comments = Comment.objects.filter(
        post=post,
        is_approved=True,
    ).prefetch_related("translations")

    comments_anchor_url = f"{post.get_absolute_url()}#comments-section"
    post_points_anchor_url = _post_points_anchor(post)
    login_url = f"{reverse('login')}?{urlencode({'next': comments_anchor_url})}"
    points_login_url = f"{reverse('login')}?{urlencode({'next': post_points_anchor_url})}"

    # 5. Handle new comment submission
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.warning(
                request,
                gettext("Please log in to leave a comment."),
            )
            return HttpResponseRedirect(login_url)

        comment_form = CommentForm(
            request.POST,
            user=request.user,
        )

        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post

            profile = getattr(request.user, "profile", None)

            new_comment.user = request.user
            new_comment.author_name = (
                profile.get_display_name()
                if profile
                else request.user.username
            )
            new_comment.author_email = request.user.email
            new_comment.language = get_language()

            is_trusted = getattr(profile, "is_trusted_commenter", False)
            trusted_threshold = max(
                getattr(config, "trusted_commenter_threshold", 3),
                1,
            )

            approved_comment_count = Comment.objects.filter(
                user=request.user,
                is_approved=True,
            ).count()

            has_approved_history = approved_comment_count >= trusted_threshold

            new_comment.is_approved = (
                config.auto_approve_comments
                or is_trusted
                or has_approved_history
            )

            new_comment.save()

            if (
                new_comment.is_approved
                and has_approved_history
                and profile
                and not is_trusted
            ):
                profile.is_trusted_commenter = True
                profile.save(update_fields=["is_trusted_commenter"])

            msg = (
                gettext("✅ Thank you! Your comment has been published.")
                if new_comment.is_approved
                else gettext("🕓 Thank you! Your comment awaits moderation.")
            )

            messages.success(request, msg)

            return HttpResponseRedirect(comments_anchor_url)

        logger.warning(f"❌ Invalid comment submission: {comment_form.errors.as_json()}")

    else:
        comment_form = (
            CommentForm(user=request.user)
            if request.user.is_authenticated
            else None
        )

    # 6. Breadcrumbs with optional category
    categories = list(post.categories.all())
    category = None

    if categories:
        categories.sort(key=lambda c: (get_category_depth(c), c.id))
        category = categories[0]

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": reverse("posts:post_list"), "label": gettext("Posts")},
    ]

    if category:
        breadcrumbs += list(build_category_breadcrumbs(category))

    breadcrumbs.append({
        "url": "",
        "label": post.safe_translation_getter("title", any_language=True),
    })

    points_summary = get_post_points_summary(request.user, post, config)
    points_access = can_user_assign_post_points(request.user, post, config)
    max_points_per_post = get_max_points_per_post(config)
    author_profile = getattr(post.author, "profile", None)
    citations = (
        Citation.objects
        .filter(
            content_type=ContentType.objects.get_for_model(Post, for_concrete_model=False),
            object_id=post.pk,
            language=language,
        )
        .select_related("source")
        .prefetch_related("source__translations")
        .order_by("order", "pk")
    )
    content_blocks_queryset = (
        PostContentBlock.objects.filter(post=post, language=language)
        .select_related("image_asset", "related_post", "related_post__author")
        .prefetch_related("related_post__translations")
        .order_by("order", "pk")
    )
    # A direct import may leave a row incomplete.  Public pages only receive
    # self-contained blocks so they never expose an orphaned mini-post.
    content_blocks = [block for block in content_blocks_queryset if block.is_renderable]
    point_form = (
        PostPointAllocationForm(
            initial={"points": points_summary.current_post_points},
            max_points=max_points_per_post,
        )
        if getattr(config, "post_points_enabled", True)
        else None
    )

    return render(
        request,
        "posts/post_detail.html",
        {
            "post": post,
            "comments": comments,
            "comment_form": comment_form,
            "comments_login_url": login_url,
            "post_points_login_url": points_login_url,
            "breadcrumbs": breadcrumbs,
            "translatable_object": post,
            "post_points_enabled": getattr(config, "post_points_enabled", True),
            "post_points_summary": points_summary,
            "post_points_access": points_access,
            "post_points_today_total": get_post_points_total(post),
            "post_points_form": point_form,
            "post_points_max_per_post": max_points_per_post,
            "author_profile": author_profile,
            "citations": citations,
            "content_blocks": content_blocks,
            "can_follow_author": request.user.is_authenticated and request.user != post.author,
            "is_following_author": author_profile.is_followed_by(request.user) if author_profile else False,
            "is_favorited_post": is_post_favorited_by_user(request.user, post),
            "post_favorites_total": get_post_favorites_total(post),
        },
    )


def assign_post_points_view(request, year, month, day, slug):
    if request.method != "POST":
        raise Http404(gettext("Post not found."))

    language = get_language()
    post = get_object_or_404(
        Post.objects.language(language).filter(
            translations__language_code=language,
            translations__slug=slug,
            published_date__year=year,
            published_date__month=month,
            published_date__day=day,
            status="published",
        ).distinct()
    )

    try:
        config = SiteConfiguration.get_solo()
    except SiteConfiguration.DoesNotExist:
        class ConfigFallback:
            post_points_enabled = True
            daily_post_points_budget = 10
            max_points_per_post_per_day = 5
            allow_author_self_points = False
            post_points_min_account_age_days = 0
        config = ConfigFallback()

    if not request.user.is_authenticated:
        message = gettext("Please log in to assign points to this post.")
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "error": message}, status=403)
        messages.warning(request, message)
        return redirect(f"{reverse('login')}?{urlencode({'next': _post_points_anchor(post)})}")

    form = PostPointAllocationForm(
        request.POST,
        max_points=get_max_points_per_post(config),
    )
    if not form.is_valid():
        message = gettext("Please choose a valid number of points.")
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "error": message}, status=400)
        messages.error(request, message)
        return HttpResponseRedirect(_post_points_anchor(post))

    try:
        allocation = set_post_points_for_day(
            request.user,
            post,
            form.cleaned_data["points"],
            config,
        )
    except ValidationError as exc:
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "error": exc.messages[0]}, status=400)
        messages.error(request, exc.messages[0])
        return HttpResponseRedirect(_post_points_anchor(post))

    message = (
        gettext("You assigned %(points)s point(s) to this post for today.")
        % {"points": allocation.points}
    )
    if _is_ajax_request(request):
        summary = get_post_points_summary(request.user, post, config)
        return JsonResponse(
            {
                "ok": True,
                "message": message,
                "assigned_points": allocation.points,
                "remaining_points": summary.remaining,
                "budget": summary.budget,
                "post_points_today_total": get_post_points_total(post),
            }
        )

    messages.success(request, message)
    return HttpResponseRedirect(_post_points_anchor(post))


def posts_by_category_view(request, category_slug):
    """
    📂 View para listar los posts publicados de una categoría específica.
    Compatible con jerarquía, traducción y paginación.
    """
    language = get_language()
    category = get_category_by_slug(category_slug)
    category_tree = category.get_descendants(include_self=True)

    all_posts = (
        Post.objects
        .language(language)
        .filter(
            status="published",
            translations__language_code=language,
            categories__in=category_tree,
        )
        .distinct()
        .order_by("-published_date")
    )

    posts_per_page = get_site_config_int(
        "blog_items_per_page",
        6,
        logger=logger,
        warning_message="⚠️ SiteConfiguration no encontrada. Usando paginación por defecto.",
    )
    posts = paginate_queryset(all_posts, request.GET.get("page"), posts_per_page)

    fallback_posts = (
        Post.objects
        .language(language)
        .filter(status="published", translations__language_code=language)
        .exclude(pk__in=all_posts.values("pk"))
        .order_by("-published_date")[:3]
    )

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": reverse("posts:post_list"), "label": gettext("Posts")},
    ] + list(build_category_breadcrumbs(category))

    category_label = category.safe_translation_getter(
        "name",
        language_code=get_language(),
        any_language=True,
    )

    context = {
        "category": category,
        "posts": posts,
        "breadcrumbs": breadcrumbs,
        "fallback_posts": fallback_posts,
        "category_label": category_label,
        "translatable_object": category,
        "untranslated_post_cards": get_untranslated_post_cards(
            language,
            queryset=Post.objects.filter(categories__in=category_tree),
        ),
    }

    return render(
        request,
        "posts/posts_by_category.html",
        context,
    )


def posts_by_tag_view(request, tag_slug):
    """
    🏷️ View to list all posts associated with a given tag, with pagination and fallback suggestions.
    """
    language = get_language()

    tag = (
        Tag.objects
        .language(language)
        .translated(language, translated_slug=tag_slug)
        .distinct()
        .first()
    )

    if tag is None:
        tag = get_object_or_404(
            Tag.objects
            .language(language)
            .filter(slug=tag_slug)
            .distinct()
        )

    Tag.objects.filter(pk=tag.pk).update(
        click_count=F("click_count") + 1,
    )

    tag_metric, _ = TagDailyMetric.objects.get_or_create(
        tag=tag,
        date=timezone.localdate(),
    )

    TagDailyMetric.objects.filter(pk=tag_metric.pk).update(
        click_count=F("click_count") + 1,
    )

    all_tagged_posts = (
        Post.objects
        .language(language)
        .filter(
            tag_links__tag=tag,
            tag_links__language=language,
            status="published",
            translations__language_code=language,
        )
        .distinct()
        .order_by("-published_date")
    )

    per_page = get_site_config_int(
        "blog_items_per_page",
        6,
        logger=logger,
        warning_message="⚠️ SiteConfiguration missing. Using default of 6 posts per page.",
    )
    posts = paginate_queryset(all_tagged_posts, request.GET.get("page"), per_page)

    fallback_posts = (
        Post.objects
        .language(language)
        .filter(status="published", translations__language_code=language)
        .exclude(pk__in=[post.pk for post in posts])
        .order_by("-published_date")[:3]
    )

    tag_label = tag.safe_translation_getter(
        "label",
        any_language=True,
    )

    context = {
        "tag": tag,
        "posts": posts,
        "fallback_posts": fallback_posts,
        "breadcrumbs": [
            {"url": "/", "label": gettext("Home")},
            {"url": reverse("posts:post_list"), "label": gettext("Posts")},
            {"url": "", "label": tag_label},
        ],
        "tag_label": tag_label,
        "untranslated_post_cards": get_untranslated_post_cards(
            language,
            queryset=Post.objects.filter(tag_links__tag=tag),
        ),
    }

    return render(
        request,
        "posts/posts_by_tag.html",
        context,
    )
