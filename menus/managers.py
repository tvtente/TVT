from mptt.managers import TreeManager
from mptt.querysets import TreeQuerySet
from parler.managers import TranslatableManager, TranslatableQuerySet


class MenuItemQuerySet(TranslatableQuerySet, TreeQuerySet):
    @classmethod
    def as_manager(cls):
        manager = MenuItemManager.from_queryset(cls)()
        manager._built_with_as_manager = True
        return manager


class MenuItemManager(TreeManager, TranslatableManager):
    _queryset_class = MenuItemQuerySet
