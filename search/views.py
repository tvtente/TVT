# search/views.py
import logging

from django.db.models import Q
from django.shortcuts import render
from django.utils.translation import get_language

from core.pagination import get_site_config_int, paginate_queryset
from pages.models import Page
from posts.models import Post
from posts.selectors import get_matching_mini_post_entries

logger = logging.getLogger(__name__)

def search_results_view(request):
    """
    Performs a search across Pages and Blog Posts, ordering Pages by importance,
    and paginates the results correctly.
    """
    pages_per_page = get_site_config_int(
        "search_pages_per_page",
        5,
        logger=logger,
        warning_message="SiteConfiguration does not exist. Using default pagination settings.",
    )
    posts_per_page = get_site_config_int(
        "search_posts_per_page",
        5,
        logger=logger,
    )

    query = request.GET.get('q', '')
    
    # Initialize with empty QuerySets
    page_results_qs = Page.objects.none()
    post_results = []

    language = get_language()
    if query:
        # Build the Q objects for the search query
        page_query = (
            Q(translations__title__icontains=query)
            | Q(translations__content__icontains=query)
        )
        post_query = (
            Q(translations__title__icontains=query)
            | Q(translations__summary__icontains=query)
            | Q(translations__content__icontains=query)
        )

        # --- ¡LA LÓGICA CORRECTA! ---
        # 1. Obtenemos TODAS las páginas que coinciden con la búsqueda.
        # 2. LUEGO, las ordenamos por importancia y después por título.
        page_results_qs = Page.objects.language(language).filter( \
                                      page_query, status='published', translations__language_code=language) \
                                      .distinct() \
                                      .order_by('importance_order', 'translations__title')
        
        post_results_qs = Post.objects.language(language).filter( \
                                      post_query, status='published', translations__language_code=language) \
                                      .distinct().order_by('-published_date')
        mini_post_results = get_matching_mini_post_entries(
            query,
            language_code=language,
        )
        if mini_post_results:
            # Keep ordinary search results as Post instances. This preserves
            # Django's queryset pagination semantics; only the visual
            # mini-post entries need the editorial wrapper.
            post_results = list(
                post_results_qs.select_related("author").prefetch_related(
                    "translations",
                    "translations__featured_image_asset",
                )
            )
            post_results.extend(mini_post_results)
            post_results.sort(
                key=lambda entry: entry.published_date,
                reverse=True,
            )
        else:
            post_results = post_results_qs

    # --- Paginación (ahora sobre los QuerySets correctos) ---
    paginated_page_results = paginate_queryset(
        page_results_qs,
        request.GET.get("p_page", 1),
        pages_per_page,
    )
    paginated_post_results = paginate_queryset(
        post_results,
        request.GET.get("p_post", 1),
        posts_per_page,
    )
    
    # --- Contexto ---
    total_results = page_results_qs.count() + len(post_results)

    context = {
        'query': query,
        'page_results': paginated_page_results,
        'post_results': paginated_post_results,
        'total_results': total_results,
    }

    return render(request, 'search/search_results.html', context)
