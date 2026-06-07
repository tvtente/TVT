from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0016_external_publication_date"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="profileexternalpublication",
            options={
                "ordering": ["-publication_date", "-id", "order"],
                "verbose_name": "External Publication",
                "verbose_name_plural": "External Publications",
            },
        ),
    ]
