from datetime import date

from django.core.management.base import BaseCommand

from books.models import Book
from categories.models import Category


class Command(BaseCommand):
    help = "Elimina los libros de ejemplo y crea la ficha en borrador del informe EU-OSHA."

    def handle(self, *args, **options):
        Book.objects.all().delete()

        book = Book(
            is_published=False,
            publication_date=date(2018, 1, 1),
            price="0.00",
            currency="EUR",
            allow_free_preview=True,
            requires_purchase=True,
        )
        book.set_current_language("es")
        book.title = "La prevención en pequeñas empresas desde el lugar de trabajo"
        book.slug = "prevencion-pequenas-empresas-lugar-trabajo"
        book.subtitle = (
            "Safety and health in micro and small enterprises in the EU: "
            "the view from the workplace"
        )
        book.excerpt = (
            "Investigación europea sobre cómo las microempresas y pequeñas "
            "empresas afrontan la prevención de riesgos laborales."
        )
        book.description = """
            <p>Investigación basada en 162 microempresas y pequeñas empresas de nueve países europeos. Analiza cómo trabajadores y propietarios entienden la prevención, qué dificultades encuentran y por qué algunas organizaciones actúan de manera reactiva.</p>
            <p>Incluye casos de restauración, transporte, construcción, comercio y otros sectores.</p>
            <h2>Datos bibliográficos</h2>
            <ul>
                <li><strong>Autores:</strong> David Walters, Emma Wadsworth, Peter Hasle, Bjarke Refslund, Monique Ramioul y Ann-Beth Antonsson.</li>
                <li><strong>Editor:</strong> Agencia Europea para la Seguridad y la Salud en el Trabajo (EU-OSHA).</li>
                <li><strong>Año:</strong> 2018.</li>
                <li><strong>Extensión:</strong> 163 páginas.</li>
                <li><strong>ISBN:</strong> 978-92-9020-597-5.</li>
                <li><strong>DOI:</strong> 10.2823/993143.</li>
                <li><strong>Idioma original:</strong> inglés.</li>
                <li><strong>Licencia indicada:</strong> reproducción autorizada siempre que se reconozca la fuente (página 2 del PDF).</li>
            </ul>
            <p><a href="https://osha.europa.eu/en/publications/safety-and-health-micro-and-small-enterprises-eu-view-workplace" target="_blank" rel="noopener noreferrer">Consultar página oficial de EU-OSHA</a></p>
            <p><a href="https://osha.europa.eu/sites/default/files/Safety_and_health_MSEs_Report_view_from_the_workplace.pdf" target="_blank" rel="noopener noreferrer">Consultar PDF original</a></p>
        """
        book.meta_title = "La prevención en pequeñas empresas | EU-OSHA"
        book.meta_description = (
            "Investigación de EU-OSHA sobre prevención en 162 microempresas y "
            "pequeñas empresas europeas."
        )
        book.save()

        category = Category.objects.filter(translations__name="Pymes").distinct().first()
        if category:
            book.categories.add(category)

        self.stdout.write(
            self.style.SUCCESS(
                f"Libro {book.pk} creado en borrador: {book.title}"
            )
        )
