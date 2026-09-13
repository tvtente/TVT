from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.views import serve as staticfiles_serve
from django.views.static import serve as media_serve
from django.views.generic import RedirectView
from core import views as core_views
from posts import views as post_views


# ==============================================================================
# URLS THAT SHOULD NOT BE TRANSLATED (e.g., admin, auth process)
# ==============================================================================
urlpatterns = [
    # The public site is currently Spanish-first.  Keep the bare domain
    # deterministic instead of letting LocaleMiddleware choose a language
    # from an old cookie or the browser's Accept-Language header.
    path('', RedirectView.as_view(url='/es/', permanent=False), name='spanish_home_redirect'),
    # Browsers often request this path automatically, even when a page uses an
    # SVG favicon. Redirect it to the bundled fallback so the request is not a 404.
    path('favicon.ico', RedirectView.as_view(url=f'{settings.STATIC_URL}images/favicon.svg', permanent=False)),
    # Archivo de verificación de dominio: no se traduce ni sustituye la portada.
    path('uetr2lswk1zkn93fjne4k5hyfvlann.html', core_views.public_verification_file),
    # Webhooks must not be prefixed with a language code: Meta calls this URL
    # exactly as configured in the App Dashboard.
    path('webhooks/', include('social.urls')),
    # Short links deliberately stay outside i18n_patterns: /r/p-13/ is stable.
    path('r/<slug:short_code>/', post_views.short_post_redirect_view, name='short_post_redirect'),
    path('gallery-api/', include(('gallery.staff_urls', 'gallery_media'), namespace='gallery_media')),
    # 1. Third-party app URLs (like summernote)
    path('summernote/', include('django_summernote.urls')),
    path('tinymce/', include('tinymce.urls')),

    # This includes all of Django's built-in auth URLs (login, password reset, etc.)
    # Our custom logout is technically handled by django.contrib.auth.urls's default logout,
    # as we now handle the POST request in the template. If we needed a custom
    # next_page, we'd define a specific logout path here BEFORE this include.
    path('accounts/', include('django.contrib.auth.urls')),
    path('oauth/', include('allauth.urls')),
    path('i18n/', include('django.conf.urls.i18n')), 
]


# ==============================================================================
# URLS THAT WILL BE PREFIXED WITH A LANGUAGE CODE (e.g., /en/blog/, /es/blog/)
# ==============================================================================
urlpatterns += i18n_patterns(
    # 1. Django Admin
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('menus/', include('menus.urls', namespace='menus')),
    path('categories/', include('categories.urls', namespace='categories')),
    path('search/', include('search.urls', namespace='search')),
    path('pages/', include('pages.urls', namespace='pages')),
    path('blog/', include(('posts.urls', 'posts'), namespace='blog')),
    path('contact/', include('contact.urls', namespace='contact')),
    path('comments/', include('comments.urls', namespace='comments')),
    path('gallery/', include('gallery.urls', namespace='gallery')),
    path('testimonials/', include('testimonials.urls', namespace='testimonials')),
    path("posts/", include("posts.urls", namespace='posts')),
    path('publications/', include('publications.urls', namespace='publications')),
    path('books/', include('books.urls', namespace='books')),
    path('notebooks/', include('notebooks.urls', namespace='notebooks')),
    path('shop/', include('shop.urls', namespace='shop')),
    path('', include('core.urls')),
)


# ==============================================================================
# STATIC AND PUBLIC MEDIA FILES
# ==============================================================================
# Testing must render faithfully with DEBUG=False, so it has the same explicit
# fallback as local development.  Production remains the web server's
# responsibility: it should serve these public folders directly.
if settings.DEBUG or getattr(settings, 'ENVIRONMENT', '') in {'development', 'testing'}:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', staticfiles_serve, {'insecure': True}),
        re_path(r'^media/(?P<path>.*)$', media_serve, {'document_root': settings.MEDIA_ROOT}),
    ]
# ==============================================================================
