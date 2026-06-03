from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import PostFavorite, PostPointAllocation


@dataclass
class PostPointsSummary:
    budget: int
    remaining: int
    assigned_today: int
    current_post_points: int


@dataclass
class PostPointsAccess:
    allowed: bool
    reason: str = ""


def get_post_points_budget(config):
    return max(getattr(config, "daily_post_points_budget", 10), 0)


def get_max_points_per_post(config):
    budget = get_post_points_budget(config)
    configured = max(getattr(config, "max_points_per_post_per_day", budget), 0)
    return min(configured, budget) if budget else 0


def can_user_assign_post_points(user, post, config, date=None):
    if not getattr(config, "post_points_enabled", True):
        return PostPointsAccess(False, _("Post points are disabled right now."))

    if not getattr(user, "is_authenticated", False):
        return PostPointsAccess(False, _("You need to log in to assign points to posts."))

    allow_self_points = getattr(config, "allow_author_self_points", False)
    if post.author_id == user.id and not allow_self_points:
        return PostPointsAccess(False, _("You cannot assign points to your own post."))

    if post.status != "published":
        return PostPointsAccess(False, _("Only published posts can receive points."))

    min_account_age_days = max(getattr(config, "post_points_min_account_age_days", 0), 0)
    if min_account_age_days:
        now = timezone.now()
        age_delta = now - user.date_joined
        if age_delta.days < min_account_age_days:
            return PostPointsAccess(
                False,
                _("You can start assigning points after %(days)s day(s) on the site.")
                % {"days": min_account_age_days},
            )

    return PostPointsAccess(True, "")


def get_post_points_summary(user, post, config, date=None):
    date = date or timezone.localdate()
    budget = get_post_points_budget(config)

    if not getattr(user, "is_authenticated", False):
        return PostPointsSummary(
            budget=budget,
            remaining=budget,
            assigned_today=0,
            current_post_points=0,
        )

    allocations = PostPointAllocation.objects.filter(user=user, date=date)
    assigned_today = allocations.aggregate(total=Sum("points"))["total"] or 0
    current_post_points = (
        allocations.filter(post=post).values_list("points", flat=True).first() or 0
    )
    remaining = max(budget - assigned_today, 0)

    return PostPointsSummary(
        budget=budget,
        remaining=remaining,
        assigned_today=assigned_today,
        current_post_points=current_post_points,
    )


def get_post_points_total(post, date=None):
    date = date or timezone.localdate()
    return (
        PostPointAllocation.objects.filter(post=post, date=date).aggregate(total=Sum("points"))["total"]
        or 0
    )


def get_post_favorites_total(post):
    return post.favorites.count()


def is_post_favorited_by_user(user, post):
    if not getattr(user, "is_authenticated", False):
        return False
    return PostFavorite.objects.filter(user=user, post=post).exists()


def toggle_post_favorite(user, post):
    if not getattr(user, "is_authenticated", False):
        raise ValidationError(_("You need to log in to favorite posts."))

    favorite = PostFavorite.objects.filter(user=user, post=post).first()
    if favorite:
        favorite.delete()
        return False

    PostFavorite.objects.create(user=user, post=post)
    return True


def set_post_points_for_day(user, post, points, config, date=None):
    access = can_user_assign_post_points(user, post, config, date=date)
    if not access.allowed:
        raise ValidationError(access.reason)

    date = date or timezone.localdate()
    budget = get_post_points_budget(config)
    max_per_post = get_max_points_per_post(config)

    if points < 0:
        raise ValidationError(_("Points cannot be negative."))
    if points > max_per_post:
        raise ValidationError(
            _("You can assign at most %(points)s point(s) to the same post per day.")
            % {"points": max_per_post}
        )

    allocation = PostPointAllocation.objects.filter(
        user=user,
        post=post,
        date=date,
    ).first()
    current_points = allocation.points if allocation else 0

    current_total = (
        PostPointAllocation.objects.filter(user=user, date=date).aggregate(total=Sum("points"))["total"]
        or 0
    )
    available_without_current = budget - (current_total - current_points)

    if points > available_without_current:
        raise ValidationError(
            _("You only have %(points)s point(s) left for today.")
            % {"points": max(available_without_current, 0)}
        )

    if allocation is None:
        allocation = PostPointAllocation(
            user=user,
            post=post,
            date=date,
        )
        allocation.points = points
        allocation.save()
        return allocation

    allocation.points = points
    allocation.save(update_fields=["points", "updated_at"])
    return allocation
