from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("gallery", "0002_stagedupload_convert_to_webp"),
        ("posts", "0006_post_archived_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="PostContentBlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language", models.CharField(choices=settings.LANGUAGES, default="es", max_length=10, verbose_name="Content language")),
                ("order", models.PositiveSmallIntegerField(default=1, verbose_name="Display order")),
                ("block_type", models.CharField(choices=[("content", "Content with image"), ("related_post", "Reference to another post")], default="content", max_length=20, verbose_name="Block type")),
                ("anchor", models.SlugField(blank=True, help_text="Optional URL fragment for linking directly to this section.", max_length=120, verbose_name="Section anchor")),
                ("heading", models.CharField(blank=True, max_length=250, verbose_name="Section title")),
                ("content", models.TextField(blank=True, verbose_name="Section content")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("image_asset", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="post_content_blocks", to="gallery.image", verbose_name="16:9 image from media library")),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_blocks", to="posts.post", verbose_name="Post")),
                ("related_post", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="referenced_by_content_blocks", to="posts.post", verbose_name="Referenced post")),
            ],
            options={
                "verbose_name": "Post content block",
                "verbose_name_plural": "Post content blocks",
                "ordering": ("language", "order", "pk"),
            },
        ),
    ]
