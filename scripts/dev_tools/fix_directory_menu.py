# scripts/dev_tools/fix_directory_menu.py
# Ejecutar con:
# python manage.py shell < scripts/dev_tools/fix_directory_menu.py

from django.core.cache import cache

from menus.models import Menu, MenuItem


MAIN_MENU_SLUG = "main-menu"
DIRECTORY_URL = "/accounts/directory/"


menu = Menu.objects.get(slug=MAIN_MENU_SLUG)


# 1. Eliminar Directory/User directory dentro de Account u otros padres.
account_directory_items = MenuItem.objects.filter(
    menu=menu,
    link_url=DIRECTORY_URL,
    parent__isnull=False,
)

for item in account_directory_items:
    print(f"🗑 Eliminando duplicado interno: ID {item.id} | {item.title}")
    item.delete()


# 2. Asegurar Directory público de primer nivel.
directory = MenuItem.objects.filter(
    menu=menu,
    link_url=DIRECTORY_URL,
    parent__isnull=True,
).first()

if directory:
    directory.parent = None
    directory.order = 7
    directory.link_type = MenuItem.LinkType.URL
    directory.link_url = DIRECTORY_URL
    directory.icon_class = directory.icon_class or "fas fa-users"
    directory.allowed_groups.clear()

    for language_code, value in (("es", "Directorio"), ("en", "Directory"), ("ca", "Directori")):
        directory.set_current_language(language_code)
        directory.title = value
        directory.save()

    print(f"🌍 Directory público corregido: ID {directory.id}")

else:
    directory = MenuItem.objects.create(
        menu=menu,
        parent=None,
        link_type=MenuItem.LinkType.URL,
        link_url=DIRECTORY_URL,
        order=7,
        icon_class="fas fa-users",
    )

    for language_code, value in (("es", "Directorio"), ("en", "Directory"), ("ca", "Directori")):
        directory.set_current_language(language_code)
        directory.title = value
        directory.save()

    directory.allowed_groups.clear()
    directory.save()

    print(f"🌍 Directory público creado: ID {directory.id}")


cache.clear()

print("")
print("✅ Directorio dejado solo como menú público principal.")
print("✅ Caché limpiada.")
