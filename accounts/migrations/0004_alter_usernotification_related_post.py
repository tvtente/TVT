from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0005_post_mobile_image_asset"),
        ("accounts", "0003_usernotification"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usernotification",
            name="related_post",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="notifications",
                to="posts.post",
                verbose_name="Related post",
            ),
        ),
    ]
