from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_profileeducation_credit_hours"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="profileexperience",
            options={
                "ordering": ["-end_date", "-start_date", "-id"],
                "verbose_name": "Experience",
                "verbose_name_plural": "Experience",
            },
        ),
        migrations.AddField(
            model_name="profileexperiencetranslation",
            name="key_achievements",
            field=models.TextField(blank=True, verbose_name="Key achievements or projects"),
        ),
        migrations.AddField(
            model_name="profileexperiencetranslation",
            name="main_responsibilities",
            field=models.TextField(blank=True, verbose_name="Main responsibilities"),
        ),
        migrations.AlterField(
            model_name="profileexperiencetranslation",
            name="description",
            field=models.TextField(blank=True, verbose_name="Company description"),
        ),
    ]
