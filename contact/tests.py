from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from contact.models import ContactMessage


class ContactViewTests(TestCase):
    def test_get_renders_blank_contact_form(self):
        response = self.client.get(reverse("contact:contact_form"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_post_valid_form_creates_message_and_redirects_with_success_message(self):
        response = self.client.post(
            reverse("contact:contact_form"),
            {
                "name": "Ada Lovelace",
                "email": "ada@example.com",
                "subject": "Collaboration",
                "message": "I would like to collaborate.",
            },
            follow=True,
        )

        self.assertEqual(response.redirect_chain[-1][0], reverse("contact:contact_form") + "#contact-form")
        self.assertEqual(ContactMessage.objects.count(), 1)
        message = ContactMessage.objects.get()
        self.assertEqual(message.name, "Ada Lovelace")
        self.assertEqual(message.priority, ContactMessage.Priority.MEDIUM)

        flash_messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Thank you for your message! We will get back to you shortly.", flash_messages)

    def test_post_invalid_form_does_not_create_message(self):
        response = self.client.post(
            reverse("contact:contact_form"),
            {
                "name": "",
                "email": "invalid-email",
                "subject": "",
                "message": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertTrue(response.context["form"].errors)
