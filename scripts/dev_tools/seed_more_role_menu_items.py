# scripts/dev_tools/seed_more_role_menu_items.py
# Ejecutar con:
# python manage.py shell < scripts/dev_tools/seed_more_role_menu_items.py
#
# Este script SOLO gestiona elementos de menú.
# No crea usuarios demo.
# No cambia contraseñas.
# No asigna usuarios a grupos.

from django.contrib.auth.models import Group
from django.core.cache import cache

from menus.models import Menu, MenuItem


MAIN_MENU_SLUG = "main-menu"


# ============================================================
# Canonical role groups
# ============================================================

REGISTERED_GROUPS = [
    "Subscriber",
    "Contributor",
    "Author",
    "Editor",
    "Researcher",
    "Reviewer",
    "Moderator",
    "Admin",
    "Site Manager",
]

CV_GROUPS = [
    "Contributor",
    "Author",
    "Editor",
    "Researcher",
    "Reviewer",
    "Moderator",
    "Admin",
    "Site Manager",
]

EDITORIAL_GROUPS = [
    "Author",
    "Editor",
    "Site Manager",
]

PUBLICATION_GROUPS = [
    "Researcher",
    "Reviewer",
    "Admin",
    "Site Manager",
]

BOOK_GROUPS = [
    "Editor",
    "Site Manager",
]

MODERATION_GROUPS = [
    "Author",
    "Editor",
    "Moderator",
    "Site Manager",
]

ADMIN_GROUPS = [
    "Admin",
    "Site Manager",
]


# ============================================================
# Helpers
# ============================================================

def get_menu():
    return Menu.objects.get(slug=MAIN_MENU_SLUG)


def get_groups(names):
    return [
        Group.objects.get_or_create(name=name)[0]
        for name in names
    ]


def set_titles(item, es=None, en=None, ca=None, fallback=None):
    """
    Sets translated titles using django-parler.
    """
    payloads = {
        "es": es,
        "en": en,
        "ca": ca,
    }

    if fallback and not any(value for value in payloads.values()):
        payloads["es"] = fallback

    for language_code, value in payloads.items():
        if value is None:
            continue
        item.set_current_language(language_code)
        item.title = value
        item.save()


def find_item(menu, title=None):
    """
    Finds a menu item by translated title.
    """
    if not title:
        return None

    qs = MenuItem.objects.filter(menu=menu)
    return qs.filter(translations__title__iexact=title).distinct().first()


def create_or_update_public_parent(
    *,
    menu,
    title_es,
    title_en,
    title_ca,
    order,
    icon_class,
    url="#",
    aliases=None,
):
    aliases = aliases or []

    item = find_item(menu, title_en)

    if item is None:
        for alias in aliases:
            item = find_item(menu, alias)
            if item:
                break

    if item is None:
        item = MenuItem.objects.create(
            menu=menu,
            parent=None,
            title=title_en,
            link_type=MenuItem.LinkType.URL,
            link_url=url,
            order=order,
            icon_class=icon_class,
        )

    item.menu = menu
    item.parent = None
    item.link_type = MenuItem.LinkType.URL
    item.link_url = url
    item.order = order
    item.icon_class = icon_class
    item.save()

    set_titles(item, es=title_es, en=title_en, ca=title_ca, fallback=title_en)

    item.allowed_groups.clear()
    item.save()

    print(f"🌍 Padre público: {title_en} → {url}")
    return item


def create_or_update_private_parent(
    *,
    menu,
    title_es,
    title_en,
    title_ca,
    order,
    icon_class,
    group_names,
    aliases=None,
):
    aliases = aliases or []

    item = find_item(menu, title_en)

    if item is None:
        for alias in aliases:
            item = find_item(menu, alias)
            if item:
                break

    if item is None:
        item = MenuItem.objects.create(
            menu=menu,
            parent=None,
            title=title_en,
            link_type=MenuItem.LinkType.URL,
            link_url="#",
            order=order,
            icon_class=icon_class,
        )

    item.menu = menu
    item.parent = None
    item.link_type = MenuItem.LinkType.URL
    item.link_url = "#"
    item.order = order
    item.icon_class = icon_class
    item.save()

    set_titles(item, es=title_es, en=title_en, ca=title_ca, fallback=title_en)

    item.allowed_groups.set(get_groups(group_names))
    item.save()

    print(f"🔒 Padre privado: {title_en} → {', '.join(group_names)}")
    return item


def create_or_update_public_child_item(
    *,
    menu,
    parent,
    title_es,
    title_en,
    title_ca,
    url,
    order,
    icon_class,
):
    item = (
        MenuItem.objects.filter(menu=menu, parent=parent, link_url=url).first()
        or MenuItem.objects.filter(menu=menu, link_url=url).first()
    )

    if item is None:
        item = MenuItem.objects.create(
            menu=menu,
            parent=parent,
            title=title_en,
            link_type=MenuItem.LinkType.URL,
            link_url=url,
            order=order,
            icon_class=icon_class,
        )

    item.menu = menu
    item.parent = parent
    item.link_type = MenuItem.LinkType.URL
    item.link_url = url
    item.order = order
    item.icon_class = icon_class
    item.save()

    set_titles(item, es=title_es, en=title_en, ca=title_ca, fallback=title_en)

    item.allowed_groups.clear()
    item.save()

    print(f"🌍 Item público: {title_en} → parent={parent.title} → {url}")
    return item


def create_or_update_private_child_item(
    *,
    menu,
    parent,
    title_es,
    title_en,
    title_ca,
    url,
    order,
    icon_class,
    group_names,
):
    item = (
        MenuItem.objects.filter(menu=menu, parent=parent, link_url=url).first()
        or MenuItem.objects.filter(menu=menu, link_url=url).first()
    )

    if item is None:
        item = MenuItem.objects.create(
            menu=menu,
            parent=parent,
            title=title_en,
            link_type=MenuItem.LinkType.URL,
            link_url=url,
            order=order,
            icon_class=icon_class,
        )

    item.menu = menu
    item.parent = parent
    item.link_type = MenuItem.LinkType.URL
    item.link_url = url
    item.order = order
    item.icon_class = icon_class
    item.save()

    set_titles(item, es=title_es, en=title_en, ca=title_ca, fallback=title_en)

    item.allowed_groups.set(get_groups(group_names))
    item.save()

    print(
        f"🔒 Item privado: {title_en} → parent={parent.title} "
        f"→ {url} → {', '.join(group_names)}"
    )
    return item


def cleanup_duplicate_roots(menu, keep_parent, titles):
    matches = MenuItem.objects.none()

    for title in titles:
        matches = matches | MenuItem.objects.filter(menu=menu, title__iexact=title)

        for field in ["title_es", "title_en", "title_ca"]:
            if hasattr(MenuItem, field):
                matches = matches | MenuItem.objects.filter(
                    menu=menu,
                    **{f"{field}__iexact": title},
                )

    for item in matches.distinct():
        if item.id == keep_parent.id:
            continue

        if item.get_children().exists():
            print(
                f"⚠️ No elimino posible duplicado porque tiene hijos: "
                f"ID {item.id} | {item.title}"
            )
            continue

        print(f"🗑 Eliminando duplicado vacío: ID {item.id} | {item.title}")
        item.delete()


def cleanup_admin_items_outside_parent(menu, parent, urls):
    for url in urls:
        items = list(MenuItem.objects.filter(menu=menu, link_url=url))

        canonical = None
        for item in items:
            if item.parent_id == parent.id:
                canonical = item
                break

        for item in items:
            if canonical and item.id == canonical.id:
                continue

            print(
                f"🗑 Eliminando duplicado admin fuera del padre correcto: "
                f"ID {item.id} | {item.title}"
            )
            item.delete()


# ============================================================
# Run
# ============================================================

menu = get_menu()


# ============================================================
# Publications
# ============================================================

publications_parent = create_or_update_public_parent(
    menu=menu,
    title_es="Publicaciones",
    title_en="Publications",
    title_ca="Publicacions",
    order=4,
    icon_class="fas fa-book-open",
    url="#",
    aliases=[
        "Scientific Admin",
        "Scientific",
        "Publications Admin",
        "Publicaciones admin",
        "Review",
        "Revisión",
        "Revisió",
    ],
)

create_or_update_public_child_item(
    menu=menu,
    parent=publications_parent,
    title_es="Ver publicaciones",
    title_en="View publications",
    title_ca="Veure publicacions",
    url="/publications/",
    order=10,
    icon_class="fas fa-book-open-reader",
)

create_or_update_private_child_item(
    menu=menu,
    parent=publications_parent,
    title_es="Crear publicación",
    title_en="Create publication",
    title_ca="Crear publicació",
    url="/admin/publications/publication/add/",
    order=20,
    icon_class="fas fa-file-circle-plus",
    group_names=PUBLICATION_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=publications_parent,
    title_es="Gestionar publicaciones",
    title_en="Manage publications",
    title_ca="Gestionar publicacions",
    url="/admin/publications/publication/",
    order=30,
    icon_class="fas fa-file-signature",
    group_names=PUBLICATION_GROUPS,
)

cleanup_admin_items_outside_parent(
    menu,
    publications_parent,
    [
        "/admin/publications/publication/add/",
        "/admin/publications/publication/",
    ],
)

cleanup_duplicate_roots(
    menu,
    publications_parent,
    [
        "Publications",
        "Publicaciones",
        "Publicacions",
        "Scientific Admin",
        "Scientific",
        "Publications Admin",
        "Publicaciones admin",
        "Review",
        "Revisión",
        "Revisió",
    ],
)


# ============================================================
# Books
# ============================================================

books_parent = create_or_update_public_parent(
    menu=menu,
    title_es="Libros",
    title_en="Books",
    title_ca="Llibres",
    order=5,
    icon_class="fas fa-book",
    url="#",
    aliases=[
        "Book Admin",
        "Books Admin",
        "Libros admin",
        "Llibres admin",
    ],
)

create_or_update_public_child_item(
    menu=menu,
    parent=books_parent,
    title_es="Ver libros",
    title_en="View books",
    title_ca="Veure llibres",
    url="/books/",
    order=10,
    icon_class="fas fa-book-open-reader",
)

create_or_update_private_child_item(
    menu=menu,
    parent=books_parent,
    title_es="Crear libro",
    title_en="Create book",
    title_ca="Crear llibre",
    url="/admin/books/book/add/",
    order=20,
    icon_class="fas fa-square-plus",
    group_names=BOOK_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=books_parent,
    title_es="Gestionar libros",
    title_en="Manage books",
    title_ca="Gestionar llibres",
    url="/admin/books/book/",
    order=30,
    icon_class="fas fa-book-bookmark",
    group_names=BOOK_GROUPS,
)

cleanup_admin_items_outside_parent(
    menu,
    books_parent,
    [
        "/admin/books/book/add/",
        "/admin/books/book/",
    ],
)

cleanup_duplicate_roots(
    menu,
    books_parent,
    [
        "Books",
        "Libros",
        "Llibres",
        "Book Admin",
        "Books Admin",
        "Libros admin",
        "Llibres admin",
    ],
)


# ============================================================
# Account
# ============================================================

account = create_or_update_private_parent(
    menu=menu,
    title_es="Cuenta",
    title_en="Account",
    title_ca="Compte",
    order=900,
    icon_class="fas fa-user",
    group_names=REGISTERED_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=account,
    title_es="Editar perfil",
    title_en="Edit Profile",
    title_ca="Editar perfil",
    url="/accounts/profile/edit/",
    order=10,
    icon_class="fas fa-user-pen",
    group_names=REGISTERED_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=account,
    title_es="Editar hoja de vida",
    title_en="Edit CV",
    title_ca="Editar currículum",
    url="/accounts/profile/cv/",
    order=20,
    icon_class="fas fa-id-card",
    group_names=CV_GROUPS,
)


# ============================================================
# Editorial Admin
# ============================================================

editorial_admin = create_or_update_private_parent(
    menu=menu,
    title_es="Editorial admin",
    title_en="Editorial Admin",
    title_ca="Editorial admin",
    order=910,
    icon_class="fas fa-pen-nib",
    group_names=EDITORIAL_GROUPS,
    aliases=["Editorial"],
)

create_or_update_private_child_item(
    menu=menu,
    parent=editorial_admin,
    title_es="Crear post",
    title_en="Create post",
    title_ca="Crear post",
    url="/admin/posts/post/add/",
    order=10,
    icon_class="fas fa-square-plus",
    group_names=EDITORIAL_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=editorial_admin,
    title_es="Gestionar posts",
    title_en="Manage posts",
    title_ca="Gestionar posts",
    url="/admin/posts/post/",
    order=20,
    icon_class="fas fa-newspaper",
    group_names=EDITORIAL_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=editorial_admin,
    title_es="Categorías",
    title_en="Categories",
    title_ca="Categories",
    url="/admin/categories/category/",
    order=30,
    icon_class="fas fa-folder-tree",
    group_names=EDITORIAL_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=editorial_admin,
    title_es="Etiquetas",
    title_en="Tags",
    title_ca="Etiquetes",
    url="/admin/tags/tag/",
    order=40,
    icon_class="fas fa-tags",
    group_names=EDITORIAL_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=editorial_admin,
    title_es="Media Library",
    title_en="Media Library",
    title_ca="Biblioteca multimèdia",
    url="/admin/gallery/image/",
    order=50,
    icon_class="fas fa-images",
    group_names=EDITORIAL_GROUPS,
)


# ============================================================
# Moderation
# ============================================================

moderation = create_or_update_private_parent(
    menu=menu,
    title_es="Moderación",
    title_en="Moderation",
    title_ca="Moderació",
    order=930,
    icon_class="fas fa-shield-halved",
    group_names=MODERATION_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=moderation,
    title_es="Moderar comentarios",
    title_en="Moderate comments",
    title_ca="Moderar comentaris",
    url="/admin/comments/comment/",
    order=10,
    icon_class="fas fa-comments",
    group_names=MODERATION_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=moderation,
    title_es="Comentarios pendientes",
    title_en="Pending comments",
    title_ca="Comentaris pendents",
    url="/admin/comments/comment/?is_approved__exact=0",
    order=20,
    icon_class="fas fa-hourglass-half",
    group_names=MODERATION_GROUPS,
)


# ============================================================
# Administration
# ============================================================

administration = create_or_update_private_parent(
    menu=menu,
    title_es="Administración",
    title_en="Administration",
    title_ca="Administració",
    order=940,
    icon_class="fas fa-gear",
    group_names=ADMIN_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=administration,
    title_es="Panel admin",
    title_en="Admin home",
    title_ca="Panell admin",
    url="/admin/",
    order=1,
    icon_class="fas fa-gauge-high",
    group_names=ADMIN_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=administration,
    title_es="Menús",
    title_en="Menus",
    title_ca="Menús",
    url="/admin/menus/menuitem/",
    order=10,
    icon_class="fas fa-bars",
    group_names=ADMIN_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=administration,
    title_es="Widgets",
    title_en="Widgets",
    title_ca="Widgets",
    url="/admin/widgets/widget/",
    order=20,
    icon_class="fas fa-table-cells-large",
    group_names=ADMIN_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=administration,
    title_es="Usuarios",
    title_en="Users",
    title_ca="Usuaris",
    url="/admin/auth/user/",
    order=40,
    icon_class="fas fa-user-group",
    group_names=ADMIN_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=administration,
    title_es="Grupos",
    title_en="Groups",
    title_ca="Grups",
    url="/admin/auth/group/",
    order=50,
    icon_class="fas fa-users-gear",
    group_names=ADMIN_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=administration,
    title_es="Páginas",
    title_en="Pages",
    title_ca="Pàgines",
    url="/admin/pages/page/",
    order=60,
    icon_class="fas fa-file-lines",
    group_names=ADMIN_GROUPS,
)

create_or_update_private_child_item(
    menu=menu,
    parent=administration,
    title_es="Configuración del sitio",
    title_en="Site configuration",
    title_ca="Configuració del lloc",
    url="/admin/site_settings/siteconfiguration/",
    order=70,
    icon_class="fas fa-sliders",
    group_names=ADMIN_GROUPS,
)


# ============================================================
# Cleanup / rebuild
# ============================================================

try:
    MenuItem.objects.rebuild()
    print("🌳 Árbol MPTT reconstruido.")
except Exception as exc:
    print(f"⚠️ No se pudo reconstruir MPTT automáticamente: {exc}")

cache.clear()

print("")
print("✅ Menús complementarios por rol creados/actualizados.")
print("✅ Publications queda como menú público con acciones internas por permisos.")
print("✅ Books queda como menú público con acciones internas para Editor y Site Manager.")
print("✅ Este script no toca usuarios demo ni contraseñas.")
print("✅ Caché limpiada.")
