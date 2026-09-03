# Tavata CMS 🐝

A modern, robust, and multilingual Content Management System built with Python and Django. This project is a comprehensive case study on building a feature-rich web application from the ground up, focusing on clean architecture, best practices, and scalability.

![Tavata CMS Screenshot](link-to-a-cool-screenshot-of-your-app.png) 
<!-- TODO: Add a nice screenshot of the homepage or blog list here! -->

---

## ✨ Features

Tavata CMS is not just a simple blog. It's a powerful platform designed with a professional feature set:

*   **Dual Content Types:**
    *   **Static Pages:** For "evergreen" content like "About Us" or "Terms and Conditions".
    *   **Blog Posts:** A complete, time-based blogging engine.
*   **Rich Content Editing:** Powered by **django-summernote**, providing a beautiful WYSIWYG editing experience.
*   **Dynamic, Configurable Widgets:**
    *   Build and place widgets (Recent Posts, Most Viewed, Categories, etc.) in different "zones" (e.g., sidebars) directly from the admin panel.
    *   Widget behavior (like item count) is configurable.
*   **Full Internationalization (i18n):**
    *   Supports English, Spanish, and Catalan out-of-the-box.
    *   Translates database content with `django-parler`, interface text with `.po` files, and URLs.
*   **User & Profile Management:**
    *   Complete user authentication flow (Login, Logout, Signup).
    *   Extended user profiles with custom avatars and biographical information.
*   **Interactive Comment System:**
    *   Nested (threaded) comments with reply functionality, powered by `django-mptt`.
    *   Admin-configurable comment moderation (auto-approve or manual).
*   **Advanced Navigation:**
    *   Fully database-driven menu system. Administrators can build and reorder multiple menus (e.g., main navigation, footer links, social links) via the admin.
*   **Global Site Configuration:**
    *   A central settings panel (using `django-solo`) to manage site-wide parameters like pagination, caching timeouts, and branding without touching the code.
*   **Performance-Oriented:**
    *   A configurable caching system for widgets and menus to reduce database load.
    *   Pagination implemented on all content lists.
*   **SEO Ready:** All content types include fields for custom Meta Titles and Meta Descriptions.

### Cache configuration model

The project currently separates cache concerns into two layers:

- **Environment variables** define the cache infrastructure:
  - `CACHE_BACKEND`
  - `CACHE_LOCATION`
  - `CACHE_TIMEOUT`
  - `CACHE_LOG_LEVEL`
- **Database-backed site settings** define functional cache lifetimes for specific blocks:
  - menu cache timeout
  - category tree cache timeout
  - per-widget cache timeout

By default the project still uses `LocMemCache`. A shared backend such as Redis can be adopted later by changing environment variables, without restructuring application code again.

### Production cache backends

For production, prefer a shared cache backend once the hosting provider confirms support. The project is already prepared for both common options:

- **Redis**
  - `CACHE_BACKEND=django.core.cache.backends.redis.RedisCache`
  - `CACHE_LOCATION=redis://127.0.0.1:6379/1`
- **Memcached**
  - `CACHE_BACKEND=django.core.cache.backends.memcached.PyMemcacheCache`
  - `CACHE_LOCATION=127.0.0.1:11211`

Until infrastructure is confirmed, production can still run with `LocMemCache` only if you set `ALLOW_PRODUCTION_LOCMEM_CACHE=True` explicitly as a temporary exception. This is intentionally noisy so production does not fall back to per-process local memory by accident.

### Comment translation pipeline

Comments are stored in their original language. The project can request translations on demand and persist them in `CommentTranslation` rows.

- `COMMENT_TRANSLATION_PROVIDER=disabled`
  - default and safest mode
  - keeps the translation endpoint available but returns a controlled “not available” response
- `COMMENT_TRANSLATION_PROVIDER=mock`
  - development/testing helper
  - generates deterministic fake translations so the UI flow can be exercised without an external provider
- `COMMENT_TRANSLATION_PROVIDER=deepl`
  - real integration against DeepL Free / Pro endpoints
  - requires `DEEPL_API_KEY`
  - optional `DEEPL_API_URL` if you need to override the default Free endpoint
  - `COMMENT_TRANSLATION_TIMEOUT` controls request timeout in seconds

When a real provider is chosen later, the translation service can be extended without changing the comment UI contract again.

---

## Architecture overview

Tavata CMS is a **modular Django project**: each area of the product lives in its own **app** (a focused package of models, views, templates, and admin). Together they form one website and one admin experience.

### What the system is

The CMS lets staff **publish and organise content** (pages, posts, media, publications, testimonials) and **shape the public site** (menus, sidebar/body blocks called **widgets**, global settings, theme choices) **without redeploying code** for every change. Visitors see content in their chosen language where translations exist.

### How apps are grouped

| Group                        | Django apps                                                                 | Role in plain language |
|------------------------------|-----------------------------------------------------------------------------|-------------------------|
| **Core spine**               | `core`, `pages`, `posts`, `categories`, `menus`, `widgets`, `site_settings` | **Structure**: home routing, CMS pages, blog/editing spine, taxonomy, navigation, reusable blocks in zones, singleton settings & theme presets. |
| **User & interaction layer** | `accounts`, `comments`                                                      | **People**: sign-up, profiles, directory listing, threaded moderated comments on posts. |
| **Content support**          | `gallery`, `tags`, `testimonials`, `publications`                           | **Assets & variants**: reusable images, tagging, quoted endorsements block, longer-form publications alongside the blog. |
| **Utility**                  | `search`, `contact`                                                         | **Cross-cutting**: unified search across pages and posts; contact form messages for staff. |

### Main content flow

Editors work in the **Django admin** (and standard auth flows for the public site). **Pages** and **posts** are the two primary written surfaces: pages for stable site copy and landing-style content, posts for dated articles. **Categories** and **tags** organise that content. **Gallery** images can be referenced as shared media. The **homepage** can pull in **home sections** that point at **widget zones**, so layout stays flexible.

### Admin-driven configuration

**Site settings** provide one place for operational choices (pagination sizes, comment policy hints, menu/widget cache lifetime, and similar). **Visual theme** choices (logo, colours, slogan text where translated) live with **site templates**. **Menus** and **widgets** are entirely data-defined: staff create menu trees and widget rows; the front end reads that data when rendering.

### Widgets and menus on the frontend

**Menus** render by **slug** (for example main nav, footer, social links). **Widgets** render inside **named zones** embedded in templates (for example a right sidebar). Each widget has a **type** (recent posts, category list, grid, carousel, testimonials, user directory, and others) and simple options (how many items, filters, optional titles or “view all” links). Changing menus or posts can **invalidate caches** so lists stay reasonably fresh without hitting the database on every request.

### Media, users, comments, and search

- **Media:** Uploads go to standard **media** folders (for example gallery images and avatars); production typically serves them via the web server, not Django.
- **Users:** **Accounts** extends Django’s user with a **profile** (avatar, bio, visibility). Some widgets and comment trust rules depend on profile flags.
- **Comments:** **Comments** attach to **posts**, support threading and moderation, and respect site configuration for approval behaviour.
- **Search:** **Search** runs the visitor’s query across **published pages** and **posts** in one place, with separate pagination settings from site configuration.

### Core vs supporting

**Core spine** apps carry most day-to-day CMS behaviour: if you change them, you affect routing, layout slots, or global behaviour. **Supporting** apps add specialised content types or cross-cutting features without replacing that spine. **Utility** apps are thin but visible to users (search box, contact form).

### High-impact areas (change with care)

These parts touch **many templates**, **caching**, **URLs**, or **multilingual** behaviour. Regressions here are easy to feel on the live site:

- **`posts`** — main blog engine, widgets, search, tags.
- **`pages`** — static pages, homepage, home sections, SEO fields.
- **`menus`** — every layout that includes navigation; cache invalidation.
- **`widgets`** — large dispatch of widget types and shared cache keys.
- **`comments`** — moderation, threading, and trust rules tied to profiles and settings.

For more on the database translation strategy, scroll to **Architecture & Philosophy → Internationalization strategy (database content)** later in this README.

---

## 🛠️ Tech Stack

This project is built with a modern and robust stack:
*   **Backend:** Python 3.13.13, Django 5.2
*   **Database:** SQLite (for development), MySQL (for production)
*   **Frontend:** Bootstrap 5, FontAwesome
*   **Key Django Libraries:**
    *   `django-parler` for database content translation.
    *   `django-summernote` for WYSIWYG editing.
    *   `django-mptt` for hierarchical data (comments).
    *   `django-solo` for singleton configuration models.
    *   `python-decouple` for managing environment settings.

---

## 🚀 Getting Started

Instructions on how to set up and run a local instance of this project.

### Prerequisites

*   Python 3.13.13 for production parity.
*   `pip` and `venv`.
*   GNU gettext for internationalization commands.
    *   On Debian/Ubuntu: `sudo apt install gettext`

### Local Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/tavata-art/tvt-cms.git
    cd tvt-cms
    ```

2.  **Create and activate the virtual environment:**
    ```bash
    python3.13 -m venv ../tvt_313_env
    source ../tvt_313_env/bin/activate
    python --version
    ```

    The expected production-compatible version is:

    ```text
    Python 3.13.13
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run checks and migrations:**
    ```bash
    python manage.py check
    python manage.py migrate
    ```

5.  **Create a local superuser:**
    ```bash
    python manage.py createsuperuser
    ```

6.  **Run the development server:**
    ```bash
    python manage.py runserver 127.0.0.1:8000
    ```

The site will be available at `http://127.0.0.1:8000/`.

---

## ⚙️ Environment Variables

The project reads configuration with `python-decouple`. Environment variables from the server take priority. If they are not available, Django can read a `.env` file located at the project root.

For production, the project root is usually:

```text
/home/tvt/tvt
```

### Production Variables

```env
ENVIRONMENT=production
DEBUG=False

SECRET_KEY=replace_with_a_long_private_django_secret_key

ALLOWED_HOSTS=tvtavata.com,www.tvtavata.com

DB_NAME=database_name
DB_USER=database_user
DB_PASSWORD=database_password
DB_HOST=localhost
DB_PORT=3306

STATIC_ROOT=/home/tvt/domains/tvtavata.com/public_html/static
MEDIA_ROOT=/home/tvt/domains/tvtavata.com/public_html/media

LOG_FILE_PATH=/home/tvt/tvtlogs/error.log

GOOGLE_CLIENT_ID=replace_with_google_oauth_client_id
GOOGLE_CLIENT_SECRET=replace_with_google_oauth_client_secret
```

Important notes:

*   `SECRET_KEY` is required in production.
*   `DEBUG` must be `False`, not `release`.
*   `ALLOWED_HOSTS` is comma-separated.
*   `LOG_FILE_PATH` intentionally points outside the project.
*   Google login is enabled only when both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set.
*   Do not commit `.env` to Git.

For Google OAuth, register these redirect URIs in Google Cloud:

```text
http://127.0.0.1:8000/oauth/google/login/callback/
https://tvtavata.com/oauth/google/login/callback/
https://www.tvtavata.com/oauth/google/login/callback/
```

Generate a secure `SECRET_KEY` locally with:

```bash
source ../tvt_313_env/bin/activate
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🗄️ Database

Development uses SQLite by default. Production uses MySQL when:

```env
ENVIRONMENT=production
```

### Check Database Configuration

```bash
python manage.py check
```

### Review Migrations

```bash
python manage.py showmigrations
```

### Apply Migrations

```bash
python manage.py migrate
```

If production output says:

```text
No migrations to apply.
```

the database schema is already up to date for the migrations currently present in the project.

If Django warns about third-party apps such as `django_summernote`, do not create migrations for those packages in production without reviewing the change first.

---

## 🧱 Static And Media Files

Static files are collected into `STATIC_ROOT`.

In production:

```text
/home/tvt/domains/tvtavata.com/public_html/static
```

Media files are stored in `MEDIA_ROOT`.

In production:

```text
/home/tvt/domains/tvtavata.com/public_html/media
```

### Regenerate Static Files

```bash
source /home/tvt/virtualenv/tvt/3.13/bin/activate
cd /home/tvt/tvt
python manage.py collectstatic
```

To clean static files first:

```bash
rm -rf /home/tvt/domains/tvtavata.com/public_html/static/*
python manage.py collectstatic
```

Use the cleanup command carefully; it removes the current collected static files before rebuilding them.

---

## 👤 Superuser Creation

### Recommended With Shell Access

```bash
source /home/tvt/virtualenv/tvt/3.13/bin/activate
cd /home/tvt/tvt
python manage.py createsuperuser
```

### DirectAdmin Or No Shell Access

This project includes `create_superuser.py`. It is intended as a helper when the hosting panel can run a Python script during setup.

Run it only after:

*   Dependencies are installed.
*   Environment variables are available to Django.
*   Migrations have already run.

Set these temporary environment variables in DirectAdmin:

```env
DJANGO_SUPERUSER_USERNAME=tvt
DJANGO_SUPERUSER_EMAIL=admin@tvtavata.com
DJANGO_SUPERUSER_PASSWORD=replace_with_a_secure_temporary_password
```

Then run:

```bash
python create_superuser.py
```

Current behavior:

*   Loads Django with `DJANGO_SETTINGS_MODULE=tvt.settings`.
*   Calls Django's configured user model.
*   Creates the superuser if it does not exist.
*   Updates the same user if it already exists.
*   Exits without error if `DJANGO_SUPERUSER_PASSWORD` is not set.

Important:

*   If database tables are not migrated yet, the script will fail.
*   Remove `DJANGO_SUPERUSER_PASSWORD` from DirectAdmin after the user is created.
*   The script also accepts `BOOTSTRAP_SUPERUSER_USERNAME`, `BOOTSTRAP_SUPERUSER_EMAIL`, and `BOOTSTRAP_SUPERUSER_PASSWORD` as fallback names.

### Temporary Bootstrap Command

If you need to create or update the first superuser from the deployed environment,
enable bootstrap only temporarily and run:

```bash
python3 manage.py bootstrap_superuser
```

Required environment:

```env
BOOTSTRAP_SUPERUSER_ENABLED=True
BOOTSTRAP_SUPERUSER_USERNAME=admin
BOOTSTRAP_SUPERUSER_EMAIL=admin@tvtavata.com
BOOTSTRAP_SUPERUSER_PASSWORD=replace_with_a_secure_temporary_password
```

After creating the user, immediately set:

```env
BOOTSTRAP_SUPERUSER_ENABLED=False
```

and restart Passenger.

---

## 🚢 Production Deployment Notes

## ✅ Continuous Integration

The repository includes a GitHub Actions workflow at:

```text
.github/workflows/ci.yml
```

It runs on every pull request, on pushes to `main`/`master`, and manually via
`workflow_dispatch`.

Current CI checks:

*   `python manage.py check`
*   `python manage.py compilemessages`
*   `python manage.py test`

The workflow uses:

*   `ENVIRONMENT=development`
*   SQLite
*   empty Google OAuth credentials

This keeps CI independent from the production DirectAdmin/Passenger runtime.

### Reuse remote media while working locally

Uploaded images live in `media/` and are not normally copied by Git. To make a
local development or testing instance display the images already uploaded to
the public site, add the following to its local `.env`:

```env
USAR_MEDIA_REMOTA_EN_DESARROLLO=yes
MEDIA_REMOTA_BASE_URL=https://tvtente.com
```

This makes Django generate media URLs beginning with
`https://tvtente.com/media/`; static assets continue to use the local
`/static/` configuration. Disable the first variable when you need to test a
new local upload before it has been sent to the server.

### Passenger WSGI

`passenger_wsgi.py` must load Django, not the plain diagnostic `It works` app.

Expected production path:

```text
/home/tvt/tvt/passenger_wsgi.py
```

After changing code or environment variables, restart Passenger:

```bash
cd /home/tvt/tvt
mkdir -p tmp
touch tmp/restart.txt
```

### Upload Exclusions

Do not upload local runtime files:

*   `.env`
*   `.git`
*   `.github`
*   `.vscode`
*   `db.sqlite3`
*   `logs`
*   `*.log`
*   `staticfiles`
*   virtual environments such as `venv`, `.venv`, `env`, `tvt_313_env`, `tvt_311_env`

See `filezilla-exclude.txt` and `FILEZILLA_UPLOAD.md` for FileZilla guidance.

---

## 🏛️ Architecture & Philosophy

This project was built with a few key principles in mind:
*   **Modularity:** Each distinct piece of functionality (blog, pages, widgets) is encapsulated in its own Django app.
*   **Configuration over Code:** Empowering the site administrator to control as much as possible (menus, widgets, settings) from the admin panel without needing developer intervention.
*   **Cleanliness and Best Practices:** Adhering to Django's design philosophies, internationalization standards, and professional development workflows (e.g., using Git branches for features).

### Internationalization strategy (database content)

Tavata now uses **one** Django library for multilingual **database** fields: **`django-parler`**. Locale, URL prefixes, and UI strings (`.po`/`.mo`) remain standard Django i18n and are separate from the database translation layer.

Models that expose multilingual database content subclass **`TranslatableModel`** and define a **`TranslatedFields(...)`** block. Translations live in a separate translation table linked to a master row. This applies to content models such as `Page`, `HomeSection`, `Category`, `Menu`, `MenuItem`, `Widget`, `SiteTemplate`, `Profile`, the CV-related `accounts` models, `Post`, `Tag`, `Publication`, `Book`, and `Testimonial`.

`SiteConfiguration` remains non-translated because it stores operational settings rather than per-language editorial content. `gallery.Image` also remains single-language in the media library.

Configure Parler via **`PARLER_LANGUAGES`** / **`PARLER_LANGUAGE_OPTIONS`** in `tvt/settings.py`. Admin and forms use **`TranslatableAdmin`**, Parler-aware form classes, and explicit translation rows instead of `field_es/field_en/field_ca` columns.

#### Rule for new code

**All new multilingual models must use `django-parler`** (`TranslatableModel` + `TranslatedFields`). Do not introduce ad-hoc JSON translations, duplicated `field_es/field_en/field_ca` columns, or parallel translation systems.

<!--
## 🤝 Contributing

(Optional) If you ever make this open-source, you can add contribution guidelines here.
-->

## 🐝 About the Authors

This project was collaboratively developed by **Gustavo** and his AI. colleague, **MSc. Tavata**.
