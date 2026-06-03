# Environment Configuration Guide

This project supports three runtime environments selected by `ENVIRONMENT`:

- `development`
- `testing`
- `production`

---

## How Settings Resolution Works

- In `development` and `testing`, settings read values from environment variables and can fall back to the root `.env` file.
- In `production`, settings read values from process environment variables only (DirectAdmin/Passenger session/environment), not from the root `.env`.

---

## Development

### Required

```env
ENVIRONMENT=development
```

### Recommended

```env
SECRET_KEY=replace-with-a-safe-local-secret
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
LANGUAGE_CODE=en
TIME_ZONE=UTC
```

### Database Behavior

Development always uses SQLite:

- `ENGINE=django.db.backends.sqlite3`
- `NAME=BASE_DIR/db.sqlite3`

No DB env vars are required in development.

---

## Testing

### Typical `.env` values

```env
ENVIRONMENT=testing
SECRET_KEY=replace-with-a-testing-secret
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,testserver
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

DB_ENGINE=django.db.backends.mysql
DB_NAME=your_test_db
DB_TEST_NAME=your_existing_test_db
DB_USER=your_test_user
DB_PASSWORD=your_test_password
DB_HOST=localhost
DB_PORT=3306
```

Testing is MySQL/MariaDB only. SQLite is not supported for `ENVIRONMENT=testing`.
If your MySQL user cannot create databases automatically, set `DB_TEST_NAME` to a pre-created schema such as `tvtentec_test`.

---

## Production (DirectAdmin / Passenger)

Define these in DirectAdmin environment/session variables.

### Required

```env
ENVIRONMENT=production
SECRET_KEY=your_strong_secret
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

DB_ENGINE=django.db.backends.mysql
DB_NAME=your_prod_db
DB_USER=your_prod_user
DB_PASSWORD=your_prod_password
DB_HOST=localhost
DB_PORT=3306

STATIC_ROOT=/home/USERNAME/domains/yourdomain.com/public_html/static
MEDIA_ROOT=/home/USERNAME/domains/yourdomain.com/public_html/media
STATIC_URL=/static/
MEDIA_URL=/media/
```

### Optional hardening flags

```env
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_PROXY_SSL_HEADER_ENABLED=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
```

---

## Commands To Test Each Environment

### Development

```bash
export ENVIRONMENT=development
python3 manage.py check
python3 manage.py migrate
python3 manage.py runserver 127.0.0.1:8000
```

### Testing

```bash
export ENVIRONMENT=testing
python3 manage.py check
python3 manage.py test
```

### Production-like validation

```bash
export ENVIRONMENT=production
# export all required production variables first
python3 manage.py check --deploy
python3 manage.py collectstatic --noinput
```
