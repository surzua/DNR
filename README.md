# 📡 Data Newsjacking Radar (DNR) · v0.2

[![CI Tests](https://github.com/surzua/DNR/actions/workflows/ci.yml/badge.svg)](https://github.com/surzua/DNR/actions/workflows/ci.yml)
[![Daily Radar](https://github.com/surzua/DNR/actions/workflows/daily_radar.yml/badge.svg)](https://github.com/surzua/DNR/actions/workflows/daily_radar.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![LLM](https://img.shields.io/badge/LLM-Gemini%20Flash-orange.svg)
![Alerts](https://img.shields.io/badge/Alerts-Telegram-0088cc.svg)

DNR observa noticias y señales públicas, inicialmente en Chile, para proponer productos digitales que alguien pueda querer usar, entender, resolver o experimentar a raíz de un evento. Convierte la señal en un brief para decisión humana; no construye ni publica productos de forma autónoma.

Una propuesta puede ser una calculadora, comparador, guía, planificador, simulador, explicador, juego/desafío, utilidad local para archivos, recurso descargable o experiencia creativa. Data Science y Streamlit siguen disponibles cuando sirven, pero ya no son una restricción del radar.

## Qué entrega una oportunidad

- Audiencia, necesidad, primera interacción, producto, entradas y resultado.
- Motivo concreto de difusión: quién compartiría qué, con quién y para qué.
- Evidencia separada entre lo que la noticia reporta, hechos contrastados, supuestos e hipótesis.
- Estado editorial (`Pendiente de revisión`, `Respaldo parcial`, `Lista para construir`) independiente del acceso HTTP de una URL.
- Brief de construcción: alcance mínimo, límites, habilidad a practicar, dificultad técnica y de comprobación, dependencias y casos de validación.

La selección final, la investigación editorial, el diseño, desarrollo, despliegue y publicación pertenecen al creador.

## Flujo

```text
RSS + Reddit + eventos fechados + Trends opcional
                    │
                    ▼
  Contexto con fuente, publicación, detección y límites de señal
                    │
                    ▼
  Evaluación estructurada: producto, evidencia, difusión y aprendizaje
                    │
                    ▼
  Filtros deterministas y deduplicación por producto + necesidad
                    │
                    ▼
  Historial trazable + resumen privado por Telegram
```

Las señales de Reddit, Trends y cobertura repetida no se equiparan entre sí: cada una conserva procedencia y limitaciones. Google Trends usa su RSS público de Chile solo si se activa explícitamente en `config/sources.yaml`; una falla no interrumpe la ingesta principal. Los eventos previsibles se agregan manualmente como `scheduled_events` con fecha y fuente.

## Evidencia honesta

Una respuesta HTTP satisfactoria se guarda como `accessible`: significa solamente “URL accesible; contenido pendiente de revisión editorial”. No confirma que el contenido sea pertinente, actual, correcto o que respalde una conclusión. Las fuentes pueden registrar afirmaciones respaldadas, ubicación revisada, vigencia y comprobaciones pendientes. Un bloqueo de acceso es incertidumbre, no falsedad.

Las ideas con evidencia incompleta pueden quedar como prometedoras pero pendientes; no se presentan como listas para construir. Los casos de regresión documentados están en [docs/REVIEW_CASES.md](docs/REVIEW_CASES.md).

## Instalación y uso

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Configura `NVIDIA_API_KEY` o `GEMINI_API_KEY` para evaluar oportunidades. `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` solo son necesarios para el envío real.

Si configuras `NVIDIA_API_KEY`, el radar consulta NVIDIA NIM primero, exige resultados mediante JSON Schema y valida la respuesta localmente. Reintenta una vez ante una respuesta inválida, un timeout o un error HTTP transitorio; los errores permanentes como 401 pasan directamente al respaldo. Por defecto usa `meta/llama-3.3-70b-instruct`; puedes cambiarlo con `NVIDIA_MODEL` por un modelo que admita salida estructurada en tu cuenta. Si NVIDIA falla, prueba los modelos Gemini configurados, validando cada respuesta antes de aceptarla. Cada petición tiene un timeout de 60 segundos y Gemini no multiplica los intentos dentro del SDK. Si todos fallan, la ejecución informa el error; no lo presenta como un día sin oportunidades.

Para GitHub Actions, agrega la clave como secreto del repositorio llamado `NVIDIA_API_KEY` en **Settings → Secrets and variables → Actions → New repository secret**. Opcionalmente, crea una variable de repositorio `NVIDIA_MODEL` en la pestaña **Variables**. La clave local en `.env` no se transfiere a GitHub. Los cambios del workflow deben estar en GitHub para que Actions los use.

```bash
# Recolectar fuentes sin usar el modelo ni modificar historial
python main.py --skip-llm

# Ejecutar evaluación y mostrar el despacho sin enviar ni persistir
python main.py --dry-run

# Reutilizar el snapshot local de artículos
python main.py --use-cache --dry-run

# Omitir Telegram y persistir solo el historial de la corrida
python main.py --skip-telegram

# Ejecutar pruebas deterministas
pytest -q
```

## Configuración de señales

`config/sources.yaml` contiene feeds RSS, subreddits, umbrales y estas opciones:

- `verify_source_urls`: registra acceso técnico acotado a URLs.
- `require_accessible_source`: opcional y desactivado por defecto; si se activa, descarta propuestas sin URL accesible, pero no las marca como revisadas editorialmente.
- `trends.enabled`: activa el RSS público de Google Trends para Chile después de comprobar su disponibilidad en el entorno.
- `scheduled_events`: lista manual de eventos con `title`, `date` ISO y `source_url`.

El historial es compatible con registros previos: los campos nuevos tienen defaults conservadores y nunca reclasifican una evidencia antigua como revisada.

## Automatización

GitHub Actions ejecuta el radar diariamente y puede persistir el historial. La ejecución se serializa para evitar solapamientos. No hay cuotas de alerta: pueden existir hasta tres propuestas, una o ninguna. Las alertas de Telegram son privadas y no publican contenido ni miden su rendimiento.

Ante una falla, Actions conserva durante 7 días el snapshot de noticias como artefacto `radar-input-<run_id>` para reproducir el caso. Las ejecuciones con `dry_run=true` evalúan con las APIs reales, simulan Telegram y omiten tanto la persistencia como las notificaciones de error a Telegram.

## Estructura

```text
src/analysis/      # Contrato, prompt, selección y evidencia
src/ingestion/     # RSS, Reddit, Trends opcional y eventos fechados
src/storage/       # Historial y snapshot compatibles
src/notifiers/     # Tarjeta privada de Telegram
tests/             # Pruebas unitarias, integración y casos de revisión
docs/              # Especificación, roadmap y casos revisados
```

Consulta [docs/STRATEGY_REVIEW.md](docs/STRATEGY_REVIEW.md) para la estrategia, límites y criterios completos de DNR v0.2.
