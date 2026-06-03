# Plan de Convergencia Multilingüe

## Objetivo

Converger todo el proyecto hacia una sola estrategia de traducción:

- `django-parler` como estándar único

Se abandona progresivamente `django-modeltranslation` para reducir:

- deuda técnica
- complejidad de mantenimiento
- carga cognitiva del equipo
- inconsistencias editoriales
- riesgo en migraciones futuras

## Decisión de Fase 1

La decisión arquitectónica para este repositorio es:

1. No introducir nuevos modelos traducibles con `django-modeltranslation`.
2. Considerar `django-parler` como única estrategia objetivo.
3. Ejecutar la migración por olas de apps, no en un cambio masivo.
4. Aprovechar que no hay datos de producción para simplificar migraciones de datos.

## Inventario actual

### Ya usan `django-parler`

- `accounts`
- `books`
- `categories`
- `menus`
- `pages`
- `posts`
- `publications`
- `site_settings`
- `widgets`

## Orden de migración recomendado

### Ola 1

- `categories`
- `menus`
- `widgets`
- `pages`

### Ola 2

- `site_settings`

### Ola 3

- `accounts`

### Ola 4

- retirada definitiva de `modeltranslation`

## Estado actual

La convergencia funcional del repositorio quedó completada:

- todas las apps multilingües activas usan `django-parler`
- `modeltranslation` fue retirado de `INSTALLED_APPS`
- las referencias de runtime a `translation.py` desaparecieron
- la lógica de disponibilidad por idioma ya depende de traducciones reales

## Criterios por modelo

### Deben ser traducibles

- títulos
- slugs públicos por idioma
- excerpts
- descriptions
- labels editoriales visibles
- textos del CV y perfil público
- contenido rico visible al usuario

### No deben ser traducibles

- precios
- moneda
- fechas
- estados
- flags booleanos
- relaciones técnicas
- permisos
- campos de control interno

## Regla editorial

Una traducción se considera existente solo si existe la fila de traducción real
en ese idioma.

Consecuencias:

- la disponibilidad por idioma deja de depender de fallback implícito
- el sistema puede mostrar con claridad cuándo un contenido no existe en un idioma
- los formularios pueden trabajar sobre valores reales del idioma activo

## Fase 1 completada cuando

- el estándar único está decidido
- el orden de migración está aprobado
- el equipo deja de crear nuevas traducciones con `modeltranslation`
- existe documentación base de convergencia

## Criterios de entrada a Fase 2

Antes de empezar la primera migración real:

1. elegir la primera app de la ola 1
2. identificar exactamente sus campos traducibles
3. definir la política de fallback esperada
4. definir qué pruebas funcionales se ejecutarán al terminar esa app

## Primera app recomendada

La primera app recomendada para Fase 2 es:

- `categories`

Razones:

- bajo riesgo
- modelo simple
- alta visibilidad
- buen módulo para fijar patrón de migración

## Riesgos conocidos

- `accounts` será la app más delicada
- `site_settings` mezcla configuración técnica con textos visibles
- habrá que revisar slugs y cambio de idioma en `pages`, `menus` y `categories`
- los tests actuales no cubren todavía toda la semántica multilingüe objetivo

## Resultado esperado

Al finalizar la convergencia:

- una sola estrategia de traducción
- semántica consistente entre apps
- menor complejidad en admin y formularios
- menos riesgo en mantenimiento futuro
- mayor claridad para editores y desarrolladores
