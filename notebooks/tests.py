import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from notebooks.models import Notebook


User = get_user_model()


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish"), ("ca", "Catalan")))
class NotebookModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="notebook-author", password="x")

    def test_markdown_is_rendered_and_images_become_zoomable(self):
        notebook = Notebook.objects.create(
            author=self.user,
            status=Notebook.Status.PUBLISHED,
        )
        notebook.set_current_language("en")
        notebook.title = "Notebook"
        notebook.slug = "notebook"
        notebook.markdown_source = "# Heading\n\n![Alt](https://example.com/a.png)\n\n**Bold**"
        notebook.save()

        self.assertIn("<h1>Heading</h1>", notebook.rendered_html)
        self.assertIn('class="zoomable"', notebook.rendered_html)

    def test_markdown_keeps_data_uri_images_for_self_contained_exports(self):
        notebook = Notebook.objects.create(
            author=self.user,
            status=Notebook.Status.PUBLISHED,
        )
        notebook.set_current_language("en")
        notebook.title = "Notebook data"
        notebook.slug = "notebook-data"
        notebook.markdown_source = "![Inline](data:image/png;base64,ZmFrZQ==)"
        notebook.save()

        self.assertIn("data:image/png;base64,ZmFrZQ==", notebook.rendered_html)


@override_settings(LANGUAGES=(("en", "English"), ("es", "Spanish"), ("ca", "Catalan")))
class NotebookViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="notebook-view-author", password="x")

    def _create_notebook(self, *, status=Notebook.Status.PUBLISHED):
        notebook = Notebook.objects.create(
            author=self.user,
            status=status,
        )
        notebook.set_current_language("en")
        notebook.title = "Notebook view"
        notebook.slug = "notebook-view"
        notebook.abstract = "Abstract"
        notebook.markdown_source = "## Section\n\nNotebook body."
        notebook.trusted_html_fragment = '<div class="plotly-inline">plot</div>'
        notebook.meta_title = "Notebook meta"
        notebook.meta_description = "Notebook description"
        notebook.save()
        return notebook

    def test_list_view_shows_published_notebooks(self):
        notebook = self._create_notebook()

        response = self.client.get("/en/notebooks/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, notebook.translated_title)

    def test_detail_view_renders_markdown_and_trusted_html_fragment(self):
        notebook = self._create_notebook()

        response = self.client.get(reverse("notebooks:notebook_detail", kwargs={"slug": "notebook-view"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Section")
        self.assertContains(response, "Notebook body.")
        self.assertContains(response, 'class="plotly-inline"', html=False)

    def test_detail_view_returns_translation_unavailable_when_slug_exists_in_other_language(self):
        notebook = self._create_notebook()

        response = self.client.get("/es/notebooks/notebook-view/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response,
            "Este contenido no está disponible en este idioma.",
            status_code=404,
            html=False,
        )
