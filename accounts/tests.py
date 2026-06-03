from datetime import date
from types import SimpleNamespace

from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.templatetags.static import static
from django.test import TestCase

from comments.models import Comment
from .models import (
    ProfileCertification,
    ProfileCertificationType,
    ProfileCompetency,
    ProfileCompetencyLevel,
    ProfileCompetencyType,
    ProfileEducation,
    ProfileEducationType,
    ProfileExperience,
    ProfileExperienceType,
    ProfileExternalPublication,
    ProfileExternalPublicationType,
    ProfileLanguage,
    ProfileLanguageLevel,
    ProfileLink,
    ProfileLinkType,
    ProfileSkill,
    ProfileSkillLevel,
    ProfileSkillType,
    UserFollow,
    UserNotification,
    get_user_avatar_url,
)
from posts.models import Post


class ProfileCvModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cvuser", password="testpass123")
        self.profile = self.user.profile

        self.language_level = ProfileLanguageLevel.objects.create(name="C1", slug="c1")
        self.skill_level = ProfileSkillLevel.objects.create(name="Advanced", slug="advanced")
        self.skill_type = ProfileSkillType.objects.create(name="Programming", slug="programming")
        self.competency_level = ProfileCompetencyLevel.objects.create(name="Expert", slug="expert")
        self.competency_type = ProfileCompetencyType.objects.create(name="Critical thinking", slug="critical-thinking")
        self.link_type = ProfileLinkType.objects.create(name="LinkedIn", slug="linkedin")
        self.external_publication_type = ProfileExternalPublicationType.objects.create(
            name="Article",
            slug="article",
        )
        self.experience_type = ProfileExperienceType.objects.create(name="Research", slug="research")
        self.education_type = ProfileEducationType.objects.create(name="Master", slug="master")
        self.certification_type = ProfileCertificationType.objects.create(
            name="Certificate",
            slug="certificate",
        )

    def test_can_create_all_catalog_models(self):
        self.assertEqual(ProfileLanguageLevel.objects.count(), 1)
        self.assertEqual(ProfileSkillLevel.objects.count(), 1)
        self.assertEqual(ProfileCompetencyLevel.objects.count(), 1)
        self.assertEqual(ProfileLinkType.objects.count(), 1)
        self.assertEqual(ProfileExternalPublicationType.objects.count(), 1)
        self.assertEqual(ProfileExperienceType.objects.count(), 1)
        self.assertEqual(ProfileEducationType.objects.count(), 1)
        self.assertEqual(ProfileCertificationType.objects.count(), 1)

    def test_can_create_all_cv_models_and_related_names(self):
        education = ProfileEducation.objects.create(
            profile=self.profile,
            education_type=self.education_type,
            institution="Example University",
            degree="MSc",
            start_year=2020,
        )
        experience = ProfileExperience.objects.create(
            profile=self.profile,
            experience_type=self.experience_type,
            organization="Research Lab",
            position="Research Assistant",
            start_date=date(2022, 1, 1),
        )
        certification = ProfileCertification.objects.create(
            profile=self.profile,
            certification_type=self.certification_type,
            name="Data Science Certificate",
            issuer="Example Institute",
            issue_date=date(2024, 1, 1),
        )
        language = ProfileLanguage.objects.create(
            profile=self.profile,
            language="English",
            level=self.language_level,
        )
        skill = ProfileSkill.objects.create(
            profile=self.profile,
            skill_type=self.skill_type,
            level=self.skill_level,
            description="Python",
        )
        competency = ProfileCompetency.objects.create(
            profile=self.profile,
            competency_type=self.competency_type,
            level=self.competency_level,
            description="Critical thinking",
        )
        link = ProfileLink.objects.create(
            profile=self.profile,
            label="LinkedIn",
            url="https://example.com/linkedin",
            link_type=self.link_type,
        )
        external_publication = ProfileExternalPublication.objects.create(
            profile=self.profile,
            title="Sample Article",
            publication_type=self.external_publication_type,
            year=2025,
        )

        self.assertEqual(self.profile.education_items.count(), 1)
        self.assertEqual(self.profile.experience_items.count(), 1)
        self.assertEqual(self.profile.certification_items.count(), 1)
        self.assertEqual(self.profile.language_items.count(), 1)
        self.assertEqual(self.profile.skill_items.count(), 1)
        self.assertEqual(self.profile.competency_items.count(), 1)
        self.assertEqual(self.profile.link_items.count(), 1)
        self.assertEqual(self.profile.external_publication_items.count(), 1)

        self.assertIn(education, self.profile.education_items.all())
        self.assertIn(experience, self.profile.experience_items.all())
        self.assertIn(certification, self.profile.certification_items.all())
        self.assertIn(language, self.profile.language_items.all())
        self.assertIn(skill, self.profile.skill_items.all())
        self.assertIn(competency, self.profile.competency_items.all())
        self.assertIn(link, self.profile.link_items.all())
        self.assertIn(external_publication, self.profile.external_publication_items.all())

        for obj in (
            self.language_level,
            self.skill_level,
            self.competency_level,
            self.link_type,
            self.external_publication_type,
            self.experience_type,
            self.education_type,
            self.certification_type,
            education,
            experience,
            certification,
            language,
            skill,
            competency,
            link,
            external_publication,
        ):
            self.assertTrue(str(obj).strip())


class UserFollowTests(TestCase):
    def setUp(self):
        self.follower = User.objects.create_user(username="follower", password="testpass123")
        self.followed = User.objects.create_user(username="followed", password="testpass123")

    def test_profile_follow_counts_reflect_relation(self):
        UserFollow.objects.create(follower=self.follower, followed=self.followed)

        self.assertEqual(self.followed.profile.followers_count, 1)
        self.assertEqual(self.follower.profile.following_count, 1)
        self.assertTrue(self.followed.profile.is_followed_by(self.follower))

    def test_toggle_follow_view_creates_relation(self):
        self.client.force_login(self.follower)

        response = self.client.post(
            reverse("accounts:toggle_follow", kwargs={"username": self.followed.username}),
            {"next": reverse("accounts:public_profile", kwargs={"username": self.followed.username})},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            UserFollow.objects.filter(follower=self.follower, followed=self.followed).exists()
        )

    def test_toggle_follow_view_removes_existing_relation(self):
        UserFollow.objects.create(follower=self.follower, followed=self.followed)
        self.client.force_login(self.follower)

        response = self.client.post(
            reverse("accounts:toggle_follow", kwargs={"username": self.followed.username}),
            {"next": reverse("accounts:public_profile", kwargs={"username": self.followed.username})},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            UserFollow.objects.filter(follower=self.follower, followed=self.followed).exists()
        )

    def test_user_cannot_follow_self(self):
        self.client.force_login(self.follower)

        response = self.client.post(
            reverse("accounts:toggle_follow", kwargs={"username": self.follower.username}),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "You cannot follow your own account.")


class UserNotificationTests(TestCase):
    def setUp(self):
        self.follower = User.objects.create_user(username="notif-follower", password="testpass123")
        self.author = User.objects.create_user(username="notif-author", password="testpass123")
        UserFollow.objects.create(follower=self.follower, followed=self.author)

    def _create_published_post(self, slug="notif-post", title="Notification post"):
        post = Post.objects.create(author=self.author, status="published")
        post.set_current_language("en")
        post.title = title
        post.slug = slug
        post.content = "Body"
        post.save()
        return post


    def test_followed_author_publication_creates_notification(self):
        post = self._create_published_post()

        notification = UserNotification.objects.get(
            recipient=self.follower,
            notification_type=UserNotification.NotificationType.FOLLOWED_AUTHOR_PUBLISHED_POST,
        )
        self.assertEqual(notification.related_post, post)
        self.assertFalse(notification.is_read)
        self.assertIn("Notification post", notification.message)

    def test_followed_author_notification_is_not_duplicated_on_edit(self):
        post = self._create_published_post()
        post.set_current_language("en")
        post.content = "Updated body"
        post.save()

        self.assertEqual(
            UserNotification.objects.filter(
                recipient=self.follower,
                notification_type=UserNotification.NotificationType.FOLLOWED_AUTHOR_PUBLISHED_POST,
                related_post=post,
            ).count(),
            1,
        )

    def test_mark_notification_as_read_view_updates_status(self):
        notification = UserNotification.objects.create(
            recipient=self.follower,
            actor=self.author,
            notification_type=UserNotification.NotificationType.FOLLOWED_AUTHOR_PUBLISHED_POST,
            title="New post from notif-author",
            message='notif-author published the post "Notification post".',
            url="/posts/example/",
        )
        self.client.force_login(self.follower)

        response = self.client.post(
            reverse("accounts:mark_notification_read", kwargs={"notification_id": notification.id}),
            {"next": reverse("accounts:inbox")},
        )

        self.assertEqual(response.status_code, 302)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_inbox_view_lists_notifications(self):
        UserNotification.objects.create(
            recipient=self.follower,
            actor=self.author,
            notification_type=UserNotification.NotificationType.FOLLOWED_AUTHOR_PUBLISHED_POST,
            title="New post from notif-author",
            message='notif-author published the post "Notification post".',
            url="/posts/example/",
        )
        self.client.force_login(self.follower)

        response = self.client.get(reverse("accounts:inbox"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New post from notif-author")

    def test_approved_comment_on_authors_post_creates_notification(self):
        post = self._create_published_post(slug="commented-post", title="Commented Post")
        commenter = User.objects.create_user(username="notif-commenter", password="testpass123")

        comment = Comment.objects.create(
            post=post,
            user=commenter,
            author_name="notif-commenter",
            author_email="commenter@example.com",
            content="Interesting read",
            language="en",
            is_approved=True,
        )

        notification = UserNotification.objects.get(
            recipient=self.author,
            notification_type=UserNotification.NotificationType.COMMENT_ON_YOUR_POST,
        )
        self.assertEqual(notification.related_post, post)
        self.assertIn("Commented Post", notification.message)
        self.assertEqual(notification.payload["comment_id"], comment.id)

    def test_comment_notification_is_created_when_comment_is_approved_later(self):
        post = self._create_published_post(slug="moderated-post", title="Moderated Post")
        commenter = User.objects.create_user(username="notif-moderated", password="testpass123")
        comment = Comment.objects.create(
            post=post,
            user=commenter,
            author_name="notif-moderated",
            author_email="moderated@example.com",
            content="Pending moderation",
            language="en",
            is_approved=False,
        )

        self.assertFalse(
            UserNotification.objects.filter(
                recipient=self.author,
                notification_type=UserNotification.NotificationType.COMMENT_ON_YOUR_POST,
            ).exists()
        )

        comment.is_approved = True
        comment.save()

        self.assertTrue(
            UserNotification.objects.filter(
                recipient=self.author,
                notification_type=UserNotification.NotificationType.COMMENT_ON_YOUR_POST,
                dedupe_key=f"comment-on-post:{comment.id}:{self.author.id}",
            ).exists()
        )


class UserAvatarUrlTests(TestCase):
    def test_get_user_avatar_url_returns_static_fallback_when_profile_attribute_is_missing(self):
        user_like = SimpleNamespace()

        self.assertEqual(
            get_user_avatar_url(user_like),
            static("images/avatars/default_private.png"),
        )


class ProfileCvPresentationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cv-present", password="testpass123")
        self.user.user_permissions.add(
            Permission.objects.get(codename="edit_own_cv"),
        )
        self.profile = self.user.profile
        self.profile.set_current_language("en")
        self.profile.display_name = "CV Present"
        self.profile.professional_title = "Researcher"
        self.profile.bio = "Works on editorial and methodological research."
        self.profile.save()

        self.skill_level = ProfileSkillLevel.objects.create(name="Advanced", slug="advanced-present")
        self.skill_type = ProfileSkillType.objects.create(name="Qualitative analysis", slug="qualitative-analysis")
        self.competency_level = ProfileCompetencyLevel.objects.create(name="Strong", slug="strong-present")
        self.competency_type = ProfileCompetencyType.objects.create(name="Critical reading", slug="critical-reading")
        self.link_type = ProfileLinkType.objects.create(name="ORCID", slug="orcid-present")
        self.external_publication_type = ProfileExternalPublicationType.objects.create(
            name="Essay",
            slug="essay-present",
        )

        ProfileSkill.objects.create(
            profile=self.profile,
            skill_type=self.skill_type,
            level=self.skill_level,
            description="Coding, annotation, and source analysis.",
        )
        ProfileCompetency.objects.create(
            profile=self.profile,
            competency_type=self.competency_type,
            level=self.competency_level,
            description="Interdisciplinary synthesis and collaborative writing.",
        )
        ProfileLink.objects.create(
            profile=self.profile,
            label="Research profile",
            url="https://example.com/research-profile",
            link_type=self.link_type,
        )
        ProfileExternalPublication.objects.create(
            profile=self.profile,
            title="Editorial Methods Notebook",
            publication_type=self.external_publication_type,
            year=2026,
        )

    def test_public_profile_highlights_research_profile_sections(self):
        response = self.client.get(
            reverse("accounts:public_profile", kwargs={"username": self.user.username})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Research and Professional Profile")
        self.assertContains(response, "Technical and Methodological Knowledge")
        self.assertContains(response, "Transversal Competencies")
        self.assertContains(response, "Public References")

    def test_cv_editor_uses_academic_research_wording(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("accounts:profile_cv_edit"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Structure your public academic and professional CV with education, experience, methods, links, and publications.",
        )
        self.assertContains(response, "Technical and Methodological Knowledge")
        self.assertContains(response, "Academic and Professional Links")

    def test_get_user_avatar_url_returns_static_fallback_when_profile_avatar_resolution_fails(self):
        class BrokenProfile:
            def get_avatar_url(self):
                raise ValueError("broken avatar")

        user_like = SimpleNamespace(profile=BrokenProfile())

        self.assertEqual(
            get_user_avatar_url(user_like),
            static("images/avatars/default_private.png"),
        )
