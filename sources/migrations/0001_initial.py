from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import parler.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="Source",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=500, verbose_name="Title")),
                ("organisation", models.CharField(blank=True, max_length=250, verbose_name="Organisation or author")),
                ("source_type", models.CharField(choices=[("law", "Law or regulation"), ("directive", "Directive or international regulation"), ("official_guidance", "Official guidance"), ("standard", "Technical standard"), ("scientific_article", "Scientific article"), ("report", "Report"), ("book", "Book"), ("web", "Web resource"), ("other", "Other")], default="web", max_length=30, verbose_name="Source type")),
                ("publication_date", models.DateField(blank=True, null=True, verbose_name="Publication date")),
                ("language", models.CharField(choices=settings.LANGUAGES, default="es", max_length=10, verbose_name="Original language")),
                ("url", models.URLField(blank=True, verbose_name="Official URL")),
                ("bibliographic_reference", models.TextField(blank=True, verbose_name="Bibliographic reference")),
                ("summary", models.TextField(blank=True, verbose_name="Editorial notes")),
                ("status", models.CharField(choices=[("draft", "Draft"), ("verified", "Verified"), ("archived", "Archived")], default="draft", max_length=12, verbose_name="Verification status")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Source", "verbose_name_plural": "Sources", "ordering": ("organisation", "title")},
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="Citation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("object_id", models.PositiveBigIntegerField(verbose_name="Content ID")),
                ("language", models.CharField(choices=settings.LANGUAGES, default="es", max_length=10, verbose_name="Content language")),
                ("order", models.PositiveSmallIntegerField(default=1, verbose_name="Display order")),
                ("locator", models.CharField(blank=True, help_text="For example: Article 14, page 24, or section 3.", max_length=250, verbose_name="Page, section or locator")),
                ("note", models.TextField(blank=True, help_text="Optional explanation of how this source supports the content.", verbose_name="Editorial note")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("content_type", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="contenttypes.contenttype", verbose_name="Content type")),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="citations", to="sources.source", verbose_name="Source")),
            ],
            options={"verbose_name": "Citation", "verbose_name_plural": "Citations", "ordering": ("content_type", "object_id", "language", "order", "pk")},
        ),
        migrations.AddConstraint(
            model_name="citation",
            constraint=models.UniqueConstraint(fields=("source", "content_type", "object_id", "language"), name="unique_source_citation_per_content_language"),
        ),
    ]
