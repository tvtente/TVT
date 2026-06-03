# Reset local de migraciones preservando data de prueba

Este proyecto ya tiene un comando para respaldar la data útil antes de reiniciar migraciones:

```bash
/home/tvt/MEGA/GIT/ART/tta_venv_313/bin/python manage.py backup_project_data
```

El comando exporta por defecto:

- `auth.user`
- `auth.group`
- `sites.site`
- `accounts`
- `books`
- `categories`
- `comments`
- `contact`
- `gallery`
- `menus`
- `pages`
- `posts`
- `publications`
- `shop`
- `site_settings`
- `tags`
- `testimonials`
- `widgets`

Y excluye tablas técnicas que conviene regenerar:

- `admin`
- `auth.permission`
- `contenttypes`
- `sessions`
- `socialaccount`

## Procedimiento recomendado

### Opción A: preservar la base local existente

Es la opción más segura cuando el esquema actual ya coincide con el código.

1. Generar el respaldo JSON.
2. Verificar que el archivo exista en `data_exports/`.
3. Eliminar las migraciones propias del proyecto, dejando solo `__init__.py`.
4. Ejecutar `makemigrations`.
5. Borrar solo las filas de `django_migrations` correspondientes a las apps propias.
6. Ejecutar `migrate --fake-initial`.
7. Validar con `check`, `showmigrations` y pruebas.

### Opción B: reconstruir la base local desde cero

Úsala solo si también quieres resetear físicamente la BD local.

1. Generar el respaldo JSON.
2. Verificar que el archivo exista en `data_exports/`.
3. Borrar la base local principal y la base de test.
4. Eliminar las migraciones propias del proyecto, dejando solo `__init__.py`.
5. Ejecutar `makemigrations`.
6. Ejecutar `migrate`.
7. Reimportar la data con `loaddata`.
8. Reaplicar seeders estructurales si hiciera falta.

## Secuencia orientativa

```bash
# 1. Backup
/home/tvt/MEGA/GIT/ART/tta_venv_313/bin/python manage.py backup_project_data

# 2. Regenerar migraciones
/home/tvt/MEGA/GIT/ART/tta_venv_313/bin/python manage.py makemigrations

# 3. Limpiar historial de migraciones propio
/home/tvt/MEGA/GIT/ART/tta_venv_313/bin/python manage.py shell -c "
from django.db.migrations.recorder import MigrationRecorder
apps = ['accounts','books','categories','comments','contact','gallery','menus','pages','posts','publications','shop','site_settings','tags','testimonials','widgets']
MigrationRecorder.Migration.objects.filter(app__in=apps).delete()
"

# 4. Reanclar el nuevo historial sin tocar la data actual
/home/tvt/MEGA/GIT/ART/tta_venv_313/bin/python manage.py migrate --fake-initial
```

## Notas

- `data_exports/` ya está ignorado por Git.
- La opción A evita depender de `sudo mariadb` o de permisos root sobre la base.
- Si no quieres conservar pedidos de prueba, usa:

```bash
/home/tvt/MEGA/GIT/ART/tta_venv_313/bin/python manage.py backup_project_data --without-shop
```

- Después de restaurar puede hacer falta volver a ejecutar scripts de estructura, por ejemplo:
  - `scripts/dev_tools/seed_role_permissions.py`
  - scripts de menú si quieres regenerarlos
