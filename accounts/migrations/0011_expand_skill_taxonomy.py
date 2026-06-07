from django.db import migrations


ROOT_SKILL_TYPES = [
    {
        "slug": "relational-databases",
        "aliases": ["databases"],
        "names": {
            "es": "Bases de datos relacionales",
            "en": "Relational databases",
            "ca": "Bases de dades relacionals",
        },
        "children": [
            ("sql", "SQL"),
            ("mysql", "MySQL"),
            ("postgresql", "PostgreSQL"),
            ("sql-server", "SQL Server"),
            ("oracle", "Oracle"),
            ("sqlite", "SQLite"),
            ("mariadb", "MariaDB"),
        ],
    },
    {
        "slug": "non-relational-databases",
        "names": {
            "es": "Bases de datos no relacionales",
            "en": "Non-relational databases",
            "ca": "Bases de dades no relacionals",
        },
        "children": [
            ("mongodb", "MongoDB"),
            ("redis", "Redis"),
            ("cassandra", "Cassandra"),
            ("elasticsearch", "Elasticsearch"),
            ("opensearch", "OpenSearch"),
            ("firestore", "Firestore"),
        ],
    },
    {
        "slug": "compiled-code",
        "names": {
            "es": "Código compilado",
            "en": "Compiled code",
            "ca": "Codi compilat",
        },
        "children": [
            ("java", "Java"),
            ("csharp", "C#"),
            ("cplusplus", "C/C++"),
            ("go", "Go"),
            ("rust", "Rust"),
            ("kotlin", "Kotlin"),
            ("swift", "Swift"),
        ],
    },
    {
        "slug": "interpreted-and-scripting",
        "aliases": ["interpreted-code"],
        "names": {
            "es": "Código interpretado y scripting",
            "en": "Interpreted and scripting languages",
            "ca": "Codi interpretat i scripting",
        },
        "children": [
            ("python", "Python"),
            ("php", "PHP"),
            ("javascript", "JavaScript"),
            ("typescript", "TypeScript"),
            ("r", "R"),
            ("sas", "SAS"),
            ("bash", "Bash"),
            ("ruby", "Ruby"),
            ("matlab", "MATLAB"),
            ("powershell", "PowerShell"),
        ],
    },
    {
        "slug": "frontend-development",
        "aliases": ["web-development"],
        "names": {
            "es": "Desarrollo frontend",
            "en": "Frontend development",
            "ca": "Desenvolupament frontend",
        },
        "children": [
            ("html-css", "HTML/CSS"),
            ("react", "React"),
            ("vuejs", "Vue.js"),
            ("angular", "Angular"),
            ("nextjs", "Next.js"),
            ("svelte", "Svelte"),
            ("bootstrap", "Bootstrap"),
        ],
    },
    {
        "slug": "backend-and-apis",
        "names": {
            "es": "Backend y APIs",
            "en": "Backend and APIs",
            "ca": "Backend i APIs",
        },
        "children": [
            ("django", "Django"),
            ("fastapi", "FastAPI"),
            ("flask", "Flask"),
            ("nodejs", "Node.js"),
            ("laravel", "Laravel"),
            ("spring-boot", "Spring Boot"),
            ("aspnet-core", "ASP.NET Core"),
            ("ruby-on-rails", "Ruby on Rails"),
        ],
    },
    {
        "slug": "mobile-development",
        "names": {
            "es": "Desarrollo móvil",
            "en": "Mobile development",
            "ca": "Desenvolupament mòbil",
        },
        "children": [
            ("android-kotlin", "Android (Kotlin)"),
            ("ios-swift", "iOS (Swift)"),
            ("flutter", "Flutter"),
            ("react-native", "React Native"),
        ],
    },
    {
        "slug": "data-science-ml",
        "aliases": ["data-science"],
        "names": {
            "es": "Ciencia de datos y ML",
            "en": "Data science and ML",
            "ca": "Ciència de dades i ML",
        },
        "children": [
            ("jupyter", "Jupyter"),
            ("numpy", "NumPy"),
            ("pandas", "Pandas"),
            ("scikit-learn", "scikit-learn"),
            ("tensorflow", "TensorFlow"),
            ("pytorch", "PyTorch"),
            ("keras", "Keras"),
            ("xgboost", "XGBoost"),
        ],
    },
    {
        "slug": "data-engineering",
        "names": {
            "es": "Ingeniería de datos",
            "en": "Data engineering",
            "ca": "Enginyeria de dades",
        },
        "children": [
            ("apache-spark", "Apache Spark"),
            ("apache-airflow", "Apache Airflow"),
            ("dbt", "dbt"),
            ("apache-kafka", "Apache Kafka"),
            ("databricks", "Databricks"),
            ("hadoop", "Hadoop"),
        ],
    },
    {
        "slug": "analytics-bi",
        "names": {
            "es": "Analítica y BI",
            "en": "Analytics and BI",
            "ca": "Analítica i BI",
        },
        "children": [
            ("power-bi", "Power BI"),
            ("tableau", "Tableau"),
            ("excel", "Excel"),
            ("looker-studio", "Looker Studio"),
            ("spss", "SPSS"),
            ("qlik-sense", "Qlik Sense"),
        ],
    },
    {
        "slug": "cloud-devops-infrastructure",
        "aliases": ["devops-infrastructure"],
        "names": {
            "es": "Cloud, DevOps e infraestructura",
            "en": "Cloud, DevOps and infrastructure",
            "ca": "Cloud, DevOps i infraestructura",
        },
        "children": [
            ("git", "Git"),
            ("docker", "Docker"),
            ("kubernetes", "Kubernetes"),
            ("linux", "Linux"),
            ("ci-cd", "CI/CD"),
            ("terraform", "Terraform"),
            ("aws", "AWS"),
            ("azure", "Azure"),
            ("gcp", "GCP"),
        ],
    },
]


def expand_skill_taxonomy(apps, schema_editor):
    ProfileSkillType = apps.get_model("accounts", "ProfileSkillType")
    ProfileSkillTypeTranslation = apps.get_model("accounts", "ProfileSkillTypeTranslation")

    def ensure_translations(instance, names):
        for language_code, name in names.items():
            ProfileSkillTypeTranslation.objects.update_or_create(
                master_id=instance.pk,
                language_code=language_code,
                defaults={"name": name, "description": ""},
            )

    def get_by_slug_or_alias(slug, aliases=None):
        aliases = aliases or []
        for candidate in [slug, *aliases]:
            instance = ProfileSkillType.objects.filter(slug=candidate).first()
            if instance:
                return instance
        return None

    def ensure_root(root_data, order):
        root = get_by_slug_or_alias(root_data["slug"], root_data.get("aliases"))
        if root is None:
            root = ProfileSkillType.objects.create(
                slug=root_data["slug"],
                order=order,
                is_active=True,
                parent=None,
            )
        else:
            root.slug = root_data["slug"]
            root.order = order
            root.is_active = True
            root.parent = None
            root.save(update_fields=["slug", "order", "is_active", "parent"])

        ensure_translations(root, root_data["names"])
        return root

    def ensure_child(parent, child_slug, child_name, order):
        child = ProfileSkillType.objects.filter(slug=child_slug).first()
        if child is None:
            child = ProfileSkillType.objects.create(
                slug=child_slug,
                order=order,
                is_active=True,
                parent_id=parent.pk,
            )
        else:
            child.order = order
            child.is_active = True
            child.parent_id = parent.pk
            child.save(update_fields=["order", "is_active", "parent"])

        ensure_translations(
            child,
            {
                "es": child_name,
                "en": child_name,
                "ca": child_name,
            },
        )

    for order, root_data in enumerate(ROOT_SKILL_TYPES, start=1):
        root = ensure_root(root_data, order)
        for child_order, (child_slug, child_name) in enumerate(root_data["children"], start=1):
            ensure_child(root, child_slug, child_name, child_order)


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("accounts", "0010_alter_profilecertification_options_and_more"),
    ]

    operations = [
        migrations.RunPython(expand_skill_taxonomy, migrations.RunPython.noop),
    ]
