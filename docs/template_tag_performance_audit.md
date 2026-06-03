# Auditoría Fase 1: template tags, lógica de negocio y caché

## Objetivo

Identificar qué template tags del proyecto concentran lógica de negocio, consultas y caché, y priorizar qué mover fuera de la capa de presentación en las siguientes fases.

## Resumen ejecutivo

La observación es válida: hoy el proyecto depende especialmente de `widgets` y `menus` para construir bloques complejos directamente desde template tags. Esto tiene tres efectos:

- mezcla render con acceso a datos y reglas de negocio
- dificulta pruebas unitarias finas y depuración
- limita escalabilidad al apoyarse en `LocMemCache`, que no se comparte entre procesos

El principal foco no está en todos los template tags, sino en unos pocos puntos de alta concentración:

1. `widgets/templatetags/widget_tags.py`
2. `menus/templatetags/menu_tags.py`
3. `categories/templatetags/category_tags.py`

Los demás tags son comparativamente ligeros.

## Estado actual del caché

Backend configurado:

- [tvt/settings.py](/home/tvt/MEGA/GIT/ART/TVT/tvt/settings.py:346)
- `django.core.cache.backends.locmem.LocMemCache`

Implicaciones:

- cada proceso mantiene su propio caché
- los invalidadores no garantizan coherencia entre workers
- un `cache hit` en un proceso puede no existir en otro
- la depuración de resultados inconsistentes se vuelve más difícil

## Inventario de template tags

### Alto impacto

#### `widgets/templatetags/widget_tags.py`

Responsabilidad original:

- obtiene `WidgetZone`
- recorre widgets
- construye keys de caché
- resuelve múltiples tipos de widget con `match/case`
- ejecuta consultas distintas por tipo
- hace `annotate`, `Count`, `Sum`, `Length`, `Q`, filtros por idioma y categoría
- adjunta datos derivados a objetos (`thumbnail_url`)
- cachea resultados finales por widget

Riesgos:

- archivo demasiado centralizado
- alta densidad de ramas de negocio
- difícil aislar por tipo de widget
- cambios pequeños pueden tener efectos laterales amplios
- complejidad alta para reproducir errores de datos o caché

Síntomas ya observados:

- duplicación de categorías por `join` de traducciones
- dependencia de invalidación por versión de cache key

Prioridad:

- `Muy alta`

#### `menus/templatetags/menu_tags.py`

Responsabilidad actual:

- obtiene menús por slug e idioma
- cachea estructuras completas de navegación
- aplica visibilidad por grupos después de leer caché
- construye children visibles
- resuelve menús dinámicos
- ejecuta lógica adicional para:
  - categorías de blog
  - páginas importantes
  - listas dinámicas de posts

Riesgos:

- mezcla navegación, permisos y contenido dinámico
- hace consultas dentro de helpers invocados desde render
- el cálculo de categorías visibles recorre árbol y consulta descendientes
- el caché guarda estructuras de menú con comportamiento derivado

Prioridad:

- `Muy alta`

### Impacto medio

#### `categories/templatetags/category_tags.py`

Responsabilidad actual:

- construye árbol completo de categorías por idioma
- cachea la lista completa
- depende de `SiteConfiguration` para timeout

Riesgos:

- carga todos los nodos del árbol en render
- sigue resolviendo árbol y timeout en capa de template
- aunque la key ya está centralizada, la construcción sigue cerca del render

Prioridad:

- `Media`

### Bajo impacto

#### `site_settings/templatetags/settings_tags.py`

Responsabilidad actual:

- acceso directo a `SiteConfiguration.get_solo()`
- acceso a `SiteTemplate.get_chosen()`

Riesgo:

- bajo, aunque sería mejor centralizar acceso si crece su uso

Prioridad:

- `Baja`

#### `accounts/templatetags/avatar_tags.py`

Responsabilidad actual:

- filtros de presentación
- fallback seguro para nombre y bio

Riesgo:

- bajo

Prioridad:

- `Baja`

#### `core/templatetags/*`

Responsabilidad actual:

- utilidades pequeñas de URL y filtros

Riesgo:

- bajo

Prioridad:

- `Baja`

## Hallazgos concretos

### 1. Concentración de lógica en template tags

Los tags de `widgets` y `menus` no solo adaptan datos para la plantilla: actúan como selectores, servicios de contenido, capa de permisos parcial y orquestadores de caché.

### 2. Caché distribuido por archivo, no por política central

Hay generación de keys y lecturas/escrituras de caché en varios puntos:

- `widgets/cache_keys.py`
- `menus/cache_keys.py`
- `categories/cache_keys.py`

Eso dificulta:

- auditar expiraciones
- versionar invalidaciones de forma homogénea
- trazar dependencias entre contenido y caché

### 3. Dependencia de `LocMemCache`

Hoy sirve para desarrollo y simplifica el arranque, pero no es una base sana para producción con varios procesos.

### 4. Observabilidad todavía básica

Ya existe logging de caché más uniforme, pero todavía faltan:

- métricas de queries por tag o selector
- medición por tipo de widget en tiempo de ejecución
- profiling sistemático por bloque

## Priorización de refactor

### Ola 1

- `widgets/templatetags/widget_tags.py`
- `menus/templatetags/menu_tags.py`

### Ola 2

- `categories/templatetags/category_tags.py`

### Ola 3

- `site_settings/templatetags/settings_tags.py`
- `accounts/templatetags/avatar_tags.py`
- `core/templatetags/*`

## Criterios de salida de la Fase 1

La Fase 1 se considera completa si:

- existe inventario de tags con lógica de datos
- hay priorización clara por impacto
- está identificado el backend de caché y su limitación actual
- queda definida la siguiente ola de extracción

## Recomendación para la Fase 2

Extraer primero `widgets` y `menus` a una capa de servicios/selectors:

- `widgets/services/` o `widgets/selectors.py`
- `menus/services/` o `menus/selectors.py`

Los template tags deberían quedar como adaptadores finos:

- leer contexto
- invocar servicio
- devolver estructura lista para render

## Avance actual de la Fase 2

### Hecho

- `widgets/templatetags/widget_tags.py` ya quedó reducido a adaptador fino.
- La lógica de construcción de datos y caché pasó a [widgets/selectors.py](/home/tvt/MEGA/GIT/ART/TVT/widgets/selectors.py:1).
- Se añadió una prueba para el caso de categorías duplicadas por traducciones en [widgets/tests.py](/home/tvt/MEGA/GIT/ART/TVT/widgets/tests.py:1).
- Se añadieron pruebas del selector por zona y del template tag fino para validar la nueva separación de capas.

### Siguiente frente

- `menus/templatetags/menu_tags.py`

## Avance actual de la Fase 3

### Hecho

- `widgets` ya tiene pruebas de selector, procesamiento por zona y template tag fino.
- la extracción de lógica desde el tag quedó protegida con tests en SQLite, alineados con CI.

## Avance actual de la Fase 4

### Hecho

- `widgets`, `menus` y `categories` ya usan helpers explícitos de cache keys.
- `categories` dejó de construir la key del árbol inline dentro del template tag.
- `widgets` y `menus` ya tienen iteradores de keys para invalidación por idioma.
- Se añadieron pruebas para:
  - invalidación de caché en `categories`
  - expansión de keys en `menus`
  - consistencia del flujo de caché en `widgets`

### Beneficio inmediato

- menos strings sueltos de keys repartidos por el código
- invalidación más consistente
- versionado de keys más localizable
- base más limpia para migrar luego a Redis u otro backend compartido

## Avance actual de la Fase 5

### Hecho

- el backend de caché ya quedó parametrizado por entorno en [tvt/settings.py](/home/tvt/MEGA/GIT/ART/TVT/tvt/settings.py:346)
- el comportamiento por defecto sigue siendo `LocMemCache`
- `.env.example` ya documenta:
  - `CACHE_BACKEND`
  - `CACHE_LOCATION`
  - `CACHE_TIMEOUT`

### Decisión actual

- no activar `Redis` todavía
- mantener `LocMemCache` hasta confirmar con el hosting si Redis está disponible
- dejar el cambio futuro reducido a variables de entorno, no a refactor adicional

## Avance actual de la Fase 6

### Hecho

- se añadió observabilidad específica de caché en:
  - [core/cache_observability.py](/home/tvt/MEGA/GIT/ART/TVT/core/cache_observability.py:1)
  - [widgets/selectors.py](/home/tvt/MEGA/GIT/ART/TVT/widgets/selectors.py:1)
  - [menus/templatetags/menu_tags.py](/home/tvt/MEGA/GIT/ART/TVT/menus/templatetags/menu_tags.py:1)
  - [categories/templatetags/category_tags.py](/home/tvt/MEGA/GIT/ART/TVT/categories/templatetags/category_tags.py:1)
- `settings.py` ahora registra en arranque:
  - backend de caché activo
  - ubicación/configuración base
  - timeout global por defecto
- se añadió `CACHE_LOG_LEVEL` para ajustar la verbosidad de los logs de caché por entorno

### Aclaración de configuración actual

Hoy el sistema de caché está dividido en dos capas:

- **Variables de entorno**
  - `CACHE_BACKEND`
  - `CACHE_LOCATION`
  - `CACHE_TIMEOUT`
  - `CACHE_LOG_LEVEL`

Estas controlan la infraestructura global del caché.

- **Modelos/configuración editorial**
  - `SiteConfiguration.menu_cache_timeout`
  - `SiteConfiguration.category_tree_cache_timeout`
  - `Widget.cache_timeout`

Estas controlan el tiempo funcional de caché por tipo de bloque.

## Comandos útiles para esta auditoría

```bash
find . -path '*/templatetags/*.py' | sort
rg -n "cache\\.|annotate\\(|prefetch_related\\(|select_related\\(|Count\\(|Sum\\(" . -g'*/templatetags/*.py' -g'*.py'
```
