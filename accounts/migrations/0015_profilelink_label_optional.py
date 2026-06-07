from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_force_curated_competency_activation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profilelinktranslation",
            name="label",
            field=models.CharField(blank=True, max_length=120, verbose_name="Label"),
        ),
    ]
