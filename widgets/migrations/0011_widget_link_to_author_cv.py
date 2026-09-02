from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("widgets", "0010_widget_page_card")]

    operations = [
        migrations.AddField(
            model_name="widget",
            name="link_to_author_cv",
            field=models.BooleanField(
                default=False,
                help_text="For a featured profile page, link to the author's public CV when it is available in the selected language.",
                verbose_name="Prefer the author's public CV",
            ),
        ),
    ]
