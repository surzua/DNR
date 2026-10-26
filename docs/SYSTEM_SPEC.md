# DNR v0.2 — Especificación del sistema

## Propósito

DNR convierte señales públicas de Chile en propuestas de productos digitales que una persona pueda evaluar y construir manualmente. No crea repositorios de productos, no los despliega, no publica campañas ni mide su rendimiento.

El resultado es una oportunidad trazable: producto, audiencia, evidencia, motivo de difusión y brief de aprendizaje. La elección editorial final sigue siendo humana.

## Flujo técnico

1. `src/ingestion/` recolecta RSS y Reddit; opcionalmente agrega RSS público de Google Trends y eventos fechados configurados.
2. Cada `NewsArticle` conserva fuente, fecha de publicación/evento, primera detección, actualización si existe, tipo y límites de señal. La agrupación de cobertura anota medios relacionados sin borrar sus artículos.
3. `src/analysis/prompt_templates.py` entrega contexto temporal y procedencia a Gemini, con el contenido de noticias delimitado como no confiable.
4. `src/analysis/opportunity_eval.py` valida la salida Pydantic, traza el detonante a la ingesta y filtra/ordena oportunidades. La deduplicación se basa en detonante + producto + necesidad, por lo que alternativas sustanciales para un mismo evento permanecen posibles.
5. `src/analysis/source_verification.py` hace una comprobación HTTP acotada y segura. Sus resultados son técnicos, no editoriales.
6. `src/storage/history_manager.py` persiste oportunidades y descartes de forma atómica y compatible con registros antiguos.
7. `src/notifiers/telegram_bot.py` entrega un resumen privado, escapado para HTML y con fallback de texto plano.

## Contrato principal

`Opportunity` separa los siguientes conceptos:

- `product_type`, `suggested_deliverable` y `implementation_options`: qué es, cómo se entrega y con qué podría construirse.
- `reported_facts`, `corroborated_facts`, `assumptions`, `hypotheses_to_test` y `critical_claims`: niveles de certeza distintos.
- `evidence_status`: `Pendiente de revisión`, `Respaldo parcial` o `Lista para construir`. Los valores históricos se aceptan para lectura, pero no se generan desde una comprobación HTTP.
- `share_with`, `share_purpose`, `share_mechanism` y `shareable_artifact`: circuito concreto de difusión.
- `scope_class`, `minimum_version`, `explicit_limits`, `learning_skill`, dificultades separadas y `validation_cases`: brief para construir y aprender.

`DataSource` admite datos, reglas/reglamentos, documentación, mecánicas reproducibles y fuentes editoriales. `verification_status="accessible"` significa únicamente que la URL respondió con contenido admisible; `editorial_status` y sus respaldos se completan tras revisión humana.

## Configuración

`config/sources.yaml` define fuentes, límites y `pipeline`:

- `verify_source_urls`: activa el registro de disponibilidad HTTP.
- `require_accessible_source`: gate opcional, desactivado por defecto. Si se usa, exige acceso técnico pero no prueba evidencia editorial.
- `trends.enabled`: activa el RSS público de Trends para Chile. Fallos parciales solo generan warning.
- `scheduled_events`: eventos previsibles con título, fecha ISO y fuente.

## Garantías y límites

- Como máximo se proponen tres oportunidades por corrida; también puede haber ninguna.
- El detonante de una propuesta debe coincidir exactamente con una señal ingerida.
- No se siguen redirecciones ni se permiten hosts privados al comprobar fuentes.
- Un acceso bloqueado es incertidumbre, no falsedad. Una afirmación contradicha no se promueve como oportunidad lista para construir.
- Las pruebas automatizadas cubren contrato, persistencia, seguridad, notificación, ingesta y casos de revisión. No demuestran calidad editorial ni viralidad real.
