from django.db import migrations, models
import django.db.models.deletion


ROOT_SKILL_TYPES = [
    {
        "slug": "databases",
        "names": {"es": "Bases de datos", "en": "Databases", "ca": "Bases de dades"},
        "children": [
            ("sql", "SQL"),
            ("sql-server", "SQL Server"),
            ("oracle", "Oracle"),
            ("mysql", "MySQL"),
            ("postgresql", "PostgreSQL"),
            ("sqlite", "SQLite"),
            ("mongodb", "MongoDB"),
        ],
    },
    {
        "slug": "compiled-code",
        "names": {"es": "Código compilado", "en": "Compiled code", "ca": "Codi compilat"},
        "children": [
            ("java", "Java"),
            ("csharp", "C#"),
            ("cplusplus", "C/C++"),
            ("go", "Go"),
            ("rust", "Rust"),
        ],
    },
    {
        "slug": "interpreted-code",
        "names": {"es": "Código interpretado", "en": "Interpreted code", "ca": "Codi interpretat"},
        "children": [
            ("python", "Python"),
            ("php", "PHP"),
            ("javascript", "JavaScript"),
            ("typescript", "TypeScript"),
            ("r", "R"),
            ("sas", "SAS"),
            ("bash", "Bash"),
        ],
    },
    {
        "slug": "data-science",
        "names": {"es": "Ciencia de datos", "en": "Data science", "ca": "Ciència de dades"},
        "children": [
            ("pandas", "Pandas"),
            ("numpy", "NumPy"),
            ("scikit-learn", "scikit-learn"),
            ("tensorflow", "TensorFlow"),
            ("pytorch", "PyTorch"),
            ("jupyter", "Jupyter"),
        ],
    },
    {
        "slug": "web-development",
        "names": {"es": "Desarrollo web", "en": "Web development", "ca": "Desenvolupament web"},
        "children": [
            ("html-css", "HTML/CSS"),
            ("django", "Django"),
            ("flask", "Flask"),
            ("fastapi", "FastAPI"),
            ("laravel", "Laravel"),
            ("react", "React"),
            ("nodejs", "Node.js"),
        ],
    },
    {
        "slug": "devops-infrastructure",
        "names": {"es": "DevOps e infraestructura", "en": "DevOps and infrastructure", "ca": "DevOps i infraestructura"},
        "children": [
            ("git", "Git"),
            ("docker", "Docker"),
            ("linux", "Linux"),
            ("ci-cd", "CI/CD"),
            ("aws", "AWS"),
            ("azure", "Azure"),
            ("gcp", "GCP"),
        ],
    },
    {
        "slug": "analytics-bi",
        "names": {"es": "Analítica y BI", "en": "Analytics and BI", "ca": "Analítica i BI"},
        "children": [
            ("power-bi", "Power BI"),
            ("tableau", "Tableau"),
            ("excel", "Excel"),
            ("looker-studio", "Looker Studio"),
            ("spss", "SPSS"),
        ],
    },
]


def seed_skill_hierarchy(apps, schema_editor):
    ProfileSkillType = apps.get_model("accounts", "ProfileSkillType")
    ProfileSkillTypeTranslation = apps.get_model("accounts", "ProfileSkillTypeTranslation")

    def ensure_translations(instance, names):
        for language_code, name in names.items():
            ProfileSkillTypeTranslation.objects.update_or_create(
                master_id=instance.pk,
                language_code=language_code,
                defaults={"name": name, "description": ""},
            )

    for order, root_data in enumerate(ROOT_SKILL_TYPES, start=1):
        root, _ = ProfileSkillType.objects.update_or_create(
            slug=root_data["slug"],
            defaults={
                "order": order,
                "is_active": True,
                "parent": None,
            },
        )
        ensure_translations(root, root_data["names"])

        for child_order, (child_slug, child_name) in enumerate(root_data["children"], start=1):
            child, _ = ProfileSkillType.objects.update_or_create(
                slug=child_slug,
                defaults={
                    "order": child_order,
                    "is_active": True,
                    "parent_id": root.pk,
                },
            )
            ensure_translations(
                child,
                {
                    "es": child_name,
                    "en": child_name,
                    "ca": child_name,
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_profilecertification_updates"),
    ]

    operations = [
        migrations.AddField(
            model_name="profileskilltype",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="children",
                to="accounts.profileskilltype",
                verbose_name="Parent category",
            ),
        ),
        migrations.RunPython(seed_skill_hierarchy, migrations.RunPython.noop),
    ]
