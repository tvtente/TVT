from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.core import mail
from django.templatetags.static import static
from django.test import TestCase, override_settings
from django.utils.translation import gettext

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
    get_user_default_avatar_url,
    get_user_avatar_url,
)
from posts.models import Post


class ProfileCvModelsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cvuser", password="testpass123")
        self.profile = self.user.profile

        self.language_level = ProfileLanguageLevel.objects.create(name="C1", slug="c1")
        self.skill_level = ProfileSkillLevel.objects.create(name="Advanced", slug="advanced")
        self.skill_category = ProfileSkillType.objects.create(name="Databases", slug="databases-test")
        self.skill_type = ProfileSkillType.objects.create(
            name="MySQL",
            slug="mysql-test",
            parent=self.skill_category,
        )
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
            start_date=date(2020, 9, 1),
            credit_hours=120,
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
            publication_date=date(2025, 1, 1),
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

        self.assertEqual(education.start_year, 2020)
        self.assertIsNone(education.end_year)
        self.assertEqual(education.credit_hours, 120)

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

    def test_current_education_records_today_as_end_date(self):
        education = ProfileEducation.objects.create(
            profile=self.profile,
            education_type=self.education_type,
            institution="Open University",
            degree="MSc",
            start_date=date(2024, 1, 1),
            is_current=True,
        )

        self.assertEqual(education.end_date, date.today())
        self.assertEqual(education.start_year, 2024)
        self.assertEqual(education.end_year, date.today().year)

    def test_current_experience_records_today_as_end_date_and_sorts_first(self):
        older = ProfileExperience.objects.create(
            profile=self.profile,
            experience_type=self.experience_type,
            organization="Older Org",
            position="Analyst",
            start_date=date(2020, 1, 1),
            end_date=date(2023, 1, 1),
        )
        current = ProfileExperience.objects.create(
            profile=self.profile,
            experience_type=self.experience_type,
            organization="Current Org",
            position="Lead",
            start_date=date(2024, 1, 1),
            is_current=True,
        )

        self.assertEqual(current.end_date, date.today())
        ordered = list(ProfileExperience.objects.filter(profile=self.profile))
        self.assertEqual(ordered[0].pk, current.pk)
        self.assertEqual(ordered[1].pk, older.pk)

    def test_profile_link_uses_link_type_name_when_label_is_empty(self):
        link = ProfileLink.objects.create(
            profile=self.profile,
            link_type=self.link_type,
            url="https://example.com/orcid",
        )

        self.assertEqual(link.get_display_label(), "LinkedIn")
        self.assertEqual(link.safe_translation_getter("label", any_language=True), "LinkedIn")

    def test_certification_without_expiration_clears_expiration_date(self):
        certification = ProfileCertification.objects.create(
            profile=self.profile,
            certification_type=self.certification_type,
            name="Platform Certificate",
            issuer="Example Institute",
            issue_date=date(2024, 1, 1),
            expiration_date=date(2025, 1, 1),
            no_expiration=True,
            credit_hours=40,
            credential_id="REF-123",
        )

        self.assertIsNone(certification.expiration_date)
        self.assertEqual(certification.credit_hours, 40)
        self.assertEqual(certification.credential_id, "REF-123")

    def test_skill_type_hierarchy_label_uses_category_and_subcategory(self):
        self.assertEqual(self.skill_type.hierarchy_label, "Databases / MySQL")

    def test_certifications_are_ordered_by_issue_date_descending(self):
        older = ProfileCertification.objects.create(
            profile=self.profile,
            certification_type=self.certification_type,
            name="Older Certificate",
            issuer="Example Institute",
            issue_date=date(2023, 1, 1),
        )
        newer = ProfileCertification.objects.create(
            profile=self.profile,
            certification_type=self.certification_type,
            name="Newer Certificate",
            issuer="Example Institute",
            issue_date=date(2025, 1, 1),
        )

        ordered = list(ProfileCertification.objects.filter(profile=self.profile))

        self.assertEqual(ordered[0].pk, newer.pk)
        self.assertEqual(ordered[1].pk, older.pk)

    def test_external_publications_are_ordered_by_publication_date_descending(self):
        older = ProfileExternalPublication.objects.create(
            profile=self.profile,
            title="Older Publication",
            publication_type=self.external_publication_type,
            publication_date=date(2023, 1, 1),
        )
        newer = ProfileExternalPublication.objects.create(
            profile=self.profile,
            title="Newer Publication",
            publication_type=self.external_publication_type,
            publication_date=date(2025, 1, 1),
        )

        ordered = list(ProfileExternalPublication.objects.filter(profile=self.profile))

        self.assertEqual(ordered[0].pk, newer.pk)
        self.assertEqual(ordered[1].pk, older.pk)


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
        self.followed.email = "followed@example.com"
        self.followed.save(update_fields=["email"])
        self.client.force_login(self.follower)

        with self.settings(
            EMAIL_NOTIFICATIONS_ENABLED=True,
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        ), self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("accounts:toggle_follow", kwargs={"username": self.followed.username}),
                {"next": reverse("accounts:public_profile", kwargs={"username": self.followed.username})},
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            UserFollow.objects.filter(follower=self.follower, followed=self.followed).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["followed@example.com"])

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
        self.assertEqual(payload["error"], gettext("You cannot follow your own account."))


class UserNotificationTests(TestCase):
    def setUp(self):
        self.follower = User.objects.create_user(username="notif-follower", password="testpass123")
        self.author = User.objects.create_user(
            username="notif-author",
            password="testpass123",
            email="author@example.com",
        )
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

    def test_deleting_post_keeps_notification_and_clears_related_post(self):
        post = self._create_published_post(slug="deletable-post", title="Deletable Post")
        notification = UserNotification.objects.get(
            recipient=self.follower,
            notification_type=UserNotification.NotificationType.FOLLOWED_AUTHOR_PUBLISHED_POST,
        )

        post.delete()

        notification.refresh_from_db()
        self.assertIsNone(notification.related_post)
        self.assertIn("Deletable Post", notification.message)

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

    def test_approved_comment_sends_email_when_enabled(self):
        post = self._create_published_post(slug="email-comment", title="Email comment")
        commenter = User.objects.create_user(username="email-commenter", password="testpass123")

        with self.settings(
            EMAIL_NOTIFICATIONS_ENABLED=True,
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        ), self.captureOnCommitCallbacks(execute=True):
            comment = Comment.objects.create(
                post=post,
                user=commenter,
                content="Interesting read",
                language="en",
                is_approved=True,
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["author@example.com"])
        self.assertIn("New comment", mail.outbox[0].subject)
        notification = UserNotification.objects.get(
            payload__comment_id=comment.id,
            recipient=self.author,
        )
        self.assertEqual(
            notification.email_delivery_status,
            UserNotification.EmailDeliveryStatus.SENT,
        )
        self.assertIsNotNone(notification.email_sent_at)

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

        self.assertTrue(
            UserNotification.objects.filter(
                recipient=self.author,
                notification_type=UserNotification.NotificationType.COMMENT_ON_YOUR_POST,
            ).exists()
        )

        comment.is_approved = True
        comment.save()

        self.assertEqual(
            UserNotification.objects.filter(
                recipient=self.author,
                notification_type=UserNotification.NotificationType.COMMENT_ON_YOUR_POST,
                dedupe_key=f"comment-on-post:{comment.id}:{self.author.id}",
            ).count(),
            1,
        )


class UserAvatarUrlTests(TestCase):
    def test_get_user_avatar_url_returns_static_fallback_when_profile_attribute_is_missing(self):
        user_like = SimpleNamespace()

        self.assertEqual(
            get_user_avatar_url(user_like),
            static("images/avatars/default_private.png"),
        )

    def test_get_user_default_avatar_url_uses_profile_choice(self):
        user = User.objects.create_user(username="female-avatar", password="testpass123")
        user.profile.default_avatar_choice = user.profile.AvatarChoice.FEMALE
        user.profile.save(update_fields=["default_avatar_choice"])

        self.assertEqual(
            get_user_default_avatar_url(user),
            static("images/avatars/default_female.png"),
        )

    @override_settings(MEDIA_URL="https://tvtente.com/media/")
    def test_profile_uses_remote_avatar_url_without_local_file(self):
        user = User.objects.create_user(username="remote-avatar", password="testpass123")
        profile = user.profile
        profile.avatar.name = "avatars/remote-avatar.png"
        profile.use_default_avatar = False

        self.assertEqual(
            profile.get_avatar_url(),
            "https://tvtente.com/media/avatars/remote-avatar.png",
        )


class ProfileCvPresentationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cv-present", password="testpass123")
        self.user.first_name = "Casey"
        self.user.last_name = "Present"
        self.user.save(update_fields=["first_name", "last_name"])
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
        self.skill_category = ProfileSkillType.objects.create(name="Databases", slug="databases-present-group")
        self.skill_type = ProfileSkillType.objects.create(
            name="PostgreSQL",
            slug="postgresql-present-group",
            parent=self.skill_category,
        )
        self.competency_level = ProfileCompetencyLevel.objects.create(name="Strong", slug="strong-present")
        self.competency_type = ProfileCompetencyType.objects.create(name="Critical reading", slug="critical-reading")
        self.link_type = ProfileLinkType.objects.create(name="ORCID", slug="orcid-present")
        self.certification_type = ProfileCertificationType.objects.create(
            name="Professional course",
            slug="professional-course-present",
        )
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
        ProfileEducation.objects.create(
            profile=self.profile,
            institution="Open University",
            degree="MA",
            start_date=date(2018, 1, 1),
            end_date=date(2020, 12, 31),
        )
        ProfileExperience.objects.create(
            profile=self.profile,
            organization="Research Lab",
            position="Analyst",
            start_date=date(2020, 1, 1),
            end_date=date(2023, 12, 31),
        )
        ProfileCertification.objects.create(
            profile=self.profile,
            certification_type=self.certification_type,
            name="Research Methods Certificate",
            issuer="Method Lab",
            issue_date=date(2024, 1, 1),
            credit_hours=40,
            no_expiration=True,
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
            publication_date=date(2026, 1, 1),
        )

    def test_public_profile_highlights_research_profile_sections(self):
        response = self.client.get(
            reverse("accounts:public_profile", kwargs={"username": self.user.username})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Casey Present")
        self.assertContains(response, "CV Present")
        self.assertNotContains(response, "@cv-present")
        self.assertIn("1</span> Publications", response.content.decode())
        self.assertContains(response, "Research and Professional Profile")
        self.assertContains(response, "Years of Experience")
        self.assertContains(response, "Years of Education")
        self.assertContains(response, "N. Certifications")
        self.assertContains(response, "- 40 hrs.")
        self.assertContains(response, "Databases")
        self.assertContains(response, "PostgreSQL")

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

    @patch("accounts.views.build_public_profile_pdf_bytes", return_value=b"%PDF-1.7 test")
    def test_public_profile_pdf_uses_reportlab_response(self, pdf_builder_mock):
        response = self.client.get(
            reverse("accounts:public_profile_pdf", kwargs={"username": self.user.username})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn('inline; filename="cv-present-cv.pdf"', response["Content-Disposition"])
        self.assertEqual(response.content, b"%PDF-1.7 test")
        pdf_builder_mock.assert_called_once()

    def test_get_user_avatar_url_returns_static_fallback_when_profile_avatar_resolution_fails(self):
        class BrokenProfile:
            def get_avatar_url(self):
                raise ValueError("broken avatar")

        user_like = SimpleNamespace(profile=BrokenProfile())

        self.assertEqual(
            get_user_avatar_url(user_like),
            static("images/avatars/default_private.png"),
        )


class ProfileCvSkillEditorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cv-editor", password="testpass123")
        self.user.user_permissions.add(
            Permission.objects.get(codename="edit_own_cv"),
        )
        self.profile = self.user.profile

        self.databases = ProfileSkillType.objects.create(name="Databases", slug="skill-editor-databases")
        self.mysql = ProfileSkillType.objects.create(
            name="MySQL",
            slug="skill-editor-mysql",
            parent=self.databases,
        )
        self.postgresql = ProfileSkillType.objects.create(
            name="PostgreSQL",
            slug="skill-editor-postgresql",
            parent=self.databases,
        )
        self.interpreted = ProfileSkillType.objects.create(name="Interpreted Code", slug="skill-editor-interpreted")
        self.python = ProfileSkillType.objects.create(
            name="Python",
            slug="skill-editor-python",
            parent=self.interpreted,
        )
        self.analytical = ProfileCompetencyType.objects.get(slug="analytical-thinking")
        self.problem_solving = ProfileCompetencyType.objects.get(slug="problem-solving")
        self.continuous_learning = ProfileCompetencyType.objects.get(slug="continuous-learning")
        self.autonomy = ProfileCompetencyType.objects.get(slug="autonomy")
        self.teamwork = ProfileCompetencyType.objects.get(slug="teamwork")
        self.communication = ProfileCompetencyType.objects.get(slug="communication")

    def _empty_cv_post_data(self):
        return {
            "education-TOTAL_FORMS": "0",
            "education-INITIAL_FORMS": "0",
            "experience-TOTAL_FORMS": "0",
            "experience-INITIAL_FORMS": "0",
            "certifications-TOTAL_FORMS": "0",
            "certifications-INITIAL_FORMS": "0",
            "languages-TOTAL_FORMS": "0",
            "languages-INITIAL_FORMS": "0",
            "competencies-TOTAL_FORMS": "0",
            "competencies-INITIAL_FORMS": "0",
            "links-TOTAL_FORMS": "0",
            "links-INITIAL_FORMS": "0",
            "external_publications-TOTAL_FORMS": "0",
            "external_publications-INITIAL_FORMS": "0",
        }

    def test_cv_editor_renders_category_based_skill_selector(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("accounts:profile_cv_edit"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add another category")
        self.assertContains(response, "Select a category")
        self.assertContains(response, "Databases")
        self.assertContains(response, "Interpreted Code")
        self.assertContains(response, "Analytical thinking")
        self.assertContains(response, "Maximum selection: 5 competencies.")

    def test_cv_editor_saves_selected_technologies_grouped_by_category(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:profile_cv_edit"),
            {
                **self._empty_cv_post_data(),
                "skill_groups-TOTAL_FORMS": "2",
                "skill_groups-0-category": str(self.databases.pk),
                "skill_groups-0-technologies": [str(self.mysql.pk), str(self.postgresql.pk)],
                "skill_groups-1-category": str(self.interpreted.pk),
                "skill_groups-1-technologies": [str(self.python.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        saved_skill_ids = list(
            ProfileSkill.objects.filter(profile=self.profile)
            .order_by("order", "id")
            .values_list("skill_type_id", flat=True)
        )
        self.assertEqual(saved_skill_ids, [self.mysql.pk, self.postgresql.pk, self.python.pk])

    def test_cv_editor_rejects_duplicate_categories(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:profile_cv_edit"),
            {
                **self._empty_cv_post_data(),
                "skill_groups-TOTAL_FORMS": "2",
                "skill_groups-0-category": str(self.databases.pk),
                "skill_groups-0-technologies": [str(self.mysql.pk)],
                "skill_groups-1-category": str(self.databases.pk),
                "skill_groups-1-technologies": [str(self.postgresql.pk)],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Each category can only be selected once.")
        self.assertFalse(ProfileSkill.objects.filter(profile=self.profile).exists())

    def test_cv_editor_saves_up_to_five_selected_competencies(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:profile_cv_edit"),
            {
                **self._empty_cv_post_data(),
                "skill_groups-TOTAL_FORMS": "0",
                "competency_choices": [
                    str(self.analytical.pk),
                    str(self.problem_solving.pk),
                    str(self.continuous_learning.pk),
                    str(self.autonomy.pk),
                    str(self.teamwork.pk),
                ],
            },
        )

        self.assertEqual(response.status_code, 302)
        saved_competency_ids = list(
            ProfileCompetency.objects.filter(profile=self.profile)
            .order_by("order", "id")
            .values_list("competency_type_id", flat=True)
        )
        self.assertEqual(
            saved_competency_ids,
            [
                self.analytical.pk,
                self.problem_solving.pk,
                self.continuous_learning.pk,
                self.autonomy.pk,
                self.teamwork.pk,
            ],
        )

    def test_cv_editor_rejects_more_than_five_competencies(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:profile_cv_edit"),
            {
                **self._empty_cv_post_data(),
                "skill_groups-TOTAL_FORMS": "0",
                "competency_choices": [
                    str(self.analytical.pk),
                    str(self.problem_solving.pk),
                    str(self.continuous_learning.pk),
                    str(self.autonomy.pk),
                    str(self.teamwork.pk),
                    str(self.communication.pk),
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You can select up to five transversal competencies.")
        self.assertFalse(ProfileCompetency.objects.filter(profile=self.profile).exists())
