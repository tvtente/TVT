# File: accounts/forms.py
import logging
from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from django.utils.translation import get_language, gettext_lazy as _
from parler.forms import TranslatableModelForm

from widgets.widgets import CustomClearableFileInput

from .models import (
    Profile,
    ProfileCertification,
    ProfileCompetency,
    ProfileEducation,
    ProfileExperience,
    ProfileExternalPublication,
    ProfileLanguage,
    ProfileLink,
    ProfileSkill,
)

logger = logging.getLogger(__name__)


def _get_active_language_code():
    return (get_language() or "es").split("-")[0]


class TranslationAwareTranslatableModelForm(TranslatableModelForm):
    """
    Show the raw value of the active language for parler models without fallback.
    """

    translated_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.is_bound or not getattr(self, "instance", None) or not self.instance.pk:
            return

        language_code = _get_active_language_code()
        translation = self.instance.translations.filter(language_code=language_code).first()

        for field_name in self.translated_fields:
            if field_name not in self.fields:
                continue
            self.initial[field_name] = getattr(translation, field_name, "") if translation else ""


# --- 1. Custom SIGNUP Form (for new user registration) ---
class CustomUserCreationForm(UserCreationForm):
    """
    A custom form for new user registration.

    It only handles User model fields.
    Profile data is created automatically through the Profile post_save signal.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        # password1 and password2 are handled automatically by UserCreationForm.
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["password2"].help_text = None

        self.fields["username"].widget.attrs.update({
            "class": "form-control",
            "placeholder": _("Choose a username"),
        })
        self.fields["password1"].widget.attrs.update({
            "class": "form-control",
            "placeholder": _("Enter password"),
        })
        self.fields["password2"].widget.attrs.update({
            "class": "form-control",
            "placeholder": _("Confirm password"),
        })

        self.fields["username"].label = _("Username")
        self.fields["password1"].label = _("Password")
        self.fields["password2"].label = _("Confirm Password")


# --- 2. Custom User UPDATE Form (for editing basic User data) ---
class UserUpdateForm(forms.ModelForm):
    """
    A form for updating basic, non-sensitive user information.
    """

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["first_name"].label = _("First Name")
        self.fields["last_name"].label = _("Last Name")
        self.fields["email"].label = _("Contact Email")

        self.fields["first_name"].widget.attrs.update({
            "class": "form-control",
            "placeholder": _("Your first name"),
        })
        self.fields["last_name"].widget.attrs.update({
            "class": "form-control",
            "placeholder": _("Your last name"),
        })


# --- 3. Custom Profile UPDATE Form (for editing extended Profile data) ---
class ProfileUpdateForm(TranslationAwareTranslatableModelForm):
    """
    A form for updating the extended profile.

    This form is for the user's basic profile data.
    CV/resume sections are handled separately by profile CV formsets.
    """

    # We explicitly define the avatar field to force our custom widget.
    avatar = forms.ImageField(
        label=_("Profile Picture"),
        required=False,
        widget=CustomClearableFileInput(),
    )

    translated_fields = (
        "display_name",
        "professional_title",
        "headline",
        "institution",
        "country",
        "city",
        "areas_of_interest",
        "bio",
        "location",
    )

    class Meta:
        model = Profile
        fields = [
            "display_name",
            "professional_title",
            "headline",
            "institution",
            "country",
            "city",
            "orcid",
            "areas_of_interest",
            "is_researcher",
            "is_contributor",
            "bio",
            "location",
            "website_url",
            "avatar",
            "default_avatar_choice",
            "use_default_avatar",
            "is_listed_publicly",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply Bootstrap classes to the rest of the fields.
        self.fields["display_name"].widget.attrs.update({"class": "form-control"})
        self.fields["professional_title"].widget.attrs.update({"class": "form-control"})
        self.fields["headline"].widget.attrs.update({"class": "form-control"})
        self.fields["institution"].widget.attrs.update({"class": "form-control"})
        self.fields["country"].widget.attrs.update({"class": "form-control"})
        self.fields["city"].widget.attrs.update({"class": "form-control"})
        self.fields["orcid"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "0000-0000-0000-0000",
        })
        self.fields["areas_of_interest"].widget.attrs.update({
            "class": "form-control",
            "rows": 3,
        })
        self.fields["is_researcher"].widget.attrs.update({"class": "form-check-input"})
        self.fields["is_contributor"].widget.attrs.update({"class": "form-check-input"})
        self.fields["bio"].widget.attrs.update({
            "class": "form-control",
            "rows": 4,
        })
        self.fields["location"].widget.attrs.update({"class": "form-control"})
        self.fields["website_url"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "https://...",
        })
        self.fields["default_avatar_choice"].widget.attrs.update({"class": "form-select"})
        self.fields["use_default_avatar"].widget.attrs.update({"class": "form-check-input"})
        self.fields["is_listed_publicly"].widget.attrs.update({"class": "form-check-input"})

        logger.debug("ProfileUpdateForm initialized for instance: %s", self.instance)


# --- 4. Base CV / Resume Form ---
class BaseProfileCVForm(TranslationAwareTranslatableModelForm):
    """
    Base form for CV/resume sections.

    It applies Bootstrap classes consistently and filters catalog dropdowns
    to show only active parametrization values when the related catalog model
    has an `is_active` field.
    """

    select_fields = {
        "education_type",
        "experience_type",
        "certification_type",
        "level",
        "link_type",
        "publication_type",
        "skill_type",
        "competency_type",
    }

    checkbox_fields = {
        "is_current",
        "no_expiration",
        "DELETE",
    }

    textarea_fields = {
        "description",
    }

    date_fields = {
        "start_date",
        "end_date",
        "issue_date",
        "expiration_date",
        "publication_date",
    }

    number_fields = {
        "start_year",
        "end_year",
        "year",
        "order",
        "credit_hours",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            widget = field.widget

            # Filter catalog dropdowns to active values only.
            if hasattr(field, "queryset"):
                model = field.queryset.model
                if hasattr(model, "is_active"):
                    field.queryset = field.queryset.filter(
                        is_active=True
                    ).order_by("order", "slug")

            if field_name in self.select_fields:
                widget.attrs.update({"class": "form-select"})
            elif field_name in self.checkbox_fields:
                widget.attrs.update({"class": "form-check-input"})
            elif field_name in self.textarea_fields:
                widget.attrs.update({
                    "class": "form-control",
                    "rows": 3,
                })
            elif field_name in self.date_fields:
                widget.attrs.update({
                    "class": "form-control",
                    "type": "date",
                })
            elif field_name in self.number_fields:
                widget.attrs.update({"class": "form-control"})
            else:
                widget.attrs.update({"class": "form-control"})


# --- 5. CV / Resume Forms ---
class ProfileEducationForm(BaseProfileCVForm):
    """
    Form for one education item in the user's CV.
    """

    translated_fields = ("institution", "degree", "field_of_study", "description")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "is_current" in self.fields:
            self.fields["is_current"].help_text = _("If checked, the system will record today's date as the current end date.")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        is_current = bool(cleaned_data.get("is_current"))

        if not start_date:
            self.add_error("start_date", _("Start date is required."))

        if is_current:
            cleaned_data["end_date"] = date.today()
            cleaned_data["end_year"] = cleaned_data["end_date"].year
        elif not end_date:
            self.add_error("end_date", _("End date is required unless the entry is marked as current."))
        elif start_date and end_date and end_date < start_date:
            self.add_error("end_date", _("End date cannot be earlier than start date."))

        if start_date:
            cleaned_data["start_year"] = start_date.year
        elif not cleaned_data.get("start_year"):
            cleaned_data["start_year"] = None

        if not is_current and not end_date:
            cleaned_data["end_year"] = None

        return cleaned_data

    class Meta:
        model = ProfileEducation
        fields = [
            "education_type",
            "institution",
            "institution_url",
            "credit_hours",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "is_current",
            "description",
        ]


class ProfileExperienceForm(BaseProfileCVForm):
    """
    Form for one experience item in the user's CV.
    """

    translated_fields = (
        "organization",
        "position",
        "location",
        "description",
        "main_responsibilities",
        "key_achievements",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "is_current" in self.fields:
            self.fields["is_current"].help_text = _("If checked, the system will record today's date as the current end date.")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        is_current = bool(cleaned_data.get("is_current"))

        if not start_date:
            self.add_error("start_date", _("Start date is required."))

        if is_current:
            cleaned_data["end_date"] = date.today()
        elif not end_date:
            self.add_error("end_date", _("End date is required unless the entry is marked as current."))
        elif start_date and end_date and end_date < start_date:
            self.add_error("end_date", _("End date cannot be earlier than start date."))

        return cleaned_data

    class Meta:
        model = ProfileExperience
        fields = [
            "experience_type",
            "organization",
            "organization_url",
            "position",
            "start_date",
            "end_date",
            "is_current",
            "location",
            "description",
            "main_responsibilities",
            "key_achievements",
        ]


class ProfileCertificationForm(BaseProfileCVForm):
    """
    Form for one certification item in the user's CV.
    """

    translated_fields = ("name", "issuer", "description")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "no_expiration" in self.fields:
            self.fields["no_expiration"].help_text = _("Check this if the certification does not expire.")

    def clean(self):
        cleaned_data = super().clean()
        issue_date = cleaned_data.get("issue_date")
        expiration_date = cleaned_data.get("expiration_date")
        no_expiration = bool(cleaned_data.get("no_expiration"))

        if no_expiration:
            cleaned_data["expiration_date"] = None
        elif issue_date and not expiration_date:
            self.add_error("expiration_date", _("Expiration date is required unless the certification has no expiration."))
        elif issue_date and expiration_date and expiration_date < issue_date:
            self.add_error("expiration_date", _("Expiration date cannot be earlier than issue date."))

        return cleaned_data

    class Meta:
        model = ProfileCertification
        fields = [
            "certification_type",
            "name",
            "issuer",
            "issue_date",
            "expiration_date",
            "no_expiration",
            "credit_hours",
            "credential_id",
            "credential_url",
            "description",
        ]


class ProfileLanguageForm(BaseProfileCVForm):
    """
    Form for one language item in the user's CV.
    """

    translated_fields = ("language",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        level_field = self.fields.get("level")
        if level_field is not None:
            level_field.label_from_instance = lambda obj: (
                f"{obj.translated_name} - {obj.translated_description}"
                if obj.translated_description
                else obj.translated_name
            )

    class Meta:
        model = ProfileLanguage
        fields = [
            "language",
            "level",
        ]


class ProfileSkillForm(BaseProfileCVForm):
    """
    Form for one professional/technical skill item in the user's CV.

    The skill itself must come from ProfileSkillType.
    """

    translated_fields = ("description",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        skill_type_field = self.fields.get("skill_type")
        if skill_type_field is not None:
            skill_type_field.queryset = (
                skill_type_field.queryset
                .filter(is_active=True, children__isnull=True)
                .select_related("parent")
                .prefetch_related("translations", "parent__translations")
                .distinct()
            )
            skill_type_field.label_from_instance = lambda obj: obj.hierarchy_label

    class Meta:
        model = ProfileSkill
        fields = [
            "skill_type",
            "level",
        ]


class ProfileCompetencyForm(BaseProfileCVForm):
    """
    Form for one personal/transversal competency item in the user's CV.

    The competency itself must come from ProfileCompetencyType.
    """

    translated_fields = ("description",)

    class Meta:
        model = ProfileCompetency
        fields = [
            "competency_type",
            "level",
            "description",
            "order",
        ]


class ProfileLinkForm(BaseProfileCVForm):
    """
    Form for one professional/external profile link.
    """

    translated_fields = ()

    class Meta:
        model = ProfileLink
        fields = [
            "link_type",
            "url",
        ]


class ProfileExternalPublicationForm(BaseProfileCVForm):
    """
    Form for one external publication item.

    Internal TVT publications remain handled by publications.Publication.
    """

    translated_fields = ("title", "publisher", "description")

    class Meta:
        model = ProfileExternalPublication
        fields = [
            "publication_type",
            "title",
            "publisher",
            "publication_date",
            "url",
            "doi",
            "description",
        ]


# --- 6. CV / Resume Inline Formsets ---
# Each formset is linked to Profile. The logged-in user will only edit records
# attached to their own Profile from the frontend view.

ProfileEducationFormSet = inlineformset_factory(
    Profile,
    ProfileEducation,
    form=ProfileEducationForm,
    extra=0,
    can_delete=True,
)

ProfileExperienceFormSet = inlineformset_factory(
    Profile,
    ProfileExperience,
    form=ProfileExperienceForm,
    extra=0,
    can_delete=True,
)

ProfileCertificationFormSet = inlineformset_factory(
    Profile,
    ProfileCertification,
    form=ProfileCertificationForm,
    extra=0,
    can_delete=True,
)

ProfileLanguageFormSet = inlineformset_factory(
    Profile,
    ProfileLanguage,
    form=ProfileLanguageForm,
    extra=0,
    can_delete=True,
)

ProfileSkillFormSet = inlineformset_factory(
    Profile,
    ProfileSkill,
    form=ProfileSkillForm,
    extra=0,
    can_delete=True,
)

ProfileCompetencyFormSet = inlineformset_factory(
    Profile,
    ProfileCompetency,
    form=ProfileCompetencyForm,
    extra=0,
    can_delete=True,
)

ProfileLinkFormSet = inlineformset_factory(
    Profile,
    ProfileLink,
    form=ProfileLinkForm,
    extra=0,
    can_delete=True,
)

ProfileExternalPublicationFormSet = inlineformset_factory(
    Profile,
    ProfileExternalPublication,
    form=ProfileExternalPublicationForm,
    extra=0,
    can_delete=True,
)
