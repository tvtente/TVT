import logging

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static 
from django.core.exceptions import ObjectDoesNotExist, SuspiciousFileOperation, ValidationError
from parler.models import TranslatableModel, TranslatedFields
from django.utils import timezone


logger = logging.getLogger(__name__)


class ProfileCatalogBase(TranslatableModel):
    slug = models.SlugField(
        max_length=140,
        unique=True,
        verbose_name=_("Slug"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is active"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at"),
    )

    class Meta:
        abstract = True
        ordering = ["order", "slug"]

    def __str__(self):
        return self.safe_translation_getter("name", any_language=True) or self.slug

    @property
    def translated_name(self):
        return self.safe_translation_getter("name", any_language=True) or self.slug

    @property
    def translated_description(self):
        return self.safe_translation_getter("description", any_language=True) or ""


class ProfileLanguageLevel(ProfileCatalogBase):
    translations = TranslatedFields(
        name=models.CharField(max_length=120, verbose_name=_("Name")),
        description=models.TextField(blank=True, verbose_name=_("Description")),
    )

    class Meta(ProfileCatalogBase.Meta):
        verbose_name = _("Language level")
        verbose_name_plural = _("Language levels")


class ProfileSkillLevel(ProfileCatalogBase):
    translations = TranslatedFields(
        name=models.CharField(max_length=120, verbose_name=_("Name")),
        description=models.TextField(blank=True, verbose_name=_("Description")),
    )

    class Meta(ProfileCatalogBase.Meta):
        verbose_name = _("Skill level")
        verbose_name_plural = _("Skill levels")


class ProfileCompetencyLevel(ProfileCatalogBase):
    translations = TranslatedFields(
        name=models.CharField(max_length=120, verbose_name=_("Name")),
        description=models.TextField(blank=True, verbose_name=_("Description")),
    )

    class Meta(ProfileCatalogBase.Meta):
        verbose_name = _("Competency level")
        verbose_name_plural = _("Competency levels")

class ProfileSkillType(ProfileCatalogBase):
    translations = TranslatedFields(
        name=models.CharField(max_length=120, verbose_name=_("Name")),
        description=models.TextField(blank=True, verbose_name=_("Description")),
    )

    class Meta(ProfileCatalogBase.Meta):
        verbose_name = _("Skill type")
        verbose_name_plural = _("Skill types")


class ProfileCompetencyType(ProfileCatalogBase):
    translations = TranslatedFields(
        name=models.CharField(max_length=120, verbose_name=_("Name")),
        description=models.TextField(blank=True, verbose_name=_("Description")),
    )

    class Meta(ProfileCatalogBase.Meta):
        verbose_name = _("Competency type")
        verbose_name_plural = _("Competency types")

class ProfileLinkType(ProfileCatalogBase):
    translations = TranslatedFields(
        name=models.CharField(max_length=120, verbose_name=_("Name")),
        description=models.TextField(blank=True, verbose_name=_("Description")),
    )

    class Meta(ProfileCatalogBase.Meta):
        verbose_name = _("Profile link type")
        verbose_name_plural = _("Profile link types")


class ProfileExternalPublicationType(ProfileCatalogBase):
    translations = TranslatedFields(
        name=models.CharField(max_length=120, verbose_name=_("Name")),
        description=models.TextField(blank=True, verbose_name=_("Description")),
    )

    class Meta(ProfileCatalogBase.Meta):
        verbose_name = _("External publication type")
        verbose_name_plural = _("External publication types")


class ProfileExperienceType(ProfileCatalogBase):
    translations = TranslatedFields(
        name=models.CharField(max_length=120, verbose_name=_("Name")),
        description=models.TextField(blank=True, verbose_name=_("Description")),
    )

    class Meta(ProfileCatalogBase.Meta):
        verbose_name = _("Experience type")
        verbose_name_plural = _("Experience types")


class ProfileEducationType(ProfileCatalogBase):
    translations = TranslatedFields(
        name=models.CharField(max_length=120, verbose_name=_("Name")),
        description=models.TextField(blank=True, verbose_name=_("Description")),
    )

    class Meta(ProfileCatalogBase.Meta):
        verbose_name = _("Education type")
        verbose_name_plural = _("Education types")


class ProfileCertificationType(ProfileCatalogBase):
    translations = TranslatedFields(
        name=models.CharField(max_length=120, verbose_name=_("Name")),
        description=models.TextField(blank=True, verbose_name=_("Description")),
    )

    class Meta(ProfileCatalogBase.Meta):
        verbose_name = _("Certification type")
        verbose_name_plural = _("Certification types")


class Profile(TranslatableModel):
    """
    Extends Django's base User model to include additional user information,
    such as a display name, avatar, and bio.
    """
    
    # --- Avatar Choices Enumeration ---
    # This provides a user-friendly way to select a default avatar.
    class AvatarChoice(models.TextChoices):
        PRIVATE = 'images/avatars/default_private.png', _("Don't specify")
        FEMALE = 'images/avatars/default_female.png', _('Female')
        MALE = 'images/avatars/default_male.png', _('Male')
        NONBINARY = 'images/avatars/default_nonbinary.png', _('Non-binary')

    # --- Core Relationship ---
    # A One-to-One link to Django's built-in User model.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # --- Identity & Contact Fields ---
    public_email = models.EmailField(
        blank=True, 
        verbose_name=_("Public Email"),
        help_text=_("An email address you don't mind sharing publicly for contact.")
    )
    website_url = models.URLField(
        max_length=255, 
        blank=True, 
        verbose_name=_("Website URL")
    )

    # --- Profile Information Fields ---
    orcid = models.CharField(
        max_length=19,
        blank=True,
        verbose_name=_("ORCID"),
        help_text=_("ORCID iD format: 0000-0000-0000-0000"),
    )
    is_researcher = models.BooleanField(
        default=False,
        verbose_name=_("Is Researcher"),
        help_text=_("Mark if this profile belongs to a researcher."),
    )
    is_contributor = models.BooleanField(
        default=False,
        verbose_name=_("Is Contributor"),
        help_text=_("Mark if this user contributes to the project/community."),
    )
    translations = TranslatedFields(
        display_name=models.CharField(
            max_length=150,
            blank=True,
            verbose_name=_("Display Name"),
            help_text=_("Your full name or a nickname, which will be shown publicly."),
        ),
        location=models.CharField(
            max_length=100,
            blank=True,
            verbose_name=_("Location"),
        ),
        professional_title=models.CharField(
            max_length=150,
            blank=True,
            verbose_name=_("Professional Title"),
            help_text=_("Your role, for example: Researcher, Professor, Data Analyst."),
        ),
        headline=models.CharField(
            max_length=220,
            blank=True,
            verbose_name=_("Headline"),
            help_text=_("Short professional summary shown in public profile cards."),
        ),
        institution=models.CharField(
            max_length=180,
            blank=True,
            verbose_name=_("Institution"),
            help_text=_("Organization, university, lab, or company."),
        ),
        country=models.CharField(
            max_length=100,
            blank=True,
            verbose_name=_("Country"),
        ),
        city=models.CharField(
            max_length=100,
            blank=True,
            verbose_name=_("City"),
        ),
        areas_of_interest=models.TextField(
            blank=True,
            verbose_name=_("Areas of Interest"),
            help_text=_("Research/professional interests, separated by commas or lines."),
        ),
        bio=models.TextField(
            blank=True,
            verbose_name=_("Biography"),
        ),
    )
    
    # --- Avatar Fields ---
    avatar = models.ImageField(
        upload_to='avatars/', 
        default='images/avatars/default_private.png', 
        verbose_name=_("Avatar")
    )
    default_avatar_choice = models.CharField(
        max_length=100,
        choices=AvatarChoice.choices,
        default=AvatarChoice.PRIVATE,
        verbose_name=_("Default Avatar Preference")
    )
    use_default_avatar = models.BooleanField(
        default=True,
        verbose_name=_("Use default avatar"),
        help_text=_("If enabled, the selected default static avatar is always used."),
    )
    is_trusted_commenter = models.BooleanField(
        default=False,
        verbose_name=_("Is a Trusted Commenter?"),
        help_text=_("If checked, comments are automatically approved.")
    )
    is_listed_publicly = models.BooleanField(
        default=False, # consider False for new registrations.
                       # We will make this configurable in the signup process.
        verbose_name=_("List profile publicly?"),
        help_text=_("If checked, your profile will be visible in the public user directory.")
    )

    class Meta:
        verbose_name_plural = _("Profiles")
        permissions = [
            ("edit_professional_profile", _("Can edit professional profile fields")),
            ("edit_own_cv", _("Can edit own CV")),
            ("list_public_profile", _("Can list profile publicly")),
        ]

    # accounts/models.py
    def get_avatar_url(self):
        default_paths = [c[0] for c in self.AvatarChoice.choices]
        chosen_default = self.default_avatar_choice or self.AvatarChoice.PRIVATE
        if chosen_default not in default_paths:
            chosen_default = self.AvatarChoice.PRIVATE

        # Default avatar mode has priority over any uploaded file.
        if self.use_default_avatar:
            return static(chosen_default)

        avatar_name = (self.avatar.name or '').strip() if self.avatar else ''
        if avatar_name and avatar_name not in default_paths:
            try:
                storage = self.avatar.storage
                if storage.exists(avatar_name):
                    return self.avatar.url
            except (ValueError, OSError, SuspiciousFileOperation):
                pass

        # Fallback to static default if uploaded file is missing/broken.
        return static(chosen_default)
        
    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_display_name(self):
        """
        Returns the user's preferred display name, with fallbacks.
        Order of preference: Profile's display_name -> User's full_name -> User's username.
        """
        return (
            self.safe_translation_getter("display_name", any_language=True)
            or self.user.get_full_name()
            or self.user.username
        )

    @property
    def followers_count(self):
        return self.user.follower_links.count()

    @property
    def following_count(self):
        return self.user.following_links.count()

    @property
    def published_posts_count(self):
        return self.user.translated_posts.filter(status="published").count()

    def is_followed_by(self, user):
        if not getattr(user, "is_authenticated", False):
            return False
        return self.user.follower_links.filter(follower=user).exists()


class UserFollow(models.Model):
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="following_links",
        verbose_name=_("Follower"),
    )
    followed = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="follower_links",
        verbose_name=_("Followed user"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("User follow")
        verbose_name_plural = _("User follows")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("follower", "followed"),
                name="unique_user_follow_relation",
            ),
        ]

    def clean(self):
        if self.follower_id and self.follower_id == self.followed_id:
            raise ValidationError(_("Users cannot follow themselves."))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.follower.username} -> {self.followed.username}"


class UserNotification(models.Model):
    class NotificationType(models.TextChoices):
        FOLLOWED_AUTHOR_PUBLISHED_POST = (
            "followed_author_published_post",
            _("Followed author published post"),
        )
        COMMENT_ON_YOUR_POST = ("comment_on_your_post", _("Comment on your post"))
        REPLY_TO_YOUR_COMMENT = ("reply_to_your_comment", _("Reply to your comment"))
        POST_FAVORITED = ("post_favorited", _("Post favorited"))
        YOUR_BOOK_PURCHASED = ("your_book_purchased", _("Your book purchased"))

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Recipient"),
    )
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="triggered_notifications",
        verbose_name=_("Actor"),
    )
    notification_type = models.CharField(
        max_length=64,
        choices=NotificationType.choices,
        verbose_name=_("Notification type"),
    )
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    message = models.TextField(verbose_name=_("Message"))
    url = models.CharField(max_length=500, blank=True, verbose_name=_("URL"))
    payload = models.JSONField(default=dict, blank=True, verbose_name=_("Payload"))
    dedupe_key = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name=_("Dedupe key"),
    )
    related_post = models.ForeignKey(
        "posts.Post",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
        verbose_name=_("Related post"),
    )
    is_read = models.BooleanField(default=False, db_index=True, verbose_name=_("Is read"))
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Read at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        verbose_name = _("User notification")
        verbose_name_plural = _("User notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
            models.Index(fields=["recipient", "notification_type"]),
        ]

    def mark_as_read(self):
        if self.is_read:
            return
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at"])

    def __str__(self):
        return f"{self.recipient.username}: {self.title}"


class ProfileEducation(TranslatableModel):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="education_items",
        verbose_name=_("Profile"),
    )
    education_type = models.ForeignKey(
        ProfileEducationType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Education type"),
    )
    institution_url = models.URLField(
        max_length=300,
        blank=True,
        verbose_name=_("Institution URL"),
    )
    start_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Start year"),
    )
    end_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("End year"),
    )
    is_current = models.BooleanField(
        default=False,
        verbose_name=_("Is current"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
    )
    translations = TranslatedFields(
        institution=models.CharField(
            max_length=180,
            verbose_name=_("Institution"),
        ),
        degree=models.CharField(
            max_length=180,
            blank=True,
            verbose_name=_("Degree"),
        ),
        field_of_study=models.CharField(
            max_length=180,
            blank=True,
            verbose_name=_("Field of study"),
        ),
        description=models.TextField(
            blank=True,
            verbose_name=_("Description"),
        ),
    )

    class Meta:
        verbose_name = _("Education")
        verbose_name_plural = _("Education")
        ordering = ["order", "-start_year", "id"]

    def __str__(self):
        if self.degree:
            return f"{self.institution} - {self.degree}"
        return self.institution


class ProfileExperience(TranslatableModel):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="experience_items",
        verbose_name=_("Profile"),
    )
    experience_type = models.ForeignKey(
        ProfileExperienceType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Experience type"),
    )
    organization_url = models.URLField(
        max_length=300,
        blank=True,
        verbose_name=_("Organization URL"),
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Start date"),
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("End date"),
    )
    is_current = models.BooleanField(
        default=False,
        verbose_name=_("Is current"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
    )
    translations = TranslatedFields(
        organization=models.CharField(
            max_length=180,
            verbose_name=_("Organization"),
        ),
        position=models.CharField(
            max_length=180,
            verbose_name=_("Position"),
        ),
        location=models.CharField(
            max_length=150,
            blank=True,
            verbose_name=_("Location"),
        ),
        description=models.TextField(
            blank=True,
            verbose_name=_("Description"),
        ),
    )

    class Meta:
        verbose_name = _("Experience")
        verbose_name_plural = _("Experience")
        ordering = ["order", "-start_date", "id"]

    def __str__(self):
        return f"{self.position} at {self.organization}"


class ProfileCertification(TranslatableModel):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="certification_items",
        verbose_name=_("Profile"),
    )
    certification_type = models.ForeignKey(
        ProfileCertificationType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Certification type"),
    )
    issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Issue date"),
    )
    expiration_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Expiration date"),
    )
    credential_id = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("Credential ID"),
    )
    credential_url = models.URLField(
        max_length=300,
        blank=True,
        verbose_name=_("Credential URL"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
    )
    translations = TranslatedFields(
        name=models.CharField(
            max_length=180,
            verbose_name=_("Name"),
        ),
        issuer=models.CharField(
            max_length=180,
            blank=True,
            verbose_name=_("Issuer"),
        ),
        description=models.TextField(
            blank=True,
            verbose_name=_("Description"),
        ),
    )

    class Meta:
        verbose_name = _("Certification")
        verbose_name_plural = _("Certifications")
        ordering = ["order", "-issue_date", "id"]

    def __str__(self):
        if self.issuer:
            return f"{self.name} - {self.issuer}"
        return self.name


class ProfileLanguage(TranslatableModel):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="language_items",
        verbose_name=_("Profile"),
    )
    level = models.ForeignKey(
        ProfileLanguageLevel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Level"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
    )
    translations = TranslatedFields(
        language=models.CharField(
            max_length=100,
            verbose_name=_("Language"),
        ),
    )

    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")
        ordering = ["order", "id"]

    def __str__(self):
        if self.level:
            return f"{self.language} - {self.level}"
        return self.language

class ProfileSkill(TranslatableModel):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="skill_items",
        verbose_name=_("Profile"),
    )
    skill_type = models.ForeignKey(
        ProfileSkillType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Skill type"),
    )
    level = models.ForeignKey(
        ProfileSkillLevel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Level"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
    )
    translations = TranslatedFields(
        description=models.TextField(
            blank=True,
            verbose_name=_("Description"),
        ),
    )

    class Meta:
        verbose_name = _("Skill")
        verbose_name_plural = _("Skills")
        ordering = ["order", "skill_type__slug", "id"]

    def __str__(self):
        return str(self.skill_type) if self.skill_type else _("Skill")


class ProfileCompetency(TranslatableModel):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="competency_items",
        verbose_name=_("Profile"),
    )
    competency_type = models.ForeignKey(
        ProfileCompetencyType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Competency type"),
    )
    level = models.ForeignKey(
        ProfileCompetencyLevel,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Level"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
    )
    translations = TranslatedFields(
        description=models.TextField(
            blank=True,
            verbose_name=_("Description"),
        ),
    )

    class Meta:
        verbose_name = _("Competency")
        verbose_name_plural = _("Competencies")
        ordering = ["order", "competency_type__slug", "id"]

    def __str__(self):
        return str(self.competency_type) if self.competency_type else _("Competency")


class ProfileLink(TranslatableModel):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="link_items",
        verbose_name=_("Profile"),
    )
    url = models.URLField(
        max_length=300,
        verbose_name=_("URL"),
    )
    link_type = models.ForeignKey(
        ProfileLinkType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Link type"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
    )
    translations = TranslatedFields(
        label=models.CharField(
            max_length=120,
            verbose_name=_("Label"),
        ),
    )

    class Meta:
        verbose_name = _("Profile Link")
        verbose_name_plural = _("Profile Links")
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class ProfileExternalPublication(TranslatableModel):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="external_publication_items",
        verbose_name=_("Profile"),
    )
    publication_type = models.ForeignKey(
        ProfileExternalPublicationType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Publication type"),
    )
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Year"),
    )
    url = models.URLField(
        max_length=300,
        blank=True,
        verbose_name=_("URL"),
    )
    doi = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("DOI"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
    )
    translations = TranslatedFields(
        title=models.CharField(
            max_length=250,
            verbose_name=_("Title"),
        ),
        publisher=models.CharField(
            max_length=180,
            blank=True,
            verbose_name=_("Publisher"),
        ),
        description=models.TextField(
            blank=True,
            verbose_name=_("Description"),
        ),
    )

    class Meta:
        verbose_name = _("External Publication")
        verbose_name_plural = _("External Publications")
        ordering = ["order", "-year", "id"]

    def __str__(self):
        return self.title


# --- Django Signal to Automate Profile Creation ---
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Signal to automatically create a Profile when a new User is created.
    """
    if kwargs.get("raw", False):
        return
    if created:
        # Simply create the profile. Django will handle the default avatar.
        Profile.objects.create(user=instance)

    # This part ensures that if you save a User, its related Profile
    # is also saved, which can be useful for other signals.
    if hasattr(instance, 'profile'):
        instance.profile.save()


def get_user_avatar_url(user):
    """
    Returns a safe avatar URL for any user-like object.
    Never raises due to missing profile/avatar/missing media file.
    """
    fallback = static(Profile.AvatarChoice.PRIVATE)
    if not user:
        return fallback
    try:
        profile = user.profile
    except ObjectDoesNotExist:
        return fallback
    except AttributeError:
        logger.warning(
            _("Failed to resolve the user profile while building the avatar URL."),
            exc_info=True,
        )
        return fallback
    if not profile:
        return fallback
    try:
        return profile.get_avatar_url()
    except (AttributeError, ValueError, OSError, SuspiciousFileOperation):
        logger.warning(
            _("Failed to resolve the user avatar URL from the profile."),
            exc_info=True,
        )
        return fallback
