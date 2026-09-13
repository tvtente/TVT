from django.db import migrations


def move_featured_tags_widget(apps, schema_editor):
    Widget = apps.get_model("widgets", "Widget")
    WidgetZone = apps.get_model("widgets", "WidgetZone")
    WidgetTranslation = apps.get_model("widgets", "WidgetTranslation")

    destination_zone, _ = WidgetZone.objects.get_or_create(
        slug="blog-sidebar-right",
        defaults={"name": "Blog Sidebar Right"},
    )
    widget = (
        Widget.objects.filter(
            widget_type="featured_tags",
            zone__slug="homepage-sidebar-left",
        )
        .order_by("pk")
        .first()
    )
    if not widget:
        return

    widget.zone = destination_zone
    widget.widget_type = "category_tag_cloud"
    widget.item_count = max(widget.item_count, 20)
    widget.save(update_fields=["zone", "widget_type", "item_count"])
    WidgetTranslation.objects.filter(master_id=widget.pk, language_code="es").update(
        title="Temas de esta categoría"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("widgets", "0012_alter_widget_widget_type"),
    ]

    operations = [
        migrations.RunPython(move_featured_tags_widget, migrations.RunPython.noop),
    ]
