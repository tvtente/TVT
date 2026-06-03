from django.db import models
from parler.models import TranslatableModel, TranslatedFields
from django.utils.translation import gettext_lazy as _

class Testimonial(TranslatableModel):
    translations = TranslatedFields(
        quote = models.TextField(verbose_name=_("Quote")),
        author_name = models.CharField(max_length=100, verbose_name=_("Author")),
        author_title = models.CharField(max_length=100, blank=True, verbose_name=_("Title or Role")),
    )

    photo = models.ImageField(upload_to="testimonials/", blank=True, null=True, verbose_name=_("Photo"))
    is_active = models.BooleanField(default=True, verbose_name=_("Visible"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Testimonial")
        verbose_name_plural = _("Testimonials")

    def __str__(self):
        return self.safe_translation_getter("author_name", any_language=True)