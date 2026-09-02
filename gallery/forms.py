from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from gallery.models import Image, StagedUpload


class ImageAddForm(forms.ModelForm):
    slug_input = forms.SlugField(
        label=_("Slug (filename base)"),
        help_text=_("Stored as gallery/{slug}.ext; numeric suffixes are added if needed."),
    )
    staging_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    source_image_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    convert_to_webp = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Convert to WebP"),
        help_text=_("Enabled by default. Disable to preserve the uploaded format, for example a PNG."),
    )

    class Meta:
        model = Image
        fields = (
            "title",
            "description",
            "language",
            "slug_input",
            "staging_id",
            "source_image_id",
            "image",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].required = False
        self.fields["description"].required = False

    def clean(self):
        cleaned = super().clean()
        staging = cleaned.get("staging_id")
        source = cleaned.get("source_image_id")
        has_file = bool(cleaned.get("image"))

        if staging and source:
            raise ValidationError(
                _("Choose either a staged upload, an existing library image, or a direct file upload."),
            )

        if source and not Image.objects.filter(pk=source).exists():
            raise ValidationError({"source_image_id": _("Selected library image is no longer available.")})

        if staging and not StagedUpload.objects.filter(pk=staging).exists():
            raise ValidationError({"staging_id": _("The staged upload expired or was removed. Upload again.")})

        if not staging and not source and not has_file:
            raise ValidationError(
                {"image": _("Upload an image or use the media library.")},
            )

        return cleaned


class ImageChangeForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ("title", "description", "language")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = False
