from datetime import date

from django.core.management.base import BaseCommand

from books.models import Book
from categories.models import Category


class Command(BaseCommand):
    help = "Configura las dos fichas de informes EU-OSHA con autores externos."

    def handle(self, *args, **options):
        first = Book.objects.get(pk=5)
        first.author_mode = Book.AuthorMode.EXTERNAL
        first.external_authors = (
            "David Walters, Emma Wadsworth, Peter Hasle, Bjarke Refslund, "
            "Monique Ramioul y Ann-Beth Antonsson"
        )
        first.official_source_url = (
            "https://osha.europa.eu/en/publications/"
            "safety-and-health-micro-and-small-enterprises-eu-view-workplace"
        )
        first.direct_pdf_url = (
            "https://osha.europa.eu/sites/default/files/"
            "Safety_and_health_MSEs_Report_view_from_the_workplace.pdf"
        )
        first.save()

        second, _ = Book.objects.get_or_create(
            translations__slug="contexto-organizacion-preventiva-microempresas-pequenas-empresas",
            defaults={
                "is_published": False,
                "publication_date": date(2016, 1, 1),
                "price": "0.00",
                "currency": "EUR",
                "allow_free_preview": True,
                "requires_purchase": True,
                "author_mode": Book.AuthorMode.EXTERNAL,
                "external_authors": "David Walters y Emma Wadsworth, en representación del grupo de investigación SESAME.",
            },
        )
        second.author_mode = Book.AuthorMode.EXTERNAL
        second.external_authors = (
            "David Walters y Emma Wadsworth, en representación del grupo de "
            "investigación SESAME."
        )
        second.is_published = False
        second.publication_date = date(2016, 1, 1)
        second.price = "0.00"
        second.currency = "EUR"
        second.allow_free_preview = True
        second.requires_purchase = True
        second.isbn = "978-92-9240-898-5"
        second.set_current_language("es")
        second.title = "Contexto y organización preventiva en microempresas y pequeñas empresas"
        second.slug = "contexto-organizacion-preventiva-microempresas-pequenas-empresas"
        second.subtitle = (
            "Contexts and arrangements for occupational safety and health in "
            "micro and small enterprises in the EU – SESAME project"
        )
        second.excerpt = (
            "Revisión académica sobre la situación preventiva de las "
            "microempresas y pequeñas empresas europeas."
        )
        second.description = """
            <p>Revisión académica sobre la situación preventiva de las microempresas y pequeñas empresas europeas. Estudia sus limitaciones económicas y organizativas, la accidentalidad, la participación de los trabajadores y las intervenciones que pueden mejorar la prevención.</p>
            <h2>Datos bibliográficos</h2>
            <ul>
                <li><strong>Autores principales:</strong> David Walters y Emma Wadsworth, en representación del grupo de investigación SESAME.</li>
                <li><strong>Editor:</strong> Agencia Europea para la Seguridad y la Salud en el Trabajo (EU-OSHA).</li>
                <li><strong>Editorial:</strong> Oficina de Publicaciones de la Unión Europea.</li>
                <li><strong>Año:</strong> 2016.</li>
                <li><strong>Extensión:</strong> 138 páginas.</li>
                <li><strong>ISBN:</strong> 978-92-9240-898-5.</li>
                <li><strong>DOI:</strong> 10.2802/754838.</li>
                <li><strong>Idioma original:</strong> inglés.</li>
            </ul>
        """
        second.meta_title = "Contexto y organización preventiva en microempresas | EU-OSHA"
        second.meta_description = (
            "Revisión SESAME sobre organización preventiva, participación y "
            "condiciones de seguridad y salud en microempresas europeas."
        )
        second.save()

        category = Category.objects.filter(translations__name="Pymes").distinct().first()
        if category:
            first.categories.add(category)
            second.categories.add(category)

        third, _ = Book.objects.get_or_create(
            translations__slug="informe-final-proyecto-europeo-sesame",
            defaults={
                "is_published": False,
                "publication_date": date(2018, 1, 1),
                "price": "0.00",
                "currency": "EUR",
                "allow_free_preview": True,
                "requires_purchase": True,
                "author_mode": Book.AuthorMode.EXTERNAL,
            },
        )
        third.author_mode = Book.AuthorMode.EXTERNAL
        third.external_authors = "David Walters, Emma Wadsworth, Peter Hasle, Bjarke Refslund y Monique Ramioul"
        third.is_published = False
        third.publication_date = date(2018, 1, 1)
        third.price = "0.00"
        third.currency = "EUR"
        third.allow_free_preview = True
        third.requires_purchase = True
        third.isbn = "978-92-9496-894-4"
        third.official_source_url = "https://osha.europa.eu/en/publications/safety-and-health-micro-and-small-enterprises-eu-final-report-3-year-sesame-project"
        third.direct_pdf_url = "https://osha.europa.eu/sites/default/files/Safety_and_health_MSEs_Final_report_3_yr_SESAME.pdf"
        third.set_current_language("es")
        third.title = "Informe final del proyecto europeo SESAME"
        third.slug = "informe-final-proyecto-europeo-sesame"
        third.subtitle = "Safety and Health in Micro and Small Enterprises in the EU: Final report from the 3-year SESAME project"
        third.excerpt = "Síntesis final de tres años de investigación europea sobre prevención en microempresas y pequeñas empresas."
        third.description = """
            <p>Síntesis final de tres años de investigación europea sobre prevención en microempresas y pequeñas empresas. Identifica qué intervenciones funcionan, la importancia del acompañamiento personalizado y la necesidad de soluciones sencillas, adaptadas al sector y fáciles de aplicar.</p>
            <h2>Datos bibliográficos</h2>
            <ul>
                <li><strong>Autores:</strong> David Walters, Emma Wadsworth, Peter Hasle, Bjarke Refslund y Monique Ramioul.</li>
                <li><strong>Editor:</strong> Agencia Europea para la Seguridad y la Salud en el Trabajo (EU-OSHA).</li>
                <li><strong>Editorial:</strong> Oficina de Publicaciones de la Unión Europea.</li>
                <li><strong>Año:</strong> 2018.</li>
                <li><strong>Extensión:</strong> 103 páginas.</li>
                <li><strong>ISBN:</strong> 978-92-9496-894-4.</li>
                <li><strong>DOI:</strong> 10.2802/29855.</li>
                <li><strong>Idioma original:</strong> inglés.</li>
                <li><strong>Licencia indicada:</strong> reproducción autorizada con reconocimiento de la fuente (página 2 del PDF).</li>
            </ul>
        """
        third.meta_title = "Informe final del proyecto SESAME | EU-OSHA"
        third.meta_description = "Síntesis final SESAME sobre intervenciones y apoyo preventivo eficaz para microempresas y pequeñas empresas."
        third.save()
        if category:
            third.categories.add(category)

        self.stdout.write(self.style.SUCCESS("Tres fichas EU-OSHA configuradas."))
