import django.db.models.deletion
import parler.fields
import parler.models
from django.db import migrations, models


def copy_existing_sources_to_translations(apps, schema_editor):
    SourceTranslation = apps.get_model("sources", "SourceTranslation")

    # The old columns are deliberately still present in the database during
    # this transition, although they have already left Django's model state.
    # Reading them directly lets us preserve every existing source safely.
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, language, title, bibliographic_reference, summary FROM sources_source"
        )
        existing_sources = cursor.fetchall()

    for source_id, language, title, bibliographic_reference, summary in existing_sources:
        SourceTranslation.objects.get_or_create(
            master_id=source_id,
            language_code=language or "es",
            defaults={
                "title": title,
                "bibliographic_reference": bibliographic_reference,
                "summary": summary,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("sources", "0001_initial"),
    ]

    operations = [
        # Keep the legacy database columns until a later, dedicated cleanup
        # migration. This makes the first conversion reversible at the data
        # level while presenting the new translated model to Django.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name="source", name="bibliographic_reference"),
                migrations.RemoveField(model_name="source", name="summary"),
                migrations.RemoveField(model_name="source", name="title"),
            ],
            database_operations=[],
        ),
        migrations.CreateModel(
            name="SourceTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language_code", models.CharField(db_index=True, max_length=15, verbose_name="Language")),
                ("title", models.CharField(max_length=500, verbose_name="Title")),
                ("bibliographic_reference", models.TextField(blank=True, verbose_name="Bibliographic reference")),
                ("summary", models.TextField(blank=True, verbose_name="Editorial notes")),
                ("master", parler.fields.TranslationsForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="translations", to="sources.source")),
            ],
            options={
                "verbose_name": "Source Translation",
                "db_table": "sources_source_translation",
                "db_tablespace": "",
                "managed": True,
                "default_permissions": (),
                "unique_together": {("language_code", "master")},
            },
            bases=(parler.models.TranslatedFieldsModelMixin, models.Model),
        ),
        migrations.RunPython(copy_existing_sources_to_translations, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="source",
            options={"ordering": ("organisation", "pk"), "verbose_name": "Source", "verbose_name_plural": "Sources"},
        ),
    ]
