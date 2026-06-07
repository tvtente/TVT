from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_profileexperience_details"),
    ]

    operations = [
        migrations.AddField(
            model_name="profilecertification",
            name="credit_hours",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Total hours completed for this certification, if applicable.",
                null=True,
                verbose_name="Number of hours",
            ),
        ),
        migrations.AddField(
            model_name="profilecertification",
            name="no_expiration",
            field=models.BooleanField(default=False, verbose_name="No expiration"),
        ),
        migrations.AlterField(
            model_name="profilecertification",
            name="credential_id",
            field=models.CharField(
                blank=True,
                help_text="Internal reference, folio, or registration number associated with the credential.",
                max_length=120,
                verbose_name="Reference or record number",
            ),
        ),
    ]
