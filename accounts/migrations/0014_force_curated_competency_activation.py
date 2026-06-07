from django.db import migrations


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


def force_curated_competency_activation(apps, schema_editor):
    ProfileCompetencyType = apps.get_model("accounts", "ProfileCompetencyType")

    for competency in ProfileCompetencyType.objects.all():
        competency.is_active = competency.slug in CURATED_COMPETENCY_SLUGS
        competency.save(update_fields=["is_active"])


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("accounts", "0013_deactivate_legacy_competencies"),
    ]

    operations = [
        migrations.RunPython(force_curated_competency_activation, migrations.RunPython.noop),
    ]
