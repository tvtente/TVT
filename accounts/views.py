# File: accounts/views.py
from collections import OrderedDict
from datetime import date
import logging
import os
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from django.utils.translation import get_language, gettext, override

from core.pagination import get_site_config_int, paginate_queryset
from publications.models import Publication

from .reportlab_pdf import build_public_profile_pdf_bytes
from .forms import (
    CustomUserCreationForm,
    UserUpdateForm,
    ProfileUpdateForm,
    ProfileEducationFormSet,
    ProfileExperienceFormSet,
    ProfileCertificationFormSet,
    ProfileLanguageFormSet,
    ProfileLinkFormSet,
    ProfileExternalPublicationFormSet,
)

from .models import (
    Profile,
    ProfileEducation,
    ProfileExperience,
    ProfileCertification,
    ProfileLanguage,
    ProfileSkill,
    ProfileSkillType,
    ProfileCompetency,
    ProfileCompetencyType,
    ProfileLink,
    ProfileExternalPublication,
    UserFollow,
    UserNotification,
)
from .services import create_new_follower_notification

from posts.models import Post
from comments.models import Comment
from site_settings.models import SiteConfiguration, SiteTemplate


logger = logging.getLogger(__name__)
User = get_user_model()
CURATED_COMPETENCY_SLUGS = (
    "analytical-thinking",
    "problem-solving",
    "continuous-learning",
    "autonomy",
    "technical-leadership",
    "communication",
    "teamwork",
    "adaptability",
    "attention-to-detail",
    "decision-making",
    "time-management",
    "research-rigor",
)

PROFILE_TRANSLATABLE_FIELDS = (
    "display_name",
    "location",
    "professional_title",
    "headline",
    "institution",
    "country",
    "city",
    "areas_of_interest",
    "bio",
)

PROFILE_ITEM_TRANSLATABLE_FIELDS = {
    "education_items": ("institution", "degree", "field_of_study", "description"),
    "experience_items": ("organization", "position", "location", "description"),
    "certification_items": ("name", "issuer", "description"),
    "language_items": ("language",),
    "skill_items": ("description",),
    "competency_items": ("description",),
    "link_items": ("label",),
    "external_publication_items": ("title", "publisher", "description"),
}


def _remove_previous_avatar_file_if_custom(profile):
    """Delete uploaded avatar safely; never raise if file is missing."""
    if not profile.avatar or not profile.avatar.name:
        return

    default_paths = [choice[0] for choice in profile.AvatarChoice.choices]
    avatar_name = (profile.avatar.name or "").strip()

    if not avatar_name or avatar_name in default_paths:
        return

    try:
        storage = profile.avatar.storage
        if storage.exists(avatar_name):
            storage.delete(avatar_name)
    except (FileNotFoundError, OSError, NotImplementedError):
        logger.warning(
            gettext("Failed to delete the previous custom avatar file."),
            exc_info=True,
        )
        return


def _get_profile_cv_formset_definitions():
    """
    Returns the CV/resume formset definitions used by the profile CV editor.

    Each tuple contains:
    - context key
    - human readable title
    - formset class
    - prefix used in POST data
    """
    return (
        ("education_formset", gettext("Education"), ProfileEducationFormSet, "education"),
        ("experience_formset", gettext("Experience"), ProfileExperienceFormSet, "experience"),
        ("certification_formset", gettext("Certifications"), ProfileCertificationFormSet, "certifications"),
        ("language_formset", gettext("Languages"), ProfileLanguageFormSet, "languages"),
        ("link_formset", gettext("Professional Links"), ProfileLinkFormSet, "links"),
        ("external_publication_formset", gettext("External Publications"), ProfileExternalPublicationFormSet, "external_publications"),
    )


def _user_can_edit_professional_profile(user):
    return user.has_perm("accounts.edit_professional_profile")


def _user_can_edit_own_cv(user):
    return user.has_perm("accounts.edit_own_cv")


def build_technical_skill_groups(skill_items):
    groups = OrderedDict()

    for item in skill_items:
        skill_type = getattr(item, "skill_type", None)
        if skill_type is None:
            continue

        category = skill_type.parent if skill_type.parent_id else skill_type
        category_key = category.pk or category.slug
        group = groups.setdefault(
            category_key,
            {
                "category": category,
                "category_name": category.translated_name,
                "items": [],
            },
        )
        group["items"].append(item)

    return list(groups.values())


def _coerce_period_bounds(item, start_attr="start_date", end_attr="end_date", start_year_attr="start_year", end_year_attr="end_year", current_attr="is_current"):
    start_value = getattr(item, start_attr, None)
    end_value = getattr(item, end_attr, None)

    if start_value is None:
        start_year = getattr(item, start_year_attr, None)
        if start_year:
            start_value = date(start_year, 1, 1)

    if end_value is None:
        if getattr(item, current_attr, False):
            end_value = timezone.localdate()
        else:
            end_year = getattr(item, end_year_attr, None)
            if end_year:
                end_value = date(end_year, 12, 31)

    if start_value is None or end_value is None or end_value < start_value:
        return None, None

    return start_value, end_value


def _calculate_total_years(items, **kwargs):
    total_days = 0
    for item in items:
        start_value, end_value = _coerce_period_bounds(item, **kwargs)
        if start_value is None or end_value is None:
            continue
        total_days += (end_value - start_value).days + 1

    if total_days <= 0:
        return None

    years = round(total_days / 365.25, 1)
    if years.is_integer():
        return str(int(years))
    return f"{years:.1f}"


def get_skill_category_catalog():
    categories = (
        ProfileSkillType.objects.filter(
            parent__isnull=True,
            is_active=True,
        )
        .prefetch_related("translations", "children__translations")
        .order_by("order", "slug")
    )

    catalog = []
    for category in categories:
        children = [
            child
            for child in category.children.all()
            if child.is_active
        ]
        if not children:
            continue
        children = sorted(children, key=lambda child: (child.order, child.slug))
        catalog.append(
            {
                "id": category.pk,
                "name": category.translated_name,
                "technologies": [
                    {
                        "id": child.pk,
                        "name": child.translated_name,
                    }
                    for child in children
                ],
            }
        )
    return catalog


def get_competency_catalog():
    competencies = (
        ProfileCompetencyType.objects.filter(
            is_active=True,
            slug__in=CURATED_COMPETENCY_SLUGS,
        )
        .prefetch_related("translations")
        .order_by("order", "slug")
    )
    return [
        {
            "id": competency.pk,
            "name": competency.translated_name,
            "description": competency.translated_description,
        }
        for competency in competencies
    ]


def build_skill_editor_rows(profile):
    rows = []
    for group in build_technical_skill_groups(profile.skill_items.select_related("skill_type", "skill_type__parent")):
        category = group["category"]
        rows.append(
            {
                "category_id": category.pk,
                "technology_ids": [
                    item.skill_type_id
                    for item in group["items"]
                    if item.skill_type_id
                ],
                "errors": [],
            }
        )
    return rows


def parse_skill_editor_rows(post_data, catalog):
    try:
        total_rows = int(post_data.get("skill_groups-TOTAL_FORMS", "0"))
    except (TypeError, ValueError):
        total_rows = 0

    catalog_map = {str(item["id"]): item for item in catalog}
    parsed_rows = []
    errors = []

    for index in range(total_rows):
        category_id = (post_data.get(f"skill_groups-{index}-category") or "").strip()
        technology_ids = [value.strip() for value in post_data.getlist(f"skill_groups-{index}-technologies") if value.strip()]

        if not category_id and not technology_ids:
            continue

        row_errors = []
        catalog_entry = catalog_map.get(category_id)
        if not category_id:
            row_errors.append(gettext("Choose a category."))
        elif catalog_entry is None:
            row_errors.append(gettext("Selected category is no longer available."))

        valid_technology_ids = set()
        if catalog_entry is not None:
            valid_technology_ids = {str(item["id"]) for item in catalog_entry["technologies"]}

        if not technology_ids:
            row_errors.append(gettext("Select at least one technology in this category."))
        elif not set(technology_ids).issubset(valid_technology_ids):
            row_errors.append(gettext("One or more selected technologies do not belong to the chosen category."))

        parsed_rows.append(
            {
                "category_id": int(category_id) if category_id.isdigit() else category_id,
                "technology_ids": [int(value) for value in technology_ids if value.isdigit()],
                "errors": row_errors,
            }
        )
        errors.extend(row_errors)

    selected_categories = [str(row["category_id"]) for row in parsed_rows if row["category_id"]]
    if len(selected_categories) != len(set(selected_categories)):
        duplicate_error = gettext("Each category can only be selected once.")
        errors.append(duplicate_error)
        seen = set()
        for row in parsed_rows:
            category_key = str(row["category_id"])
            if not category_key:
                continue
            if category_key in seen:
                row["errors"].append(duplicate_error)
            seen.add(category_key)

    return parsed_rows, errors


def sync_profile_skills_from_rows(profile, rows):
    ProfileSkill.objects.filter(profile=profile).delete()

    order = 0
    for row in rows:
        for technology_id in row["technology_ids"]:
            ProfileSkill.objects.create(
                profile=profile,
                skill_type_id=technology_id,
                order=order,
            )
            order += 1


def parse_competency_selection(post_data, catalog):
    selected_ids = [value.strip() for value in post_data.getlist("competency_choices") if value.strip()]
    valid_ids = {str(item["id"]) for item in catalog}
    errors = []

    unique_ids = []
    seen = set()
    for value in selected_ids:
        if value in seen:
            continue
        seen.add(value)
        unique_ids.append(value)

    if len(unique_ids) > 5:
        errors.append(gettext("You can select up to five transversal competencies."))

    if not set(unique_ids).issubset(valid_ids):
        errors.append(gettext("One or more selected transversal competencies are no longer available."))

    return [int(value) for value in unique_ids if value.isdigit()], errors


def sync_profile_competencies(profile, competency_ids):
    ProfileCompetency.objects.filter(profile=profile).delete()

    for order, competency_id in enumerate(competency_ids):
        ProfileCompetency.objects.create(
            profile=profile,
            competency_type_id=competency_id,
            order=order,
        )


def _user_can_list_public_profile(user):
    return user.has_perm("accounts.list_public_profile")


def _apply_profile_permission_rules(profile, user):
    """
    Enforces backend profile rules.

    Important:
    The template can hide fields, but backend must also protect the data.
    This prevents a normal user from manipulating hidden fields manually.
    """

    if not _user_can_edit_professional_profile(user):
        profile.professional_title = ""
        profile.headline = ""
        profile.institution = ""
        profile.country = ""
        profile.city = ""
        profile.orcid = ""
        profile.areas_of_interest = ""
        profile.is_researcher = False
        profile.is_contributor = False

    if not _user_can_list_public_profile(user):
        profile.is_listed_publicly = False


def _translated_value(instance, field_name, language_code):
    translation = instance.translations.filter(language_code=language_code).first()
    if translation is not None:
        return getattr(translation, field_name, None)
    return None


def _has_text(value):
    return bool(str(value).strip()) if value is not None else False


def _build_city_country_display(profile):
    city = (profile.city or "").strip()
    country = (profile.country or "").strip()

    if city and country:
        return f"{city}, {country}"
    return city or country or ""


def _is_ajax_request(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _profile_has_cv_in_language(profile, language_code):
    if any(_has_text(_translated_value(profile, field_name, language_code)) for field_name in PROFILE_TRANSLATABLE_FIELDS):
        return True

    for related_name, field_names in PROFILE_ITEM_TRANSLATABLE_FIELDS.items():
        for item in getattr(profile, related_name).all():
            if any(_has_text(_translated_value(item, field_name, language_code)) for field_name in field_names):
                return True

    return False


def _get_profile_available_translation_urls(profile):
    available = []

    for language_code, language_label in settings.LANGUAGES:
        if not _profile_has_cv_in_language(profile, language_code):
            continue

        with override(language_code):
            available.append({
                "code": language_code,
                "label": language_label,
                "url": reverse("accounts:public_profile", kwargs={"username": profile.user.username}),
            })

    return available


def _build_public_profile_context(request, username):
    user_obj = get_object_or_404(User, username=username)

    if not hasattr(user_obj, "profile") or user_obj.profile is None:
        logger.warning(
            "User '%s' does not have an associated profile. Creating one.",
            username,
        )
        profile = Profile.objects.create(user=user_obj)
    else:
        profile = user_obj.profile

    profile = (
        Profile.objects
        .filter(pk=profile.pk)
        .prefetch_related(
            "translations",
            Prefetch(
                "education_items",
                queryset=ProfileEducation.objects.select_related("education_type").prefetch_related("translations").order_by(
                    "-end_date", "-end_year", "-start_date", "-start_year", "-id"
                ),
            ),
            Prefetch(
                "experience_items",
                queryset=ProfileExperience.objects.select_related("experience_type").prefetch_related("translations").order_by(
                    "-end_date", "-start_date", "-id"
                ),
            ),
            Prefetch(
                "certification_items",
                queryset=ProfileCertification.objects.select_related("certification_type").prefetch_related("translations").order_by(
                    "-issue_date", "-id", "order"
                ),
            ),
            Prefetch(
                "language_items",
                queryset=ProfileLanguage.objects.select_related("level").prefetch_related("translations").order_by(
                    "order", "id"
                ),
            ),
            Prefetch(
                "skill_items",
                queryset=ProfileSkill.objects.select_related("skill_type", "level").prefetch_related("translations").order_by(
                    "skill_type__parent__order",
                    "skill_type__parent__slug",
                    "skill_type__order",
                    "skill_type__slug",
                    "id",
                ),
            ),
            Prefetch(
                "competency_items",
                queryset=ProfileCompetency.objects.select_related("competency_type", "level").prefetch_related("translations").order_by(
                    "order", "competency_type__slug"
                ),
            ),
            Prefetch(
                "link_items",
                queryset=ProfileLink.objects.select_related("link_type").prefetch_related("translations").order_by(
                    "order", "id"
                ),
            ),
            Prefetch(
                "external_publication_items",
                queryset=ProfileExternalPublication.objects.select_related("publication_type").prefetch_related("translations").order_by(
                    "-publication_date", "-id", "order"
                ),
            ),
        )
        .get()
    )

    user_posts = Post.objects.filter(
        author=user_obj,
        status="published",
    ).order_by("-published_date")

    user_comments = Comment.objects.filter(
        user=user_obj,
        is_approved=True,
    ).order_by("-created_at")

    internal_publications = (
        Publication.objects
        .filter(
            authors=user_obj,
            is_published=True,
        )
        .prefetch_related(
            "authors",
            "categories",
            "translations",
        )
        .distinct()
        .order_by("-publication_date")
    )

    items_per_page = get_site_config_int(
        "user_profile_items_per_page",
        5,
        logger=logger,
        warning_message="SiteConfiguration not found. Using default user profile items per page (5).",
    )

    paginated_user_posts = paginate_queryset(
        user_posts,
        request.GET.get("posts_page", 1),
        items_per_page,
    )
    paginated_user_comments = paginate_queryset(
        user_comments,
        request.GET.get("comments_page", 1),
        items_per_page,
    )

    education_items = list(profile.education_items.all())
    experience_items = list(profile.experience_items.all())
    certification_items = list(profile.certification_items.all())
    language_items = list(profile.language_items.all())
    skill_items = list(profile.skill_items.all())
    technical_skill_groups = build_technical_skill_groups(skill_items)
    competency_items = list(profile.competency_items.all())
    link_items = list(profile.link_items.all())
    external_publication_items = list(profile.external_publication_items.all())
    total_experience_years = _calculate_total_years(experience_items)
    total_education_years = _calculate_total_years(education_items)
    total_certification_hours = sum(item.credit_hours or 0 for item in certification_items)
    full_name = (user_obj.get_full_name() or "").strip() or profile.get_display_name()
    public_display_name = (profile.get_display_name() or "").strip()
    profile_identity_label = public_display_name or user_obj.username
    city_country_display = _build_city_country_display(profile)
    raw_location = (profile.location or "").strip()
    show_location_line = bool(raw_location) and raw_location != city_country_display
    total_publications_count = internal_publications.count() + len(external_publication_items)

    has_cv_items = any([
        education_items,
        experience_items,
        certification_items,
        language_items,
        skill_items,
        technical_skill_groups,
        competency_items,
        link_items,
        external_publication_items,
    ])

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": reverse("accounts:user_directory"), "label": gettext("Users")},
        {"url": "", "label": user_obj.get_full_name() or user_obj.username},
    ]

    return {
        "user_obj": user_obj,
        "profile": profile,
        "can_follow_profile": request.user.is_authenticated and request.user != user_obj,
        "is_following_profile": profile.is_followed_by(request.user),
        "internal_publications": internal_publications,
        "full_name": full_name,
        "profile_identity_label": profile_identity_label,
        "city_country_display": city_country_display,
        "show_location_line": show_location_line,
        "total_publications_count": total_publications_count,
        "education_items": education_items,
        "experience_items": experience_items,
        "certification_items": certification_items,
        "language_items": language_items,
        "skill_items": skill_items,
        "technical_skill_groups": technical_skill_groups,
        "competency_items": competency_items,
        "link_items": link_items,
        "external_publication_items": external_publication_items,
        "total_experience_years": total_experience_years,
        "total_education_years": total_education_years,
        "total_certification_hours": total_certification_hours,
        "has_cv_items": has_cv_items,
        "user_posts": paginated_user_posts,
        "user_comments": paginated_user_comments,
        "breadcrumbs": breadcrumbs,
    }


@login_required
def toggle_follow_view(request, username):
    if request.method != "POST":
        raise Http404(gettext("Profile not found."))

    target_user = get_object_or_404(User, username=username)
    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or reverse("accounts:public_profile", kwargs={"username": username})
    )

    if target_user == request.user:
        error_message = gettext("You cannot follow your own account.")
        if _is_ajax_request(request):
            return JsonResponse({"ok": False, "error": error_message}, status=400)
        messages.error(request, error_message)
        return HttpResponseRedirect(next_url)

    relation = UserFollow.objects.filter(follower=request.user, followed=target_user).first()
    if relation:
        relation.delete()
        is_following = False
        message = gettext("You stopped following %(user)s.") % {"user": target_user.username}
    else:
        UserFollow.objects.create(follower=request.user, followed=target_user)
        create_new_follower_notification(follower=request.user, followed=target_user)
        is_following = True
        message = gettext("You are now following %(user)s.") % {"user": target_user.username}

    follower_count = target_user.follower_links.count()

    if _is_ajax_request(request):
        return JsonResponse(
            {
                "ok": True,
                "is_following": is_following,
                "message": message,
                "follower_count": follower_count,
            }
        )

    messages.success(request, message)
    return HttpResponseRedirect(next_url)


@login_required
def inbox_view(request):
    notifications = request.user.notifications.select_related(
        "actor",
        "related_post",
    ).order_by("-created_at")

    paginator = Paginator(notifications, 20)
    page_number = request.GET.get("page", 1)
    inbox_page = paginator.get_page(page_number)

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": "", "label": gettext("Inbox")},
    ]

    context = {
        "notifications_page": inbox_page,
        "breadcrumbs": breadcrumbs,
    }
    return render(request, "accounts/inbox.html", context)


@login_required
def mark_notification_read_view(request, notification_id):
    if request.method != "POST":
        raise Http404(gettext("Notification not found."))

    notification = get_object_or_404(
        UserNotification,
        pk=notification_id,
        recipient=request.user,
    )
    notification.mark_as_read()

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or reverse("accounts:inbox")
    )
    messages.success(request, gettext("Notification marked as read."))
    return HttpResponseRedirect(next_url)


@login_required
def mark_all_notifications_read_view(request):
    if request.method != "POST":
        raise Http404(gettext("Inbox not found."))

    unread_qs = request.user.notifications.filter(is_read=False)
    unread_qs.update(is_read=True, read_at=timezone.now())

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or reverse("accounts:inbox")
    )
    messages.success(request, gettext("All notifications were marked as read."))
    return HttpResponseRedirect(next_url)


# --- SIGNUP VIEW ---
def signup_view(request):
    """Handles new user registration."""
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            logger.info("New user account created: '%s' (ID: %s)", user.username, user.id)

            login(request, user)
            messages.success(request, gettext("Welcome! Your account has been created successfully."))
            return redirect("home")

        logger.warning("Signup form failed validation. Errors: %s", form.errors.as_json())

    else:
        form = CustomUserCreationForm()

    return render(request, "registration/signup.html", {"form": form})


@login_required
def profile_edit_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    can_edit_professional_profile = _user_can_edit_professional_profile(request.user)
    can_edit_cv = _user_can_edit_own_cv(request.user)
    can_list_public_profile = _user_can_list_public_profile(request.user)

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()

            profile = profile_form.save(commit=False)

            uploaded_avatar = request.FILES.get("avatar")
            use_default_avatar = bool(profile_form.cleaned_data.get("use_default_avatar"))
            chosen_default = (
                profile_form.cleaned_data.get("default_avatar_choice")
                or profile.AvatarChoice.PRIVATE
            )

            profile.default_avatar_choice = chosen_default

            # Default static avatar mode always has priority.
            if use_default_avatar:
                _remove_previous_avatar_file_if_custom(profile)
                profile.use_default_avatar = True
                profile.avatar = chosen_default

                logger.info(
                    "User '%s' switched to default avatar '%s'.",
                    request.user.username,
                    chosen_default,
                )

            elif uploaded_avatar:
                extension = os.path.splitext(uploaded_avatar.name)[1]
                new_filename = f"{uuid.uuid4().hex}{extension}"

                _remove_previous_avatar_file_if_custom(profile)
                profile.avatar.save(new_filename, uploaded_avatar, save=False)
                profile.use_default_avatar = False

                logger.info(
                    "User '%s' uploaded new avatar, saved as %s",
                    request.user.username,
                    new_filename,
                )

            else:
                # No new upload and default mode disabled: keep existing value.
                # If current value is empty/default-like, force default mode to avoid invalid state.
                default_paths = [choice[0] for choice in profile.AvatarChoice.choices]
                avatar_name = (profile.avatar.name or "").strip() if profile.avatar else ""

                if not avatar_name or avatar_name in default_paths:
                    profile.use_default_avatar = True
                    profile.avatar = chosen_default

            # Enforce professional/public profile permissions before saving.
            _apply_profile_permission_rules(profile, request.user)

            profile.save()

            messages.success(request, gettext("Your profile has been updated successfully!"))
            return redirect("accounts:profile_edit")

        logger.warning(
            "Profile update form failed validation.",
            extra={"errors": profile_form.errors.as_json()},
        )

    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": reverse("accounts:profile_edit"), "label": gettext("Edit Profile")},
    ]

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "breadcrumbs": breadcrumbs,
        "can_edit_professional_profile": can_edit_professional_profile,
        "can_edit_cv": can_edit_cv,
        "can_list_public_profile": can_list_public_profile,
    }

    return render(request, "registration/profile_edit.html", context)


@login_required
def profile_cv_edit_view(request):
    """
    Allows the logged-in user to edit their own CV/resume sections.

    The admin manages parametrization catalogs.
    The user owns and edits their own CV data here.
    """

    if not _user_can_edit_own_cv(request.user):
        raise PermissionDenied(gettext("You do not have permission to edit a CV."))

    profile, _ = Profile.objects.get_or_create(user=request.user)

    formset_definitions = _get_profile_cv_formset_definitions()
    formsets = {}
    skill_category_catalog = get_skill_category_catalog()
    skill_editor_rows = build_skill_editor_rows(profile)
    skill_editor_errors = []
    competency_catalog = get_competency_catalog()
    selected_competency_ids = list(
        profile.competency_items.exclude(competency_type__isnull=True)
        .values_list("competency_type_id", flat=True)
    )
    competency_selection_errors = []

    if request.method == "POST":
        all_valid = True

        for context_key, _title, formset_class, prefix in formset_definitions:
            formset_kwargs = {
                "instance": profile,
                "prefix": prefix,
            }
            if prefix == "experience":
                formset_kwargs["queryset"] = ProfileExperience.objects.filter(profile=profile).order_by(
                    "-end_date", "-start_date", "-id"
                )
            formset = formset_class(
                request.POST,
                **formset_kwargs,
            )
            formsets[context_key] = formset

            if not formset.is_valid():
                all_valid = False
                logger.warning(
                    "Profile CV formset '%s' failed validation for user '%s'. Errors: %s",
                    prefix,
                    request.user.username,
                    formset.errors,
                )

        skill_editor_rows, skill_editor_errors = parse_skill_editor_rows(
            request.POST,
            skill_category_catalog,
        )
        if skill_editor_errors:
            all_valid = False

        selected_competency_ids, competency_selection_errors = parse_competency_selection(
            request.POST,
            competency_catalog,
        )
        if competency_selection_errors:
            all_valid = False

        if all_valid:
            for formset in formsets.values():
                formset.save()
            sync_profile_skills_from_rows(profile, skill_editor_rows)
            sync_profile_competencies(profile, selected_competency_ids)

            messages.success(request, gettext("Your CV has been updated successfully."))
            return redirect("accounts:profile_cv_edit")

        messages.error(request, gettext("Please review the highlighted errors before saving."))

    else:
        for context_key, _title, formset_class, prefix in formset_definitions:
            formset_kwargs = {
                "instance": profile,
                "prefix": prefix,
            }
            if prefix == "experience":
                formset_kwargs["queryset"] = ProfileExperience.objects.filter(profile=profile).order_by(
                    "-end_date", "-start_date", "-id"
                )
            formsets[context_key] = formset_class(**formset_kwargs)

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": reverse("accounts:profile_edit"), "label": gettext("Edit Profile")},
        {"url": "", "label": gettext("Edit CV")},
    ]

    context = {
        "profile": profile,
        "cv_sections": [
            {
                "key": context_key,
                "title": title,
                "formset": formsets[context_key],
                "prefix": prefix,
            }
            for context_key, title, _formset_class, prefix in formset_definitions
        ],
        "breadcrumbs": breadcrumbs,
        "skill_category_catalog": skill_category_catalog,
        "skill_editor_rows": skill_editor_rows or [{"category_id": "", "technology_ids": [], "errors": []}],
        "skill_editor_errors": skill_editor_errors,
        "competency_catalog": competency_catalog,
        "selected_competency_ids": selected_competency_ids,
        "competency_selection_errors": competency_selection_errors,
    }

    # Expose each formset directly for the detailed CV editor template.
    context.update(formsets)

    return render(request, "registration/profile_cv_edit.html", context)


def user_profile_public_view(request, username):
    """
    Displays public information for a given user, including profile details,
    CV/resume sections, and paginated public contributions.
    """
    try:
        context = _build_public_profile_context(request, username)
        requested_language = get_language()

        if not _profile_has_cv_in_language(context["profile"], requested_language):
            return render(
                request,
                "core/translation_unavailable.html",
                {
                    "content_kind": "profile",
                    "object": context["profile"],
                    "available_translations": _get_profile_available_translation_urls(context["profile"]),
                    "title": gettext("CV not available in this language"),
                    "meta_title": gettext("CV not available in this language"),
                    "meta_description": gettext(
                        "This profile exists, but its CV has not been entered in the selected language yet."
                    ),
                },
                status=404,
            )

        logger.info("Public profile view accessed for user: '%s'.", username)
        return render(request, "accounts/public_profile_view.html", context)

    except User.DoesNotExist:
        logger.warning("Public profile requested for non-existent user: '%s'.", username)
        raise

    except Exception as e:
        logger.error(
            "Error accessing public profile for user '%s': %s",
            username,
            e,
            exc_info=True,
        )
        raise


def user_profile_public_print_view(request, username):
    """
    Render-only print-friendly version of the public CV.
    """
    context = _build_public_profile_context(request, username)
    if not _profile_has_cv_in_language(context["profile"], get_language()):
        raise Http404(gettext("CV not available in this language."))
    context["site_template"] = SiteTemplate.get_chosen()
    return render(request, "accounts/public_profile_print.html", context)


def user_profile_public_pdf_view(request, username):
    """
    Generate a PDF using ReportLab.
    """
    context = _build_public_profile_context(request, username)
    if not _profile_has_cv_in_language(context["profile"], get_language()):
        raise Http404(gettext("CV not available in this language."))

    output_name = f"{slugify(username)}-cv.pdf"

    try:
        pdf_bytes = build_public_profile_pdf_bytes(context)
    except Exception:
        logger.exception("ReportLab PDF generation failed for user '%s'.", username)
        raise Http404(gettext("The PDF could not be generated at this time."))

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{output_name}"'
    return response


def user_directory_view(request):
    """
    Displays a paginated list of active users who chose and are allowed
    to be listed publicly.
    """
    all_users = User.objects.filter(
        is_active=True,
        profile__is_listed_publicly=True,
    ).select_related("profile").prefetch_related("profile__translations").distinct().order_by("username")

    items_per_page = get_site_config_int(
        "user_directory_items_per_page",
        25,
        logger=logger,
        warning_message="SiteConfiguration not found. Using default user directory items per page (25).",
    )
    users_on_page = paginate_queryset(
        all_users,
        request.GET.get("page"),
        items_per_page,
    )

    logger.info(
        "User directory view accessed. Showing page %s of %s users.",
        getattr(users_on_page, "number", 0),
        getattr(users_on_page, "paginator.num_pages", 0),
    )

    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": "", "label": gettext("Users")},
    ]

    context = {
        "users": users_on_page,
        "breadcrumbs": breadcrumbs,
    }

    return render(request, "accounts/user_directory.html", context)
