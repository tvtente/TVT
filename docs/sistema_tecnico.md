# Sistema Técnico TVT

## Resumen

TVT es un proyecto Django modular orientado a publicación multilingüe. Usa una arquitectura por apps y una única estrategia de traducción de contenido en base de datos: `django-parler`. Mantiene además una fuerte dependencia de configuración editorial desde admin.

## Stack

- Python 3.13.13
- Django 5.2
- Bootstrap 5
- FontAwesome
- TinyMCE
- django-summernote
- django-parler
- django-mptt
- django-solo
- django-allauth
- PyMySQL

## Estructura por apps

### Spine principal

- `core`
- `pages`
- `posts`
- `categories`
- `menus`
- `widgets`
- `site_settings`

### Contenido editorial y soporte

- `publications`
- `books`
- `gallery`
- `tags`
- `testimonials`

### Usuarios e interacción

- `accounts`
- `comments`
- `contact`
- `search`

## Enrutado

Punto de entrada principal:

- [tvt/urls.py](/home/tvt/MEGA/GIT/ART/TVT/tvt/urls.py:1)

Rutas no traducidas:

- `gallery-api/`
- `summernote/`
- `tinymce/`
- `accounts/` de auth base
- `oauth/`
- `i18n/`
- auth base y utilidades técnicas no localizadas

Rutas traducidas con `i18n_patterns`:

- `admin/`
- `accounts/`
- `menus/`
- `categories/`
- `search/`
- `pages/`
- `blog/`
- `contact/`
- `gallery/`
- `testimonials/`
- `posts/`
- `publications/`
- `books/`
- raíz `core`

## Estrategia de traducción

El sistema usa `django-parler` como estrategia única para contenido multilingüe en base de datos.

Apps relevantes:

- `pages`
- `categories`
- `menus`
- `widgets`
- `site_settings`
- `accounts`
- `posts`
- `publications`
- `books`
- `tags`
- `testimonials`

Consecuencia técnica:

- existe una tabla base y una tabla de traducción asociada
- ejemplo: `books_book` y `books_book_translation`
- la disponibilidad por idioma depende de filas reales de traducción, no de fallback implícito por columnas

Plan de referencia:

- [docs/i18n_convergence_plan.md](/home/tvt/MEGA/GIT/ART/TVT/docs/i18n_convergence_plan.md:1)

## Configuración y entornos

Punto central:

- [tvt/settings.py](/home/tvt/MEGA/GIT/ART/TVT/tvt/settings.py:1)

Entornos soportados:

- `development`
- `testing`
- `production`

Comportamiento:

- `development`: SQLite local
- `testing`: MySQL/MariaDB según variables `DB_*`
- `production`: MySQL/MariaDB desde variables de entorno

Lectura de configuración:

- `python-decouple`
- variables de sistema en producción
- `.env` con fallback en desarrollo/testing

Parámetros sensibles:

- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

## Base de datos activa validada

Durante la validación de este repositorio, el entorno activo devolvió:

- `ENVIRONMENT=testing`
- `DEBUG=False`
- engine: `django.db.backends.mysql`
- schema: `tvtavata_tvt`
- host: `192.168.0.14`
- port: `3306`

En desarrollo local puro, el proyecto usa:

- `db.sqlite3`

## Autenticación

Se combina:

- auth estándar de Django
- `django-allauth`
- login social con Google si hay credenciales

Observación:

- MariaDB no soporta constraints únicas condicionales usadas por `allauth` en `account.EmailAddress`
- el warning `models.W036` se silenció de forma explícita solo en motores MySQL/MariaDB en [tvt/settings.py](/home/tvt/MEGA/GIT/ART/TVT/tvt/settings.py:317)
- la lógica funcional sigue validándose en capa de aplicación

## Modelos de contenido principales

### `Page`

Archivo:

- [pages/models.py](/home/tvt/MEGA/GIT/ART/TVT/pages/models.py:10)

Responsabilidad:

- páginas estables
- portada
- SEO
- featured image por idioma

### `Post`

Archivo:

- [posts/models.py](/home/tvt/MEGA/GIT/ART/TVT/posts/models.py:46)

Responsabilidad:

- blog
- relación con autor, categorías, tags y galería
- métricas de vistas

### `Publication`

Archivo:

- [publications/models.py](/home/tvt/MEGA/GIT/ART/TVT/publications/models.py:17)

Responsabilidad:

- documentos científicos estructurados
- autores múltiples
- PDF completo

### `Book`

Archivo:

- [books/models.py](/home/tvt/MEGA/GIT/ART/TVT/books/models.py:16)

Responsabilidad:

- línea editorial de libros
- preview PDF y full PDF
- metadatos comerciales

## Modelos estructurales

### Categorías

- [categories/models.py](/home/tvt/MEGA/GIT/ART/TVT/categories/models.py:8)
- árbol universal con `MPTT`

### Menús

- [menus/models.py](/home/tvt/MEGA/GIT/ART/TVT/menus/models.py:16)
- menús por slug y items en árbol
- visibilidad por grupos Django

### Widgets

- [widgets/models.py](/home/tvt/MEGA/GIT/ART/TVT/widgets/models.py:6)
- zonas y bloques renderizables

### Site settings

- [site_settings/models.py](/home/tvt/MEGA/GIT/ART/TVT/site_settings/models.py:5)
- singleton operacional y modelo de theme/branding

## Capa de media

Archivo:

- [gallery/models.py](/home/tvt/MEGA/GIT/ART/TVT/gallery/models.py:36)

Patrón:

- `Image` actúa como media library compartida
- `StagedUpload` soporta el picker del admin y la finalización diferida de subidas

## Capa de interacción

### Comentarios

- [comments/models.py](/home/tvt/MEGA/GIT/ART/TVT/comments/models.py:14)
- árbol MPTT
- moderación
- traducción opcional del contenido comentado

### Contacto

- [contact/models.py](/home/tvt/MEGA/GIT/ART/TVT/contact/models.py:6)
- bandeja de entrada persistida en base de datos

### Perfiles

- [accounts/models.py](/home/tvt/MEGA/GIT/ART/TVT/accounts/models.py:109)
- perfil extendido + currículum modular

## Caché y configuración operativa

`SiteConfiguration` permite ajustar:

- paginación de blog
- paginación de búsqueda
- paginación de galería
- tamaño de directorio público
- timeout de caché de menús
- timeout de caché del árbol de categorías
- umbral de comentarista confiable
- autoaprobación de comentarios

## Riesgos y complejidades

- uso homogéneo de `parler` en modelos multilingües
- menús y widgets cacheados
- contenido con fallback de idioma
- uso mixto de SQLite y MySQL según entorno
- dependencia de MySQL remoto en testing
- fuerte centralidad de `gallery.Image` como asset compartido

## Estado validado

Comandos ejecutados con:

- `/home/tvt/MEGA/GIT/ART/tta_venv_313/bin/python`

Resultado:

- `manage.py check`: correcto
- `manage.py makemigrations books`: sin cambios pendientes
- `manage.py migrate`: `books.0001_initial` aplicada correctamente
