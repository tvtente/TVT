# Mapa de Base de Datos TVT

## Visión general

La base de datos de TVT es relacional y está organizada por módulos. No existe una tabla única de contenidos: cada dominio funcional tiene sus entidades, relaciones y, en algunos casos, tablas de traducción separadas.

## Motor y esquema

Entorno validado:

- motor: MySQL/MariaDB
- esquema: `tvtavata_tvt`
- host: `192.168.0.14`
- puerto: `3306`

Desarrollo local:

- SQLite en `db.sqlite3`

## Familias de tablas

### Sistema y autenticación

- `auth_user`
- `auth_group`
- `auth_permission`
- `django_content_type`
- `django_admin_log`
- `django_session`
- `django_site`

### Allauth

- `account_emailaddress`
- `account_emailconfirmation`
- `socialaccount_socialaccount`
- `socialaccount_socialapp`
- `socialaccount_socialtoken`

### Cuentas y perfil profesional

- `accounts_profile`
- `accounts_profileeducation`
- `accounts_profileexperience`
- `accounts_profilecertification`
- `accounts_profilelanguage`
- `accounts_profileskill`
- `accounts_profilecompetency`
- `accounts_profilelink`
- `accounts_profileexternalpublication`

Catálogos auxiliares:

- `accounts_profilelanguagelevel`
- `accounts_profileskilllevel`
- `accounts_profilecompetencylevel`
- `accounts_profileskilltype`
- `accounts_profilecompetencytype`
- `accounts_profilelinktype`
- `accounts_profileexternalpublicationtype`
- `accounts_profileexperiencetype`
- `accounts_profileeducationtype`
- `accounts_profilecertificationtype`

### Contenido principal

- `pages_page`
- `pages_homesection`
- `posts_post`
- `posts_post_translation`
- `posts_postdailymetric`
- `publications_publication`
- `publications_publication_translation`
- `books_book`
- `books_book_translation`

### Taxonomía y clasificación

- `categories_category`
- `tags_tag`
- `tags_tag_translation`
- `tags_taggedpost`
- `tags_tagdailymetric`

### Interacción

- `comments_comment`
- `contact_contactmessage`

### Recursos visuales

- `gallery_image`
- `gallery_stagedupload`

### Estructura de frontend

- `menus_menu`
- `menus_menuitem`
- `widgets_widgetzone`
- `widgets_widget`
- `site_settings_siteconfiguration`
- `site_settings_templates`
- `testimonials_testimonial`
- `testimonials_testimonial_translation`

## Entidades y claves funcionales

### `auth_user`

Entidad base de identidad.

Relaciones:

- 1:1 con `accounts_profile`
- 1:N con posts como autor
- N:M con publications como autor
- N:M con books como autor
- 1:N con comentarios

### `accounts_profile`

Extiende el usuario con datos públicos y profesionales.

Campos funcionales destacados:

- nombre visible
- email público
- website
- cargo profesional
- institución
- ORCID
- flags `is_researcher`, `is_contributor`
- avatar
- visibilidad pública
- confianza para comentarios

### `pages_page`

Entidad de página estable.

Relaciones:

- N:1 con `auth_user` como autor
- N:M con `categories_category`
- N:1 opcional con `gallery_image` en varios campos asset por idioma

### `pages_homesection`

Secciones internas para home o portadas configurables.

Relaciones:

- N:1 con `widgets_widgetzone`

### `posts_post`

Entidad central del blog.

Relaciones:

- N:1 con `auth_user`
- N:M con `categories_category`
- N:M con `tags_tag` vía `tags_taggedpost`
- 1:N con `comments_comment`
- 1:N con `posts_postdailymetric`
- N:1 opcional con `gallery_image` en assets traducibles

### `posts_post_translation`

Tabla Parler de traducciones del post.

Contiene:

- título
- slug
- summary
- content
- meta SEO
- featured/social image asset

### `posts_postdailymetric`

Métrica diaria de vistas por post.

Clave lógica:

- `unique_together(post, date)`

### `publications_publication`

Entidad de publicación científica.

Relaciones:

- N:M con `auth_user`
- N:M con `categories_category`

Campos destacados:

- DOI
- attachment PDF
- fecha
- publicado sí/no

### `publications_publication_translation`

Contiene:

- título
- slug
- abstract
- secciones científicas
- SEO
- image assets

### `books_book`

Entidad editorial de libro.

Relaciones:

- N:M con `auth_user`
- N:M con `categories_category`

Campos destacados:

- ISBN
- fecha de publicación
- precio
- moneda
- preview PDF
- full PDF
- allow_free_preview
- requires_purchase

### `books_book_translation`

Contiene:

- title
- slug
- subtitle
- description
- excerpt
- table_of_contents
- meta_title
- meta_description
- cover_image_asset
- social_image_asset

### `categories_category`

Taxonomía universal.

Patrón:

- árbol jerárquico con `parent`
- campos SEO
- tabla base + tabla de traducciones con `parler`

Sirve para:

- páginas
- posts
- publications
- books

### `tags_tag`

Etiquetas multilingües.

Patrón:

- slug global
- etiqueta traducida
- contador de clics

### `tags_taggedpost`

Tabla intermedia entre post y tag.

Añade:

- idioma
- score de relevancia
- fecha de asignación

Clave lógica:

- `unique_together(post, tag, language)`

### `comments_comment`

Comentarios en árbol.

Relaciones:

- N:1 con `posts_post`
- N:1 con `auth_user`, opcional
- auto-relación `parent`

Campos destacados:

- autor invitado o autenticado
- contenido
- idioma original
- contenido traducido opcional
- aprobado sí/no

### `gallery_image`

Media library compartida.

Patrón:

- una fila por versión/idioma
- slug único
- archivo físico asociado
- fila opcional `derived_from`

Consumida por:

- pages
- posts
- publications
- books

### `gallery_stagedupload`

Subida temporal previa a convertirla en imagen final del catálogo.

Uso:

- picker de media en admin

### `menus_menu` y `menus_menuitem`

Estructura de navegación.

Patrón:

- un menú tiene muchos items
- cada item puede tener hijos
- cada item puede limitarse por grupos de usuario

### `widgets_widgetzone` y `widgets_widget`

Renderizado de bloques dinámicos.

Patrón:

- una zona tiene muchos widgets
- un widget puede filtrar por categoría
- un widget puede cachearse

### `site_settings_siteconfiguration`

Singleton de comportamiento operacional.

No modela contenido editorial; modela reglas y parámetros.

### `site_settings_templates`

Configura branding y theme.

Campos destacados:

- logo
- favicon
- eslogan
- banner
- colores
- tamaños y proporciones

## Patrones transversales

### Traducción por columnas

Aplicada a:

- pages
- categories
- menus
- widgets
- site settings
- catálogos de accounts

### Traducción por tablas

Aplicada a:

- posts
- publications
- books
- tags
- testimonials

### Árboles jerárquicos

Aplicados a:

- categories
- comments
- menu items

### Assets reutilizables

Patrón:

- varios módulos referencian `gallery_image` en lugar de subir ficheros aislados por cada modelo

## Relaciones de mayor impacto

- `auth_user` -> `accounts_profile`
- `posts_post` -> `comments_comment`
- `posts_post` -> `tags_taggedpost` -> `tags_tag`
- `posts_post` <-> `categories_category`
- `publications_publication` <-> `auth_user`
- `books_book` <-> `auth_user`
- `books_book` <-> `categories_category`
- `pages_homesection` -> `widgets_widgetzone`
- `widgets_widget` -> `categories_category`
- `menus_menuitem` -> `auth_group`

## Observaciones para mantenimiento

- El proyecto usa `parler` como estrategia única para contenido multilingüe en base de datos.
- Los assets editoriales se centralizan en `gallery_image`, así que errores allí impactan varios módulos.
- Menús, widgets y categorías tienen estructura jerárquica y afectan a navegación y layout.
- La app `books` ya está integrada y migrada como dominio independiente.
