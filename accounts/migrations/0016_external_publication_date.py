import datetime

from django.db import migrations, models


def copy_year_to_publication_date(apps, schema_editor):
    ProfileExternalPublication = apps.get_model("accounts", "ProfileExternalPublication")

    for item in ProfileExternalPublication.objects.exclude(year__isnull=True):
        if item.year:
            item.publication_date = datetime.date(item.year, 1, 1)
            item.save(update_fields=["publication_date"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0015_profilelink_label_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="profileexternalpublication",
            name="publication_date",
            field=models.DateField(blank=True, null=True, verbose_name="Publication date"),
        ),
        migrations.RunPython(copy_year_to_publication_date, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="profileexternalpublication",
            name="year",
        ),
    ]
