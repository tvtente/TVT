# scripts/dev_tools/merge_duplicate_role_groups.py
# Ejecutar con:
# python manage.py shell < scripts/dev_tools/merge_duplicate_role_groups.py

from django.contrib.auth.models import Group
from django.core.cache import cache

from menus.models import MenuItem


GROUP_ALIASES = {
    "Author": ["Autor"],
    "Contributor": ["Contribuidor"],
    "Researcher": ["Investigador"],
    "Moderator": ["Moderadora"],
    "Reviewer": ["Revisor"],
    "Subscriber": ["Suscriptor"],
}


def merge_group_alias(canonical_name, alias_names):
    canonical_group, _ = Group.objects.get_or_create(name=canonical_name)

    print("")
    print(f"=== Fusionando hacia: {canonical_name} ===")

    for alias_name in alias_names:
        alias_group = Group.objects.filter(name=alias_name).first()

        if not alias_group:
            print(f"⚠️ Alias no existe: {alias_name}")
            continue

        print(f"➡️ Alias encontrado: {alias_name}")

        # 1. Mover usuarios del alias al grupo canónico.
        users = list(alias_group.user_set.all())

        for user in users:
            user.groups.add(canonical_group)
            print(f"   👤 Usuario movido: {user.username} → {canonical_name}")

        # 2. Fusionar permisos.
        permissions = list(alias_group.permissions.all())
        canonical_group.permissions.add(*permissions)

        if permissions:
            print(f"   🔐 Permisos fusionados: {len(permissions)}")
        else:
            print("   🔐 Sin permisos que fusionar")

        # 3. Reemplazar grupo en MenuItem.allowed_groups.
        menu_items = MenuItem.objects.filter(allowed_groups=alias_group).distinct()

        for item in menu_items:
            item.allowed_groups.add(canonical_group)
            item.allowed_groups.remove(alias_group)
            print(f"   🧭 MenuItem actualizado: ID {item.id} | {item.title}")

        # 4. Quitar alias de usuarios.
        for user in users:
            user.groups.remove(alias_group)

        # 5. Eliminar alias.
        alias_group.delete()
        print(f"   🗑️ Grupo eliminado: {alias_name}")


for canonical_name, alias_names in GROUP_ALIASES.items():
    merge_group_alias(canonical_name, alias_names)


cache.clear()

print("")
print("✅ Fusión de grupos duplicados completada.")
print("✅ Caché limpiada.")
print("")
print("Grupos actuales:")

for group in Group.objects.all().order_by("name"):
    print(f"- {group.name}")
