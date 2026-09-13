# scripts/dev_tools/fix_main_menu_structure.py
# Ejecutar con:
# python manage.py shell < scripts/dev_tools/fix_main_menu_structure.py

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
    result = []

    for name in names:
        group, _ = Group.objects.get_or_create(name=name)
        result.append(group)

    return result


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


def find_item(menu, title=None, item_id=None):
    """
    Finds a MenuItem by id or translated title.
    """
    if item_id:
        return MenuItem.objects.get(id=item_id, menu=menu)

    qs = MenuItem.objects.filter(menu=menu)
    return qs.filter(translations__title__iexact=title).distinct().first()


def find_item_by_url(menu, url):
    return MenuItem.objects.filter(menu=menu, link_url=url).first()


def create_or_update_parent(
    menu,
    title_en,
    title_es,
    title_ca,
    order,
    icon_class,
    public=True,
    groups=None,
    aliases=None,
):
    """
    Creates or updates a top-level parent item.

    aliases allows reusing old parent names, for example:
    Review -> Scientific Admin
    Editorial -> Editorial Admin
    """
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

    set_titles(
        item,
        es=title_es,
        en=title_en,
        ca=title_ca,
        fallback=title_en,
    )

    if public:
        item.allowed_groups.clear()
    else:
        item.allowed_groups.set(get_groups(groups or []))

    item.save()

    print(
        f"✅ Padre actualizado: {item.id} | {title_en} | "
        f"{'público' if public else ', '.join(groups or [])}"
    )

    return item


def make_public(item):
    item.allowed_groups.clear()
    item.save()
    print(f"🌍 Público: {item.id} | {item.title}")


def make_private(item, group_names):
    item.allowed_groups.set(get_groups(group_names))
    item.save()
    print(f"🔒 Privado: {item.id} | {item.title} → {', '.join(group_names)}")


def move_item(item, parent, order=None):
    item.parent = parent

    if order is not None:
        item.order = order

    item.save()

    print(
        f"➡️ Movido: {item.id} | {item.title} "
        f"→ parent={parent.title if parent else '-'}"
    )


def normalize_admin_item(
    *,
    menu,
    parent,
    url,
    title_en,
    title_es,
    title_ca,
    order,
    icon_class,
    group_names,
):
    """
    Finds by URL first, then by translated/base title, and attaches to parent.
    Creates the item if it does not exist.
    """
    item = find_item_by_url(menu, url)

    if item is None:
        item = find_item(menu, title_en)

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

    set_titles(
        item,
        es=title_es,
        en=title_en,
        ca=title_ca,
        fallback=title_en,
    )

    make_private(item, group_names)

    return item


def delete_duplicate_items(menu, keep_item, title_candidates=None, url=None):
    """
    Deletes duplicated items matching title candidates or URL,
    except keep_item.

    Useful after renaming/reusing old parents.
    """
    title_candidates = title_candidates or []

    qs = MenuItem.objects.filter(menu=menu)

    matches = MenuItem.objects.none()

    if url:
        matches = matches | qs.filter(link_url=url)

    for title in title_candidates:
        matches = matches | qs.filter(translations__title__iexact=title)

    for item in matches.distinct():
        if keep_item and item.id == keep_item.id:
            continue

        # Do not delete a non-empty parent automatically.
        if item.get_children().exists():
            print(
                f"⚠️ Duplicado no eliminado porque tiene hijos: "
                f"{item.id} | {item.title}"
            )
            continue

        print(f"🗑 Eliminando duplicado: {item.id} | {item.title}")
        item.delete()


# ============================================================
# Run
# ============================================================

menu = get_menu()


# ============================================================
# Public parents
# ============================================================

debates = create_or_update_parent(
    menu=menu,
    title_en="Debates",
    title_es="Debates",
    title_ca="Debats",
    order=2,
    icon_class="fas fa-comments",
    public=True,
)

explore = create_or_update_parent(
    menu=menu,
    title_en="Explore",
    title_es="Explorar",
    title_ca="Explora",
    order=3,
    icon_class="fas fa-compass",
    public=True,
)


# Directory público top-level
directory = (
    find_item_by_url(menu, "/accounts/directory/")
    or find_item(menu, "Directory")
    or find_item(menu, "Directorio")
    or find_item(menu, "Directori")
)

if directory:
    directory.parent = None
    directory.order = 7
    directory.link_type = MenuItem.LinkType.URL
    directory.link_url = "/accounts/directory/"
    directory.icon_class = directory.icon_class or "fas fa-users"
    directory.save()

    set_titles(
        directory,
        es="Directorio",
        en="Directory",
        ca="Directori",
        fallback="Directory",
    )

    make_public(directory)


# ============================================================
# Move public debate children
# ============================================================

for title, order in [
    ("Latest debates", 1),
    ("Most discussed", 2),
    ("Trending now", 3),
    ("Recommended", 4),
    ("New", 5),
]:
    item = find_item(menu, title)
    if item:
        move_item(item, debates, order)
        make_public(item)


# ============================================================
# Move public explore/category children
# ============================================================

categories_public = find_item(menu, "Categories")

if categories_public:
    move_item(categories_public, explore, 1)
    make_public(categories_public)


category_titles = [
    "Double standards and contradictions",
    "Modern relationships and dynamics",
    "Identity and self-expression",
    "Morality and social norms",
    "Psychology and well-being",
    "Society and structure",
    "Technology and the human future",
]

for index, title in enumerate(category_titles, start=2):
    item = find_item(menu, title)
    if item:
        move_item(item, explore, index)
        make_public(item)


authentic = find_item(menu, "Authentic expression or social approval")

if authentic:
    make_public(authentic)


# ============================================================
# Account
# ============================================================

account = create_or_update_parent(
    menu=menu,
    title_en="Account",
    title_es="Cuenta",
    title_ca="Compte",
    order=900,
    icon_class="fas fa-user",
    public=False,
    groups=REGISTERED_GROUPS,
)

edit_profile = (
    find_item_by_url(menu, "/accounts/profile/edit/")
    or find_item(menu, "Edit Profile")
    or find_item(menu, "Editar perfil")
)

if edit_profile:
    move_item(edit_profile, account, 10)
    set_titles(
        edit_profile,
        es="Editar perfil",
        en="Edit Profile",
        ca="Editar perfil",
        fallback="Edit Profile",
    )
    make_private(edit_profile, REGISTERED_GROUPS)


edit_cv = (
    find_item_by_url(menu, "/accounts/profile/cv/")
    or find_item(menu, "Edit CV")
    or find_item(menu, "Editar hoja de vida")
)

if edit_cv:
    move_item(edit_cv, account, 20)
    set_titles(
        edit_cv,
        es="Editar hoja de vida",
        en="Edit CV",
        ca="Editar currículum",
        fallback="Edit CV",
    )
    make_private(edit_cv, CV_GROUPS)


# ============================================================
# Editorial Admin
# ============================================================

editorial_admin = create_or_update_parent(
    menu=menu,
    title_en="Editorial Admin",
    title_es="Editorial admin",
    title_ca="Editorial admin",
    order=910,
    icon_class="fas fa-pen-nib",
    public=False,
    groups=EDITORIAL_GROUPS,
    aliases=["Editorial"],
)

normalize_admin_item(
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

normalize_admin_item(
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

normalize_admin_item(
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

normalize_admin_item(
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

normalize_admin_item(
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
# Scientific Admin / Publications
# ============================================================

scientific_admin = create_or_update_parent(
    menu=menu,
    title_en="Scientific Admin",
    title_es="Publicaciones",
    title_ca="Publicacions",
    order=920,
    icon_class="fas fa-flask",
    public=False,
    groups=PUBLICATION_GROUPS,
    aliases=[
        "Review",
        "Revisión",
        "Revisió",
        "Publications",
        "Publicaciones",
        "Publicacions",
    ],
)

normalize_admin_item(
    menu=menu,
    parent=scientific_admin,
    title_es="Crear publicación",
    title_en="Create publication",
    title_ca="Crear publicació",
    url="/admin/publications/publication/add/",
    order=10,
    icon_class="fas fa-file-circle-plus",
    group_names=PUBLICATION_GROUPS,
)

normalize_admin_item(
    menu=menu,
    parent=scientific_admin,
    title_es="Gestionar publicaciones",
    title_en="Manage publications",
    title_ca="Gestionar publicacions",
    url="/admin/publications/publication/",
    order=20,
    icon_class="fas fa-file-signature",
    group_names=PUBLICATION_GROUPS,
)

# Move old publication menu items into Scientific Admin if they exist.
for title, order in [
    ("Review publications", 20),
    ("Revisar publicaciones", 20),
    ("Add publication", 10),
    ("Crear publicación", 10),
]:
    item = find_item(menu, title)
    if item and item.id != scientific_admin.id:
        move_item(item, scientific_admin, order)
        make_private(item, PUBLICATION_GROUPS)


# ============================================================
# Moderation
# ============================================================

moderation = create_or_update_parent(
    menu=menu,
    title_en="Moderation",
    title_es="Moderación",
    title_ca="Moderació",
    order=930,
    icon_class="fas fa-shield-halved",
    public=False,
    groups=MODERATION_GROUPS,
)

normalize_admin_item(
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

normalize_admin_item(
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

administration = create_or_update_parent(
    menu=menu,
    title_en="Administration",
    title_es="Administración",
    title_ca="Administració",
    order=940,
    icon_class="fas fa-gear",
    public=False,
    groups=ADMIN_GROUPS,
)

normalize_admin_item(
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

normalize_admin_item(
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

normalize_admin_item(
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

normalize_admin_item(
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

normalize_admin_item(
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

normalize_admin_item(
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

normalize_admin_item(
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
# Cleanup duplicated Directory inside private parents
# ============================================================

directory_duplicates = MenuItem.objects.filter(
    menu=menu,
    link_url="/accounts/directory/",
    parent__isnull=False,
)

for item in directory_duplicates:
    print(f"🗑 Eliminando Directory duplicado interno: {item.id} | {item.title}")
    item.delete()


# ============================================================
# Optional cleanup old empty Review parent duplicates
# ============================================================

delete_duplicate_items(
    menu=menu,
    keep_item=scientific_admin,
    title_candidates=[
        "Review",
        "Revisión",
        "Revisió",
        "Publications",
        "Publicaciones",
        "Publicacions",
    ],
)


# ============================================================
# Rebuild MPTT tree and clear cache
# ============================================================

try:
    MenuItem.objects.rebuild()
    print("🌳 Árbol MPTT reconstruido.")
except Exception as exc:
    print(f"⚠️ No se pudo reconstruir MPTT automáticamente: {exc}")


cache.clear()

print("")
print("✅ Estructura del main-menu corregida.")
print("✅ Scientific Admin/Publicaciones normalizado para Researcher, Reviewer y Site Manager.")
print("✅ Admin queda reservado para administración del sitio.")
print("✅ Caché limpiada.")
