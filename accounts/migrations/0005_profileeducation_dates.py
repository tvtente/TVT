from datetime import date

from django.db import migrations, models


def forwards_copy_education_years_to_dates(apps, schema_editor):
    ProfileEducation = apps.get_model("accounts", "ProfileEducation")
    today = date.today()

    for item in ProfileEducation.objects.all().iterator():
        changed = False

        if item.start_year and not item.start_date:
            item.start_date = date(item.start_year, 1, 1)
            changed = True

        if item.is_current:
            if item.end_date != today:
                item.end_date = today
                changed = True
        elif item.end_year and not item.end_date:
            item.end_date = date(item.end_year, 12, 31)
            changed = True

        if changed:
            item.save(update_fields=["start_date", "end_date"])


def backwards_copy_education_dates_to_years(apps, schema_editor):
    ProfileEducation = apps.get_model("accounts", "ProfileEducation")

    for item in ProfileEducation.objects.all().iterator():
        changed = False

        if item.start_date and item.start_year != item.start_date.year:
            item.start_year = item.start_date.year
            changed = True

        if item.end_date and item.end_year != item.end_date.year:
            item.end_year = item.end_date.year
            changed = True

        if changed:
            item.save(update_fields=["start_year", "end_year"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_alter_usernotification_related_post"),
    ]

    operations = [
        migrations.AddField(
            model_name="profileeducation",
            name="end_date",
            field=models.DateField(blank=True, null=True, verbose_name="End date"),
        ),
        migrations.AddField(
            model_name="profileeducation",
            name="start_date",
            field=models.DateField(blank=True, null=True, verbose_name="Start date"),
        ),
        migrations.RunPython(
            forwards_copy_education_years_to_dates,
            backwards_copy_education_dates_to_years,
        ),
    ]
