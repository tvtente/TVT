 # Ejecutar con:
# python manage.py shell < scripts/dev_tools/seed_demo_book.py

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

from books.models import Book
from categories.models import Category


User = get_user_model()

# Autor demo: intenta usar tvt; si no existe, usa el primer superuser/staff/user.
author = (
    User.objects.filter(username="tvt").first()
    or User.objects.filter(is_superuser=True).first()
    or User.objects.filter(is_staff=True).first()
    or User.objects.first()
)

if not author:
    raise SystemExit("❌ No hay usuarios disponibles para asignar como autor.")

# Categoría opcional
category = Category.objects.first()

book, created = Book.objects.get_or_create(
    isbn="978-0-000000-00-1",
    defaults={
        "publication_date": timezone.now().date(),
        "is_published": True,
        "price": 9.99,
        "currency": "EUR",
        "allow_free_preview": True,
        "requires_purchase": True,
    },
)

book.authors.set([author])

if category:
    book.categories.set([category])

# Español
book.set_current_language("es")
book.title = "El arte de cuestionar"
book.slug = slugify("el-arte-de-cuestionar")
book.subtitle = "Una introducción editorial al pensamiento crítico"
book.excerpt = "<p>Un libro breve para abrir preguntas donde otros solo ven respuestas.</p>"
book.description = """
<p><strong>El arte de cuestionar</strong> explora cómo las ideas, las normas sociales
y los relatos públicos moldean nuestra manera de pensar.</p>
<p>Es una obra editorial de prueba para validar el módulo de libros en TVTente.</p>
"""
book.table_of_contents = """
<ol>
  <li>Por qué cuestionar importa</li>
  <li>Opinión, identidad y debate público</li>
  <li>La incomodidad como herramienta</li>
  <li>Hacia una cultura crítica</li>
</ol>
"""
book.meta_title = "El arte de cuestionar | TVTente"
book.meta_description = "Libro editorial demo para validar el módulo Books de TVTente."
book.save()

# Inglés
book.set_current_language("en")
book.title = "The Art of Questioning"
book.slug = slugify("the-art-of-questioning")
book.subtitle = "An editorial introduction to critical thinking"
book.excerpt = "<p>A short book to open questions where others only see answers.</p>"
book.description = """
<p><strong>The Art of Questioning</strong> explores how ideas, social norms
and public narratives shape the way we think.</p>
<p>This is a demo editorial book created to validate the TVTente Books module.</p>
"""
book.table_of_contents = """
<ol>
  <li>Why questioning matters</li>
  <li>Opinion, identity and public debate</li>
  <li>Discomfort as a tool</li>
  <li>Towards a critical culture</li>
</ol>
"""
book.meta_title = "The Art of Questioning | TVTente"
book.meta_description = "Demo editorial book created to validate the TVTente Books module."
book.save()

# Catalán
book.set_current_language("ca")
book.title = "L’art de qüestionar"
book.slug = slugify("l-art-de-questionar")
book.subtitle = "Una introducció editorial al pensament crític"
book.excerpt = "<p>Un llibre breu per obrir preguntes allà on altres només veuen respostes.</p>"
book.description = """
<p><strong>L’art de qüestionar</strong> explora com les idees, les normes socials
i els relats públics modelen la nostra manera de pensar.</p>
<p>És un llibre editorial de prova per validar el mòdul de llibres de TVTente.</p>
"""
book.table_of_contents = """
<ol>
  <li>Per què qüestionar importa</li>
  <li>Opinió, identitat i debat públic</li>
  <li>La incomoditat com a eina</li>
  <li>Cap a una cultura crítica</li>
</ol>
"""
book.meta_title = "L’art de qüestionar | TVTente"
book.meta_description = "Llibre editorial demo per validar el mòdul Books de TVTente."
book.save()

print("")
print("✅ Libro demo creado/actualizado correctamente.")
print(f"📘 ID: {book.id}")
print(f"👤 Autor: {author.username}")
print("🌍 Traducciones: es, en, ca")
print("🖼 Sin imágenes")
print("📄 Sin PDFs")
