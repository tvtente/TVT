"""Actualiza las páginas legales del CMS para la integración de Instagram."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from pages.models import Page


PRIVACY_APPENDICES = {
    "es": """
<hr><h2>Instagram, mensajes y asistencia automatizada</h2>
<p>Cuando una persona interactúa con las cuentas profesionales de Instagram de TVT, podemos recibir y tratar su identificador de Instagram, nombre de usuario, nombre visible, comentarios públicos, mensajes directos y los metadatos técnicos asociados. Los usamos para atender interacciones, moderar contenido, preparar respuestas y mejorar la atención.</p>
<p>Algunas respuestas pueden prepararse con un modelo de lenguaje administrado por TVT. No se toman decisiones automatizadas con efectos legales o similares. Las interacciones se realizan mediante los servicios de Meta/Instagram y los proveedores técnicos estrictamente necesarios para operar el servicio.</p>
<p>Para solicitar acceso, rectificación o eliminación, consulta la página de acceso y eliminación de datos o escribe a <a href=\"mailto:prodsc.com@gmail.com\">prodsc.com@gmail.com</a>.</p>
""",
    "en": """
<hr><h2>Instagram, messages and automated assistance</h2>
<p>When a person interacts with TVT professional Instagram accounts, we may receive and process their Instagram identifier, username, display name, public comments, direct messages and associated technical metadata. We use this information to respond to interactions, moderate content, prepare replies and improve assistance.</p>
<p>Some replies may be prepared using a language model operated by TVT. No automated decisions with legal or similarly significant effects are made. Interactions take place through Meta/Instagram and the technical providers strictly required to operate the service.</p>
<p>To request access, correction or deletion, see the data access and deletion page or email <a href=\"mailto:prodsc.com@gmail.com\">prodsc.com@gmail.com</a>.</p>
""",
    "ca": """
<hr><h2>Instagram, missatges i assistència automatitzada</h2>
<p>Quan una persona interactua amb els comptes professionals d'Instagram de TVT, podem rebre i tractar el seu identificador d'Instagram, nom d'usuari, nom visible, comentaris públics, missatges directes i metadades tècniques associades. Les fem servir per atendre interaccions, moderar contingut, preparar respostes i millorar l'atenció.</p>
<p>Algunes respostes es poden preparar amb un model de llenguatge gestionat per TVT. No es prenen decisions automatitzades amb efectes legals o similars. Les interaccions es fan mitjançant Meta/Instagram i els proveïdors tècnics estrictament necessaris.</p>
<p>Per sol·licitar accés, rectificació o eliminació, consulta la pàgina d'accés i eliminació de dades o escriu a <a href=\"mailto:prodsc.com@gmail.com\">prodsc.com@gmail.com</a>.</p>
""",
}

TERMS_APPENDICES = {
    "es": """
<hr><h2>Interacciones en Instagram</h2>
<p>Las respuestas de TVT en Instagram pueden prepararse con asistencia de inteligencia artificial y revisarse por el equipo. Son informativas y no sustituyen asesoramiento médico, legal, financiero ni profesional. Debes usar estos canales de forma respetuosa y conforme a la ley.</p>
""",
    "en": """
<hr><h2>Instagram interactions</h2>
<p>TVT replies on Instagram may be prepared with artificial intelligence assistance and reviewed by the team. They are informational and do not replace medical, legal, financial or professional advice. You must use these channels respectfully and lawfully.</p>
""",
    "ca": """
<hr><h2>Interaccions a Instagram</h2>
<p>Les respostes de TVT a Instagram es poden preparar amb assistència d'intel·ligència artificial i revisar-se per l'equip. Són informatives i no substitueixen assessorament mèdic, legal, financer ni professional. Has d'utilitzar aquests canals de manera respectuosa i conforme a la llei.</p>
""",
}

DATA_PAGE = {
    "es": {
        "title": "Acceso y eliminación de datos",
        "slug": "acceso-y-eliminacion-de-datos",
        "content": """<h2>Acceso y eliminación de datos</h2><p>Puedes solicitar una copia, corrección o eliminación de los datos personales que TVT conserva sobre tus interacciones.</p><h3>Solicitud por correo</h3><p>Escribe a <a href=\"mailto:prodsc.com@gmail.com?subject=Solicitud%20de%20datos%20TVT\">prodsc.com@gmail.com</a> con el asunto <em>Solicitud de datos TVT</em>. Indica tu nombre de usuario de Instagram y si solicitas acceso, corrección o eliminación.</p><h3>Solicitud desde Meta o Instagram</h3><p>Si realizas una solicitud de eliminación desde Meta o Instagram, TVT procesará la solicitud recibida por el canal oficial y eliminará de sus registros locales las interacciones asociadas al identificador recibido.</p><h3>Plazo</h3><p>Responderemos dentro del plazo legal aplicable. La eliminación no afecta información que debamos conservar por obligación legal, seguridad o resolución de reclamaciones; dicha información quedará restringida mientras sea necesaria.</p>""",
    },
    "en": {
        "title": "Data access and deletion",
        "slug": "data-access-and-deletion",
        "content": """<h2>Data access and deletion</h2><p>You may request a copy, correction or deletion of personal data TVT holds about your interactions.</p><h3>Request by email</h3><p>Email <a href=\"mailto:prodsc.com@gmail.com?subject=TVT%20data%20request\">prodsc.com@gmail.com</a> with the subject <em>TVT data request</em>. Include your Instagram username and whether you request access, correction or deletion.</p><h3>Request through Meta or Instagram</h3><p>If you submit a deletion request through Meta or Instagram, TVT will process the request received through the official channel and erase local interaction records associated with the received identifier.</p><h3>Timeframe</h3><p>We will respond within the applicable legal timeframe. Deletion does not affect information that must be retained for legal obligations, security or claim resolution; it will be restricted while required.</p>""",
    },
    "ca": {
        "title": "Accés i eliminació de dades",
        "slug": "acces-i-eliminacio-de-dades",
        "content": """<h2>Accés i eliminació de dades</h2><p>Pots sol·licitar una còpia, correcció o eliminació de les dades personals que TVT conserva sobre les teves interaccions.</p><h3>Sol·licitud per correu</h3><p>Escriu a <a href=\"mailto:prodsc.com@gmail.com?subject=Sol%C2%B7licitud%20de%20dades%20TVT\">prodsc.com@gmail.com</a> amb l'assumpte <em>Sol·licitud de dades TVT</em>. Indica el teu nom d'usuari d'Instagram i si sol·licites accés, correcció o eliminació.</p><h3>Sol·licitud des de Meta o Instagram</h3><p>Si fas una sol·licitud d'eliminació des de Meta o Instagram, TVT processarà la sol·licitud rebuda pel canal oficial i eliminarà dels seus registres locals les interaccions associades a l'identificador rebut.</p><h3>Termini</h3><p>Respondrem dins del termini legal aplicable. L'eliminació no afecta informació que s'hagi de conservar per obligació legal, seguretat o resolució de reclamacions; quedarà restringida mentre sigui necessària.</p>""",
    },
}


class Command(BaseCommand):
    help = "Actualiza las páginas legales del CMS para Meta e Instagram."

    def _append_once(self, page_id, additions):
        page = Page.objects.get(pk=page_id)
        for language, appendix in additions.items():
            page.set_current_language(language)
            if "Instagram" not in page.content:
                page.content += appendix
                page.save()
        self.stdout.write(f"Página {page_id} actualizada.")

    def handle(self, *args, **options):
        self._append_once(3, PRIVACY_APPENDICES)
        self._append_once(5, TERMS_APPENDICES)

        author = get_user_model().objects.get(username="tvt")
        page = Page.objects.filter(translations__slug=DATA_PAGE["es"]["slug"]).first()
        if page is None:
            page = Page.objects.create(author=author, status="published", importance_order=90)
        for language, values in DATA_PAGE.items():
            page.set_current_language(language)
            page.title = values["title"]
            page.slug = values["slug"]
            page.content = values["content"]
            page.meta_title = values["title"]
            page.meta_description = values["content"].split("</h2>", 1)[1][:150]
            page.save()

        self.stdout.write(self.style.SUCCESS(f"Página de datos publicada: #{page.pk}"))
