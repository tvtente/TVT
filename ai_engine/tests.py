from django.test import SimpleTestCase

from ai_engine.service import _risk_level


class RiskLevelTests(SimpleTestCase):
    def test_high_risk_comment_needs_extra_review(self):
        self.assertEqual(_risk_level("Necesito consejo médico urgente"), "high")

    def test_regular_comment_has_low_risk(self):
        self.assertEqual(_risk_level("Qué bonita publicación"), "low")
