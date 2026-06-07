from django.db import migrations


CURATED_COMPETENCY_SLUGS = {
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
}


def deactivate_legacy_competencies(apps, schema_editor):
    ProfileCompetencyType = apps.get_model("accounts", "ProfileCompetencyType")

    ProfileCompetencyType.objects.exclude(
        slug__in=CURATED_COMPETENCY_SLUGS,
    ).update(is_active=False)

    ProfileCompetencyType.objects.filter(
        slug__in=CURATED_COMPETENCY_SLUGS,
    ).update(is_active=True)


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("accounts", "0012_seed_transversal_competencies"),
    ]

    operations = [
        migrations.RunPython(deactivate_legacy_competencies, migrations.RunPython.noop),
    ]
