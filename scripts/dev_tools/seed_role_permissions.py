# scripts/dev_tools/seed_role_permissions.py
# Ejecutar con:
# python manage.py shell < scripts/dev_tools/seed_role_permissions.py
#
# Regenera permisos para grupos canónicos del CMS.
#
# Este script:
# - crea/actualiza grupos canónicos
# - asigna permisos por rol
# - opcionalmente ajusta usuarios demo si existen
# - limpia permisos directos de usuarios demo
#
# Grupos canónicos:
# - Subscriber
# - Contributor
# - Author
# - Editor
# - Researcher
# - Reviewer
# - Moderator
# - Admin
# - Site Manager

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


User = get_user_model()


# ============================================================
# App access policies
# ============================================================

SITE_MANAGER_FULL_ACCESS_APP_LABELS = [
    "accounts",
    "auth",
    "books",
    "categories",
    "comments",
    "contact",
    "gallery",
    "menus",
    "pages",
    "posts",
    "publications",
    "sites",
    "socialaccount",
    "shop",
    "site_settings",
    "tags",
    "testimonials",
    "widgets",
]

# Admin administra estructura del sitio.
# No administra contenido editorial/científico/producto.
ADMIN_SITE_ACCESS_APP_LABELS = [
    "auth",
    "contact",
    "menus",
    "pages",
    "sites",
    "socialaccount",
    "site_settings",
    "widgets",
]


# Researcher y Admin deben poder trabajar con publicaciones científicas con la
# misma capacidad editorial. Admin conserva, además, sus permisos de
# administración de la estructura del sitio.
PUBLICATION_ACCESS_PERMISSIONS = [
    ("publications", "publication", "add_publication"),
    ("publications", "publication", "view_publication"),
    ("publications", "publication", "change_publication"),

    ("gallery", "image", "add_image"),
    ("gallery", "image", "view_image"),
    ("gallery", "image", "change_image"),
]


# ============================================================
# Role permissions
# ============================================================

ROLE_PERMISSIONS = {
    # --------------------------------------------------------
    # Subscriber
    # Usuario autenticado básico.
    # --------------------------------------------------------
    "Subscriber": [
        ("comments", "comment", "add_comment"),
        ("comments", "comment", "view_comment"),
    ],

    # --------------------------------------------------------
    # Contributor
    # Colaborador / auspiciante / aliado.
    # --------------------------------------------------------
    "Contributor": [
        ("accounts", "profile", "edit_professional_profile"),
        ("accounts", "profile", "edit_own_cv"),
        ("accounts", "profile", "list_public_profile"),

        ("comments", "comment", "add_comment"),
        ("comments", "comment", "view_comment"),
    ],

    # --------------------------------------------------------
    # Author
    # Productor editorial de posts.
    # --------------------------------------------------------
    "Author": [
        ("accounts", "profile", "edit_professional_profile"),
        ("accounts", "profile", "edit_own_cv"),
        ("accounts", "profile", "list_public_profile"),

        ("posts", "post", "add_post"),
        ("posts", "post", "view_post"),
        ("posts", "post", "change_post"),

        ("comments", "comment", "view_comment"),
        ("comments", "comment", "change_comment"),

        ("categories", "category", "view_category"),
        ("tags", "tag", "view_tag"),

        ("gallery", "image", "add_image"),
        ("gallery", "image", "view_image"),
        ("gallery", "image", "change_image"),
    ],

    # --------------------------------------------------------
    # Editor
    # Supervisor editorial.
    #
    # Gestiona:
    # - Posts
    # - Books
    # - categorías/tags editoriales
    # - media editorial
    #
    # No gestiona publications científicas por defecto.
    # --------------------------------------------------------
    "Editor": [
        ("accounts", "profile", "edit_professional_profile"),
        ("accounts", "profile", "edit_own_cv"),
        ("accounts", "profile", "list_public_profile"),

        # Posts
        ("posts", "post", "add_post"),
        ("posts", "post", "view_post"),
        ("posts", "post", "change_post"),

        # Books
        ("books", "book", "add_book"),
        ("books", "book", "view_book"),
        ("books", "book", "change_book"),

        # Comments
        ("comments", "comment", "view_comment"),
        ("comments", "comment", "change_comment"),

        # Categories / tags
        ("categories", "category", "add_category"),
        ("categories", "category", "view_category"),
        ("categories", "category", "change_category"),

        ("tags", "tag", "add_tag"),
        ("tags", "tag", "view_tag"),
        ("tags", "tag", "change_tag"),

        ("tags", "taggedpost", "add_taggedpost"),
        ("tags", "taggedpost", "view_taggedpost"),
        ("tags", "taggedpost", "change_taggedpost"),

        # Gallery
        ("gallery", "image", "add_image"),
        ("gallery", "image", "view_image"),
        ("gallery", "image", "change_image"),

        # Context read access
        ("publications", "publication", "view_publication"),
    ],

    # --------------------------------------------------------
    # Researcher
    # Productor científico/técnico.
    # --------------------------------------------------------
    "Researcher": [
        ("accounts", "profile", "edit_professional_profile"),
        ("accounts", "profile", "edit_own_cv"),
        ("accounts", "profile", "list_public_profile"),

        ("comments", "comment", "add_comment"),
        ("comments", "comment", "view_comment"),

        *PUBLICATION_ACCESS_PERMISSIONS,
    ],

    # --------------------------------------------------------
    # Reviewer
    # Supervisor científico.
    # --------------------------------------------------------
    "Reviewer": [
        ("accounts", "profile", "edit_professional_profile"),
        ("accounts", "profile", "edit_own_cv"),
        ("accounts", "profile", "list_public_profile"),

        ("comments", "comment", "add_comment"),
        ("comments", "comment", "view_comment"),

        ("publications", "publication", "add_publication"),
        ("publications", "publication", "view_publication"),
        ("publications", "publication", "change_publication"),

        ("gallery", "image", "add_image"),
        ("gallery", "image", "view_image"),
        ("gallery", "image", "change_image"),
    ],

    # --------------------------------------------------------
    # Moderator
    # Moderación de comunidad/comentarios.
    # --------------------------------------------------------
    "Moderator": [
        ("accounts", "profile", "edit_professional_profile"),
        ("accounts", "profile", "edit_own_cv"),
        ("accounts", "profile", "list_public_profile"),

        ("comments", "comment", "view_comment"),
        ("comments", "comment", "change_comment"),

        ("posts", "post", "view_post"),
    ],

    # --------------------------------------------------------
    # Admin
    # Administración estructural del sitio.
    #
    # No gestiona contenido editorial/científico/libros.
    # --------------------------------------------------------
    "Admin": "__ADMIN_SITE_ACCESS__",

    # --------------------------------------------------------
    # Site Manager
    # Gestión operativa global.
    # --------------------------------------------------------
    "Site Manager": "__SITE_MANAGER_FULL_ACCESS__",
}


# ============================================================
# Demo users
# ============================================================
#
# Si existen, se ajustan para pruebas.
# Este script no crea usuarios nuevos.
#

DEMO_USERS = {
    "subscriber_demo": {
        "groups": ["Subscriber"],
        "is_staff": False,
        "is_superuser": False,
    },
    "contributor_demo": {
        "groups": ["Contributor"],
        "is_staff": False,
        "is_superuser": False,
    },
    "autor_demo": {
        "groups": ["Author"],
        "is_staff": True,
        "is_superuser": False,
    },
    "author_demo": {
        "groups": ["Author"],
        "is_staff": True,
        "is_superuser": False,
    },
    "editorial_demo": {
        "groups": ["Editor"],
        "is_staff": True,
        "is_superuser": False,
    },
    "editor_demo": {
        "groups": ["Editor"],
        "is_staff": True,
        "is_superuser": False,
    },
    "researcher_demo": {
        "groups": ["Researcher"],
        "is_staff": True,
        "is_superuser": False,
    },
    "reviewer_demo": {
        "groups": ["Reviewer"],
        "is_staff": True,
        "is_superuser": False,
    },
    "moderadora_demo": {
        "groups": ["Moderator"],
        "is_staff": True,
        "is_superuser": False,
    },
    "admin_demo": {
        "groups": ["Admin"],
        "is_staff": True,
        "is_superuser": False,
    },
    "tvt": {
        "groups": ["Site Manager", "Admin"],
        "is_staff": True,
        "is_superuser": False,
    },
}


# ============================================================
# Helpers
# ============================================================

def get_permission(app_label, model, codename):
    try:
        content_type = ContentType.objects.get(
            app_label=app_label,
            model=model,
        )
        return Permission.objects.get(
            content_type=content_type,
            codename=codename,
        )

    except ContentType.DoesNotExist:
        print(f"⚠️ ContentType no encontrado: {app_label}.{model}")
        return None

    except Permission.DoesNotExist:
        print(f"⚠️ Permiso no encontrado: {app_label}.{codename}_{model}")
        return None


def resolve_permissions(permission_specs):
    permissions = []

    for app_label, model, codename in permission_specs:
        permission = get_permission(app_label, model, codename)

        if permission:
            permissions.append(permission)

    return permissions


def get_permissions_for_app_labels(app_labels):
    return list(
        Permission.objects
        .filter(content_type__app_label__in=app_labels)
        .select_related("content_type")
        .order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        )
    )


def get_site_manager_full_permissions():
    return get_permissions_for_app_labels(SITE_MANAGER_FULL_ACCESS_APP_LABELS)


def get_admin_site_permissions():
    return [
        *get_permissions_for_app_labels(ADMIN_SITE_ACCESS_APP_LABELS),
        *resolve_permissions(PUBLICATION_ACCESS_PERMISSIONS),
    ]


def reset_group_permissions(group_name, permission_specs):
    group, _ = Group.objects.get_or_create(name=group_name)

    if permission_specs == "__SITE_MANAGER_FULL_ACCESS__":
        permissions = get_site_manager_full_permissions()

    elif permission_specs == "__ADMIN_SITE_ACCESS__":
        permissions = get_admin_site_permissions()

    else:
        permissions = resolve_permissions(permission_specs)

    group.permissions.set(permissions)
    group.save()

    print("")
    print(f"✅ Grupo regenerado: {group_name}")
    print(f"   Permisos totales: {group.permissions.count()}")

    for permission in group.permissions.all().order_by(
        "content_type__app_label",
        "content_type__model",
        "codename",
    ):
        print(
            f"   - {permission.content_type.app_label}."
            f"{permission.codename}"
        )


def update_demo_users():
    print("")
    print("=== Actualizando usuarios demo existentes ===")

    for username, config in DEMO_USERS.items():
        user = User.objects.filter(username=username).first()

        if not user:
            print(f"⚠️ Usuario demo no existe: {username}")
            continue

        groups = [
            Group.objects.get_or_create(name=group_name)[0]
            for group_name in config["groups"]
        ]

        user.groups.set(groups)
        user.is_active = True
        user.is_staff = config["is_staff"]
        user.is_superuser = config["is_superuser"]
        user.save()

        user.user_permissions.clear()

        print("")
        print(f"👤 Usuario demo actualizado: {username}")
        print(f"   grupos={', '.join(config['groups'])}")
        print(f"   is_staff={user.is_staff}")
        print(f"   is_superuser={user.is_superuser}")
        print("   permisos directos limpiados")


def print_effective_permissions_for_demo_users():
    print("")
    print("=== Permisos efectivos de usuarios demo ===")

    for username in DEMO_USERS.keys():
        user = User.objects.filter(username=username).first()

        if not user:
            continue

        print("")
        print(f"👤 {username}")
        print(f"   grupos: {list(user.groups.values_list('name', flat=True))}")
        print(f"   is_staff: {user.is_staff}")
        print(f"   is_superuser: {user.is_superuser}")

        for permission in sorted(user.get_all_permissions()):
            print(f"   - {permission}")


# ============================================================
# Run
# ============================================================

print("=== Regenerando permisos por rol ===")

for group_name, permission_specs in ROLE_PERMISSIONS.items():
    reset_group_permissions(group_name, permission_specs)

update_demo_users()
print_effective_permissions_for_demo_users()

print("")
print("✅ Regeneración de permisos completada.")
print("")
print("Notas:")
print("- Subscriber: usuario básico autenticado.")
print("- Contributor: colaborador/auspiciante/aliado sin admin.")
print("- Author: produce posts.")
print("- Editor: gestiona posts y books.")
print("- Researcher: produce publications.")
print("- Reviewer: revisa/gestiona publications.")
print("- Moderator: modera comentarios.")
print("- Admin: administra estructura del sitio, no contenido.")
print("- Site Manager: gestión global operativa.")
print("- Books y Shop quedan bajo Editor/Site Manager según corresponda.")
print("- Los usuarios pueden combinar grupos según necesidad real.")
