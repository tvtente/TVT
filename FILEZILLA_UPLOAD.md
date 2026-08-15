# FileZilla Upload Guide

FileZilla no usa automaticamente archivos tipo `.gitignore`, por eso este proyecto incluye
`filezilla-exclude.txt` como referencia para configurar filtros manuales.

## Subir normalmente

- Carpetas de apps Django: `accounts`, `ai_engine`, `blog`, `categories`, `comments`, `contact`, `core`, `fans`, `gallery`, `menus`, `pages`, `posts`, `publications`, `search`, `site_settings`, `social`, `tags`, `testimonials`, `tvt`, `widgets`
- `templates`
- `static`
- `locale`
- `manage.py`
- `passenger_wsgi.py`
- `requirements.txt`
- `README.md`

## No subir

- `.git`, `.github`, `.vscode`, `.codex`
- Entornos virtuales: `.venv`, `venv`, `env`, `tvt_313_env`, `tvt_313_env.bak_*`, `tvt_311_env`, `tvt_311_env.bak_*`
- Archivos locales o sensibles: `.env`, `db.sqlite3`, `*.sqlite3`
- Cachés Python: `__pycache__`, `*.pyc`, `*.pyo`, `*.pyd`
- Logs: `logs`, `*.log`, `passenger.log`
- Archivos generados o auxiliares: `staticfiles`, `requirements_backup.txt`, `reporte_completo.txt`

## Media y staticfiles

- `media` contiene archivos subidos por usuarios. Subirlo solo si necesitas migrar contenido local al servidor.
- `staticfiles` normalmente se genera en produccion con `collectstatic`. No lo subas al directorio del proyecto salvo que el hosting no permita ejecutar `collectstatic`.

## Filtros en FileZilla

1. Abre `View > Directory listing filters`.
2. Entra a `Edit filter rules`.
3. Crea un filtro para archivos/carpetas locales.
4. Agrega los patrones de `filezilla-exclude.txt`.
5. Activa el filtro antes de subir el proyecto.
