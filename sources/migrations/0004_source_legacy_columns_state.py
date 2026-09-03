from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sources", "0003_sourcetranslation_localized_url"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="source",
                    name="legacy_title",
                    field=models.CharField(
                        db_column="title",
                        default="",
                        editable=False,
                        max_length=500,
                    ),
                ),
                migrations.AddField(
                    model_name="source",
                    name="legacy_bibliographic_reference",
                    field=models.TextField(
                        db_column="bibliographic_reference",
                        default="",
                        editable=False,
                    ),
                ),
                migrations.AddField(
                    model_name="source",
                    name="legacy_summary",
                    field=models.TextField(
                        db_column="summary",
                        default="",
                        editable=False,
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
