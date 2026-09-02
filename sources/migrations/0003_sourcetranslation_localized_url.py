from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sources", "0002_source_translations"),
    ]

    operations = [
        migrations.AddField(
            model_name="sourcetranslation",
            name="localized_url",
            field=models.URLField(blank=True, verbose_name="Official URL for this language"),
        ),
    ]
