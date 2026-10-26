# Resumen del proyecto DNR

**Última revisión:** 25 de octubre de 2026  
**Nombre:** Data Newsjacking Radar (DNR)

## En una frase

DNR es un radar automatizado de noticias y conversación pública chilena que busca convertir temas de alta atención en ideas concretas, oportunas y técnicamente realizables de Data Science, Analytics y periodismo de datos.

## Propósito y valor

El sistema ayuda a detectar una historia mientras todavía existe una ventana de atención pública —idealmente dentro de 24 a 72 horas— y propone cómo aportar evidencia mediante datos. Su resultado esperado no es solo un resumen de noticias: es una oportunidad de análisis con un gancho claro, fuentes de datos posibles, un formato de entrega y un plan breve de ejecución.

El proyecto también funciona como una herramienta para desarrollar y mostrar capacidades profesionales en analítica aplicada: conecta actualidad, datos y una explicación que pueda resultar útil o interesante para una audiencia pública.

## Qué hace el flujo implementado

1. **Recolecta noticias y conversación pública** desde feeds RSS de medios chilenos y publicaciones de Reddit. La configuración actual incluye La Tercera, Diario Financiero, BioBioChile, Cooperativa y los subreddits `chile` y `republicadechile`.
2. **Normaliza y consolida** los elementos como registros tipados, filtra por antigüedad y elimina duplicados entre fuentes. En Reddit utiliza filtros de interacción y dispone de una alternativa RSS si falla el endpoint JSON.
3. **Evita repetir detonantes recientes** usando `data/history.json`, con comparación de títulos y URLs normalizados. El periodo predeterminado de enfriamiento es de dos días y puede cambiarse por CLI.
4. **Evalúa oportunidades con Gemini** mediante una respuesta estructurada y validada con Pydantic. Busca ángulos curiosos o contraintuitivos, fuentes de datos accesibles y planes de ejecución acotados.
5. **Aplica filtros deterministas**: viralidad mínima 7/10, factibilidad técnica mínima 6/10 y un máximo de tres oportunidades. Ordena por puntuación combinada y deduplica noticias detonantes.
6. **Guarda las oportunidades** en el historial y prepara un briefing y tarjetas de oportunidad para Telegram. El envío contempla formato HTML seguro, fallback a texto plano y modo de simulación.

## Qué entrega una oportunidad

- Tema y categoría.
- Por qué está generando interés.
- Gancho analítico o pregunta que el análisis podría responder.
- Formato recomendado: gráfico, app interactiva o análisis predictivo/optimización.
- Fuentes sugeridas y fricción estimada para obtenerlas.
- Puntajes de viralidad y viabilidad técnica.
- Estrategia de ejecución breve, pensada para un prototipo de menos de cuatro horas.
- Noticia detonante y enlace, cuando están disponibles.

## Arquitectura y operación

- **Python 3.11+**: pipeline CLI en `main.py`, dividido en ingesta, análisis, persistencia y notificaciones bajo `src/`.
- **Ingesta**: RSS y Reddit; `data/latest_articles.json` permite inspeccionar o reutilizar una captura local.
- **Evaluación**: Gemini mediante `google-genai`, con salida estructurada Pydantic y selección/fallback de modelos.
- **Persistencia**: `data/history.json`, guardado de forma atómica y con copia de resguardo ante corrupción.
- **Notificaciones**: Telegram Bot API.
- **Automatización**: el cron externo ejecuta diariamente el workflow de GitHub mediante `workflow_dispatch`. GitHub Actions recibe una ventana de días configurable, `dry_run` y la opción para omitir el LLM; luego hace commit del historial y puede avisar por Telegram si falla. El YAML no contiene un cron interno de GitHub: la programación diaria depende del servicio externo configurado para dispararlo.
- **CI**: otro workflow ejecuta `pytest` en pushes y pull requests hacia `main`.

## Estado confirmado al revisar el repositorio

- El núcleo funcional está implementado: ingesta RSS/Reddit, evaluación LLM, filtros, historial, Telegram, CLI y workflows de GitHub Actions.
- Hay defensas de seguridad en el flujo: tratamiento del contenido de noticias como entrada no confiable para el prompt, validación de URLs HTTP(S), límites de respuesta HTTP, redacción de credenciales en logs, validación de subreddits y persistencia atómica.
- Google Trends **no está integrado actualmente**: `src/ingestion/trends_client.py` contiene una función placeholder que lanza `NotImplementedError` y no es invocada por el orquestador de ingesta. Esto significa que el radar no consulta tendencias de búsqueda; actualmente analiza RSS y Reddit.
- El workflow actual no tiene un trigger `schedule` propio de GitHub, pero la ejecución diaria sí está cubierta por el cron externo que dispara `workflow_dispatch`. La documentación de programación externa debe leerse junto con el workflow vigente.
- `config/sources.yaml` declara `history_days_lookback: 2`, y el CLI también usa dos días como enfriamiento predeterminado. El README contiene referencias a siete días que no representan el valor predeterminado actual.

## Límites de lo que significa la salida

Las fuentes de datos, puntajes, ganchos y planes son propuestas generadas por un modelo a partir del material recolectado. No equivalen a una verificación de que cada dataset exista exactamente como se describe, de que la noticia siga siendo relevante o de que el análisis ya se haya construido. Antes de publicar una pieza, la oportunidad debe validarse contra la fuente primaria y los datos realmente disponibles.

## Referencias del repositorio

- `docs/STRATEGY_REVIEW.md`: diagnóstico y propuesta de ampliación hacia herramientas digitales útiles ligadas a noticias, con prioridades de evidencia, distribución, medición y fiabilidad. Es una propuesta de evolución; no describe cambios ya implementados.
- `README.md`: instalación, CLI y guía general de uso.
- `docs/SYSTEM_SPEC.md`: especificación de componentes y decisiones técnicas.
- `docs/SCHEDULING_OPTIONS.md`: configuración y alternativas de programación; el cron externo dispara el workflow vigente de GitHub Actions.
- `config/sources.yaml`: fuentes y umbrales de operación actuales.
- `main.py` y `src/`: comportamiento implementado del pipeline.
- `.github/workflows/daily_radar.yml`: configuración vigente de ejecución remota.
