from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0005_post_mobile_image_asset"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", _("Draft")),
                    ("published", _("Published")),
                    ("archived", _("Archived")),
                ],
                default="draft",
                max_length=10,
                verbose_name="Status",
            ),
        ),
    ]
