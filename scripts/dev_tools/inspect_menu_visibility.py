# scripts/dev_tools/inspect_menu_visibility.py
# Ejecutar con:
# python manage.py shell < scripts/dev_tools/inspect_menu_visibility.py

from menus.models import Menu, MenuItem


MENU_SLUG = "main-menu"


try:
    menu = Menu.objects.get(slug=MENU_SLUG)
except Menu.DoesNotExist:
    print(f"❌ No existe el menú con slug: {MENU_SLUG}")
    raise SystemExit


print(f"Menú: {menu.title} ({menu.slug})")
print("-" * 80)

items = (
    menu.items
    .all()
    .prefetch_related("allowed_groups")
    .select_related("parent")
    .order_by("tree_id", "lft", "order", "id")
)

for item in items:
    indent = "  " * item.level
    groups = list(item.allowed_groups.values_list("name", flat=True))

    if groups:
        visibility = "🔒 " + ", ".join(groups)
    else:
        visibility = "🌍 público"

    parent_title = item.parent.title if item.parent else "-"
    url = item.link_url or item.get_url()

    print(
        f"{indent}- ID {item.id} | {item.title} | "
        f"parent={parent_title} | order={item.order} | "
        f"url={url} | {visibility}"
    )
