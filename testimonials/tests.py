from django.test import TestCase
from django.urls import reverse

from testimonials.models import Testimonial


class TestimonialViewsTests(TestCase):
    def _create_testimonial(self, *, author_name, is_active):
        testimonial = Testimonial.objects.create(is_active=is_active)
        testimonial.set_current_language("en")
        testimonial.quote = f"Quote by {author_name}"
        testimonial.author_name = author_name
        testimonial.author_title = "Contributor"
        testimonial.save()
        return testimonial

    def test_testimonial_list_shows_only_active_testimonials(self):
        active = self._create_testimonial(author_name="Active author", is_active=True)
        self._create_testimonial(author_name="Hidden author", is_active=False)

        response = self.client.get(reverse("testimonials:testimonial_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["testimonials"]), [active])
        self.assertContains(response, "Active author")
        self.assertNotContains(response, "Hidden author")
