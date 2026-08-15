from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.staticfiles.views import serve as staticfiles_serve
from django.views.static import serve as media_serve


# ==============================================================================
# URLS THAT SHOULD NOT BE TRANSLATED (e.g., admin, auth process)
# ==============================================================================
urlpatterns = [
    # Webhooks must not be prefixed with a language code: Meta calls this URL
    # exactly as configured in the App Dashboard.
    path('webhooks/', include('social.urls')),
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
# SERVING MEDIA FILES IN DEVELOPMENT
# ==============================================================================
# This is only for development (DEBUG=True) and should not be used in production.
# The web server (e.g., Nginx) should be configured to serve media files.
if settings.DEBUG:
    # Añadimos las URLs para los archivos MEDIA
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Este es para tus archivos de app (CSS, JS, imágenes por defecto)
    # Es la forma recomendada por Django para desarrollo.
    urlpatterns += staticfiles_urlpatterns()
elif getattr(settings, 'ENVIRONMENT', '') == 'development':
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', staticfiles_serve, {'insecure': True}),
        re_path(r'^media/(?P<path>.*)$', media_serve, {'document_root': settings.MEDIA_ROOT}),
    ]
# ==============================================================================
