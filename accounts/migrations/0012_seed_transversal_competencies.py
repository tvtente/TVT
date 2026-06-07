from django.db import migrations


COMPETENCIES = [
    {
        "slug": "analytical-thinking",
        "names": {"es": "Pensamiento analítico", "en": "Analytical thinking", "ca": "Pensament analític"},
        "descriptions": {
            "es": "Capacidad para descomponer problemas complejos, identificar patrones y tomar decisiones fundamentadas a partir de evidencias.",
            "en": "Ability to break down complex problems, identify patterns, and make evidence-based decisions.",
            "ca": "Capacitat per descompondre problemes complexos, identificar patrons i prendre decisions fonamentades en evidències.",
        },
    },
    {
        "slug": "problem-solving",
        "names": {"es": "Resolución de problemas", "en": "Problem solving", "ca": "Resolució de problemes"},
        "descriptions": {
            "es": "Capacidad para abordar incidencias, proponer alternativas viables y ejecutar soluciones con criterio práctico.",
            "en": "Ability to address issues, propose viable alternatives, and execute practical solutions.",
            "ca": "Capacitat per abordar incidències, proposar alternatives viables i executar solucions amb criteri pràctic.",
        },
    },
    {
        "slug": "continuous-learning",
        "names": {"es": "Aprendizaje continuo", "en": "Continuous learning", "ca": "Aprenentatge continu"},
        "descriptions": {
            "es": "Disposición para actualizar conocimientos, incorporar nuevas herramientas y aprender de forma autónoma y sostenida.",
            "en": "Willingness to update knowledge, adopt new tools, and learn autonomously on an ongoing basis.",
            "ca": "Disposició per actualitzar coneixements, incorporar noves eines i aprendre de manera autònoma i sostinguda.",
        },
    },
    {
        "slug": "autonomy",
        "names": {"es": "Autonomía", "en": "Autonomy", "ca": "Autonomia"},
        "descriptions": {
            "es": "Capacidad para organizar el propio trabajo, priorizar tareas y avanzar con responsabilidad sin supervisión constante.",
            "en": "Ability to organize one’s own work, prioritize tasks, and move forward responsibly without constant supervision.",
            "ca": "Capacitat per organitzar la pròpia feina, prioritzar tasques i avançar amb responsabilitat sense supervisió constant.",
        },
    },
    {
        "slug": "technical-leadership",
        "names": {"es": "Liderazgo técnico", "en": "Technical leadership", "ca": "Lideratge tècnic"},
        "descriptions": {
            "es": "Capacidad para orientar decisiones técnicas, acompañar a otros y elevar la calidad del trabajo colectivo.",
            "en": "Ability to guide technical decisions, support others, and raise the quality of collective work.",
            "ca": "Capacitat per orientar decisions tècniques, acompanyar altres persones i elevar la qualitat del treball col·lectiu.",
        },
    },
    {
        "slug": "communication",
        "names": {"es": "Comunicación efectiva", "en": "Effective communication", "ca": "Comunicació efectiva"},
        "descriptions": {
            "es": "Capacidad para explicar ideas, procesos y resultados con claridad a públicos técnicos y no técnicos.",
            "en": "Ability to explain ideas, processes, and results clearly to technical and non-technical audiences.",
            "ca": "Capacitat per explicar idees, processos i resultats amb claredat a públics tècnics i no tècnics.",
        },
    },
    {
        "slug": "teamwork",
        "names": {"es": "Trabajo en equipo", "en": "Teamwork", "ca": "Treball en equip"},
        "descriptions": {
            "es": "Capacidad para colaborar, coordinar esfuerzos y construir soluciones con otras personas de forma productiva.",
            "en": "Ability to collaborate, coordinate efforts, and build solutions productively with others.",
            "ca": "Capacitat per col·laborar, coordinar esforços i construir solucions de manera productiva amb altres persones.",
        },
    },
    {
        "slug": "adaptability",
        "names": {"es": "Adaptabilidad", "en": "Adaptability", "ca": "Adaptabilitat"},
        "descriptions": {
            "es": "Capacidad para ajustarse a cambios de contexto, herramientas, prioridades o metodologías sin perder efectividad.",
            "en": "Ability to adjust to changes in context, tools, priorities, or methodologies without losing effectiveness.",
            "ca": "Capacitat per ajustar-se a canvis de context, eines, prioritats o metodologies sense perdre efectivitat.",
        },
    },
    {
        "slug": "attention-to-detail",
        "names": {"es": "Atención al detalle", "en": "Attention to detail", "ca": "Atenció al detall"},
        "descriptions": {
            "es": "Cuidado por la precisión, la consistencia y la detección temprana de errores o incoherencias.",
            "en": "Care for precision, consistency, and early detection of errors or inconsistencies.",
            "ca": "Cura per la precisió, la consistència i la detecció primerenca d’errors o incoherències.",
        },
    },
    {
        "slug": "decision-making",
        "names": {"es": "Toma de decisiones", "en": "Decision-making", "ca": "Presa de decisions"},
        "descriptions": {
            "es": "Capacidad para valorar información disponible, ponderar riesgos y decidir con oportunidad y criterio.",
            "en": "Ability to assess available information, weigh risks, and make timely, well-judged decisions.",
            "ca": "Capacitat per valorar la informació disponible, ponderar riscos i decidir amb oportunitat i criteri.",
        },
    },
    {
        "slug": "time-management",
        "names": {"es": "Gestión del tiempo", "en": "Time management", "ca": "Gestió del temps"},
        "descriptions": {
            "es": "Capacidad para planificar tiempos, sostener ritmos de entrega y gestionar varias tareas con orden.",
            "en": "Ability to plan time, maintain delivery pace, and manage multiple tasks in an organized way.",
            "ca": "Capacitat per planificar temps, sostenir ritmes de lliurament i gestionar diverses tasques amb ordre.",
        },
    },
    {
        "slug": "research-rigor",
        "names": {"es": "Rigor investigativo", "en": "Research rigor", "ca": "Rigor investigador"},
        "descriptions": {
            "es": "Capacidad para documentar procesos, contrastar fuentes y sostener estándares metodológicos consistentes.",
            "en": "Ability to document processes, contrast sources, and maintain consistent methodological standards.",
            "ca": "Capacitat per documentar processos, contrastar fonts i sostenir estàndards metodològics consistents.",
        },
    },
]


def seed_transversal_competencies(apps, schema_editor):
    ProfileCompetencyType = apps.get_model("accounts", "ProfileCompetencyType")
    ProfileCompetencyTypeTranslation = apps.get_model("accounts", "ProfileCompetencyTypeTranslation")

    for order, competency in enumerate(COMPETENCIES, start=1):
        instance, _ = ProfileCompetencyType.objects.update_or_create(
            slug=competency["slug"],
            defaults={"order": order, "is_active": True},
        )

        for language_code, name in competency["names"].items():
            ProfileCompetencyTypeTranslation.objects.update_or_create(
                master_id=instance.pk,
                language_code=language_code,
                defaults={
                    "name": name,
                    "description": competency["descriptions"][language_code],
                },
            )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("accounts", "0011_expand_skill_taxonomy"),
    ]

    operations = [
        migrations.RunPython(seed_transversal_competencies, migrations.RunPython.noop),
    ]
