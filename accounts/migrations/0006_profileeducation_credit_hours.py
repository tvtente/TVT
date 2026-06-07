from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_profileeducation_dates"),
    ]

    operations = [
        migrations.AddField(
            model_name="profileeducation",
            name="credit_hours",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Total hours or credits completed for this course of study.",
                null=True,
                verbose_name="Number of credits",
            ),
        ),
        migrations.AlterModelOptions(
            name="profileeducation",
            options={
                "ordering": ["-end_date", "-end_year", "-start_date", "-start_year", "-id"],
                "verbose_name": "Education",
                "verbose_name_plural": "Education",
            },
        ),
    ]
