# Sistema Funcional TVT

## Propósito

TVT es una plataforma editorial multilingüe construida como CMS. Su objetivo es permitir que el equipo publique, organice y mantenga contenido web sin depender de cambios de código para la operativa diaria.

El sistema cubre estas necesidades principales:

- publicar páginas estables
- publicar artículos de blog
- publicar publicaciones científicas
- publicar libros editoriales
- gestionar perfiles públicos de usuarios
- mostrar menús y bloques dinámicos
- recibir mensajes de contacto
- operar una web en varios idiomas

## Qué puede hacer un usuario visitante

Un visitante puede:

- navegar por la portada y las páginas informativas
- leer artículos del blog
- leer publicaciones científicas
- consultar libros y abrir sus previews PDF si están habilitados
- navegar por categorías y etiquetas
- usar el buscador
- ver perfiles públicos
- ver testimonios y galería
- enviar mensajes por el formulario de contacto
- comentar en posts, si el flujo público y la moderación lo permiten

## Qué puede hacer un usuario registrado

Un usuario autenticado puede:

- iniciar sesión con cuenta local o, si está configurado, con Google
- mantener su perfil
- completar datos profesionales
- aparecer en el directorio público si su perfil está marcado como visible
- comentar con identidad propia

## Qué puede hacer el equipo editorial

Según rol y permisos, el equipo puede:

- crear y editar páginas
- crear y editar posts
- crear y editar publicaciones
- crear y editar libros
- gestionar categorías
- gestionar galería e imágenes reutilizables
- gestionar testimonios
- crear menús públicos y privados
- configurar widgets y zonas de widgets
- moderar comentarios
- revisar mensajes de contacto
- ajustar branding y configuración global del sitio

## Tipos de contenido

### Páginas

Las páginas sirven para contenido estable o institucional.

Ejemplos:

- quiénes somos
- contacto
- avisos legales
- landing pages
- portada principal

Además, una página puede actuar como homepage si se marca como tal.

### Posts

Los posts son el motor del blog.

Tienen:

- autor
- fecha de publicación
- estado borrador/publicado
- categorías
- tags
- resumen SEO/social
- imágenes de portada y social
- contador de vistas

Los comentarios se asocian a posts.

### Publications

Las publicaciones son documentos científicos o académicos de estructura más formal.

Incluyen:

- autores múltiples
- categorías
- DOI
- resumen
- secciones científicas estructuradas
- PDF completo

### Books

Los libros son un módulo editorial propio, separado de posts y publications.

Incluyen:

- título y subtítulo
- excerpt
- descripción
- índice
- portada
- imagen social
- autores múltiples
- categorías
- ISBN
- precio y moneda
- PDF preview
- PDF completo
- flags de preview libre o compra requerida

## Multidioma

El sistema trabaja en:

- español
- inglés
- catalán

Comportamiento funcional:

- el visitante cambia de idioma desde el selector
- si existe traducción, el sistema abre la URL equivalente
- si no existe, el sistema muestra una página amable indicando que ese contenido aún no está disponible en ese idioma

## Navegación

La navegación no está hardcodeada en frontend. Se gestiona desde administración.

Esto permite:

- construir menús públicos
- crear menús privados por roles
- anidar opciones en árbol
- enlazar URLs manuales, páginas, categorías o listados dinámicos

## Widgets

Los widgets son bloques configurables que pueden poblar zonas de la web.

Ejemplos:

- posts recientes
- posts más vistos
- posts más comentados
- grids por intención editorial
- carruseles
- directorio de usuarios
- testimonios
- categorías del blog

## Comentarios

Los comentarios:

- pertenecen a posts
- soportan respuestas anidadas
- pueden moderarse
- pueden aprobarse automáticamente según configuración o confianza del usuario

## Perfiles públicos

Cada usuario puede tener un perfil ampliado con:

- nombre visible
- bio
- avatar
- cargo profesional
- institución
- ciudad y país
- ORCID
- áreas de interés
- educación
- experiencia
- certificaciones
- idiomas
- skills
- competencias
- enlaces externos
- publicaciones externas

## Contacto

El sitio incluye un formulario de contacto cuyos mensajes entran a una bandeja administrativa con:

- prioridad
- estado leído/no leído
- fecha de respuesta
- usuario responsable

## Branding y operación diaria

El equipo puede cambiar sin programar:

- logo
- favicon
- eslogan
- colores base
- banner superior
- proporciones del layout
- textos de copyright
- paginaciones
- parámetros de caché
- ajustes de moderación

## Resumen operativo

TVT funciona como una plataforma editorial configurable donde contenido, navegación, bloques visuales y parte del diseño viven en base de datos y se administran desde Django Admin.

