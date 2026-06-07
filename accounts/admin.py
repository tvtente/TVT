# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.sites import NotRegistered
from django.utils.translation import gettext_lazy as _
from allauth.socialaccount.models import SocialApp, SocialToken
from parler.admin import TranslatableAdmin, TranslatableStackedInline

from .models import (
    Profile,
    ProfileCertificationType,
    ProfileCompetencyLevel,
    ProfileCompetencyType,
    ProfileEducationType,
    ProfileExperienceType,
    ProfileExternalPublicationType,
    ProfileLanguageLevel,
    ProfileLinkType,
    ProfileSkillLevel,
    ProfileSkillType,
    UserFollow,
    UserNotification,
)


class ProfileInline(TranslatableStackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "profile"

    fieldsets = (
        (_("Identity"), {
            "fields": ("display_name", "public_email", "website_url"),
        }),
        (_("Professional"), {
            "fields": (
                "professional_title",
                "headline",
                "institution",
                "country",
                "city",
                "orcid",
                "areas_of_interest",
                "is_researcher",
                "is_contributor",
            ),
        }),
        (_("Profile"), {
            "fields": ("bio", "location", "is_listed_publicly", "is_trusted_commenter"),
        }),
        (_("Avatar"), {
            "fields": ("avatar", "default_avatar_choice", "use_default_avatar"),
        }),
    )


class UserAdmin(BaseUserAdmin):
    """
    Custom User admin for TVT.

    Permission strategy:
    - Users receive permissions through Django Groups / roles.
    - Direct per-user permissions are hidden from the admin to avoid confusion.
    - is_staff is kept because it controls access to Django admin.
    - is_superuser is kept for absolute administrators only.
    """

    inlines = (ProfileInline,)

    fieldsets = (
        (None, {
            "fields": ("username", "password"),
        }),
        (_("Personal info"), {
            "fields": ("first_name", "last_name", "email"),
        }),
        (_("Permissions"), {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
            ),
            "description": _(
                "Assign roles through groups. Direct per-user permissions are intentionally hidden."
            ),
        }),
        (_("Important dates"), {
            "fields": ("last_login", "date_joined"),
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "usable_password", "password1", "password2"),
        }),
    )

    filter_horizontal = ("groups",)


class ProfileCatalogAdmin(TranslatableAdmin):
    list_display = ("current_name", "slug", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("translations__name", "slug", "translations__description")
    ordering = ("order", "slug")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    @admin.display(description=_("Name"))
    def current_name(self, obj):
        return obj.translated_name


class ProfileSkillTypeAdmin(ProfileCatalogAdmin):
    list_display = ("current_name", "parent_name", "slug", "order", "is_active")
    list_filter = ("is_active", "parent")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("parent")
            .prefetch_related("parent__translations")
        )

    @admin.display(description=_("Category"))
    def parent_name(self, obj):
        if not obj.parent_id:
            return "—"
        return obj.parent.translated_name


@admin.register(Profile)
class ProfileAdmin(TranslatableAdmin):
    list_display = (
        "user",
        "current_display_name",
        "current_professional_title",
        "current_institution",
        "is_researcher",
        "is_contributor",
        "is_listed_publicly",
    )
    list_filter = (
        "is_researcher",
        "is_contributor",
        "is_listed_publicly",
        "is_trusted_commenter",
    )
    search_fields = (
        "user__username",
        "user__email",
        "translations__display_name",
        "translations__professional_title",
        "translations__institution",
        "orcid",
    )
    fieldsets = (
        (_("Identity"), {
            "fields": ("user", "display_name", "public_email", "website_url"),
        }),
        (_("Professional"), {
            "fields": (
                "professional_title",
                "headline",
                "institution",
                "country",
                "city",
                "orcid",
                "areas_of_interest",
                "is_researcher",
                "is_contributor",
            ),
        }),
        (_("Profile"), {
            "fields": ("bio", "location"),
        }),
        (_("Avatar"), {
            "fields": ("avatar", "default_avatar_choice", "use_default_avatar"),
        }),
        (_("Moderation / Visibility"), {
            "fields": ("is_trusted_commenter", "is_listed_publicly"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("translations")

    @admin.display(description=_("Display Name"))
    def current_display_name(self, obj):
        return obj.safe_translation_getter("display_name", any_language=True)

    @admin.display(description=_("Professional Title"))
    def current_professional_title(self, obj):
        return obj.safe_translation_getter("professional_title", any_language=True)

    @admin.display(description=_("Institution"))
    def current_institution(self, obj):
        return obj.safe_translation_getter("institution", any_language=True)


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "followed", "created_at")
    list_filter = ("created_at",)
    search_fields = ("follower__username", "followed__username")
    autocomplete_fields = ("follower", "followed")


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "notification_type",
        "actor",
        "short_title",
        "is_read",
        "created_at",
    )
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = (
        "recipient__username",
        "actor__username",
        "title",
        "message",
        "dedupe_key",
    )
    autocomplete_fields = ("recipient", "actor", "related_post")
    date_hierarchy = "created_at"

    @admin.display(description=_("Title"))
    def short_title(self, obj):
        return obj.title[:80]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

for social_model in (SocialApp, SocialToken):
    try:
        admin.site.unregister(social_model)
    except NotRegistered:
        pass

admin.site.register(ProfileLanguageLevel, ProfileCatalogAdmin)
admin.site.register(ProfileSkillLevel, ProfileCatalogAdmin)
admin.site.register(ProfileSkillType, ProfileSkillTypeAdmin)
admin.site.register(ProfileCompetencyLevel, ProfileCatalogAdmin)
admin.site.register(ProfileCompetencyType, ProfileCatalogAdmin)
admin.site.register(ProfileLinkType, ProfileCatalogAdmin)
admin.site.register(ProfileExternalPublicationType, ProfileCatalogAdmin)
admin.site.register(ProfileExperienceType, ProfileCatalogAdmin)
admin.site.register(ProfileEducationType, ProfileCatalogAdmin)
admin.site.register(ProfileCertificationType, ProfileCatalogAdmin)
