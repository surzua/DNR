# Data Newsjacking Radar (DNR)

Sistema automatizado de inteligencia de tendencias diseñado para detectar noticias de alta tracción (políticas, económicas, deportivas o sociales) en Chile y evaluar de forma autónoma su viabilidad como proyectos rápidos de Data Science / Analytics.

## Arquitectura

- **Ingesta:** Feeds RSS de prensa chilena (EMOL, DF, La Tercera, BioBioChile), Reddit (`r/chile`, `r/republicadechile`) y Google Trends.
- **Deduplicación e Historial:** Lectura y persistencia en `data/history.json`.
- **Motor de Viabilidad LLM:** Gemini Flash con salida estructurada en Pydantic.
- **Despacho:** Notificaciones en Markdown a Telegram Bot.
- **Automatización:** GitHub Actions programado diariamente (07:30 CLT).

## Estructura del Proyecto

```text
├── .github/
│   └── workflows/
│       └── daily_radar.yml        # Cron workflow de GitHub Actions
├── config/
│   └── sources.yaml               # URLs de feeds RSS, subreddits y parámetros
├── data/
│   └── history.json               # Registro histórico de oportunidades analizadas
├── docs/
│   └── SYSTEM_SPEC.md             # Especificación del sistema
├── src/
│   ├── ingestion/                 # Módulos de ingesta (RSS, Reddit, Trends)
│   ├── analysis/                  # Evaluación de oportunidades y prompts
│   ├── storage/                   # Gestión de historial y deduplicación
│   └── notifiers/                 # Notificaciones a Telegram
├── main.py                        # Entrypoint de ejecución
├── pyproject.toml / requirements.txt
├── tests/                         # Suite de pruebas automatizadas (pytest)
└── README.md
```

## Configuración y Variables de Entorno

Copiar `.env.example` a `.env`:

```bash
cp .env.example .env
```

Variables requeridas:
- `GEMINI_API_KEY`: API Key obtenida en Google AI Studio.
- `TELEGRAM_BOT_TOKEN`: Token HTTP del bot generado con `@BotFather`.
- `TELEGRAM_CHAT_ID`: ID numérico del chat destinatario (obtenible vía `@userinfobot`).

## Instalación y Ejecución Local

```bash
# 1. Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar pipeline completo
python main.py
```

### Opciones de Ejecución CLI

El script `main.py` incluye banderas útiles para desarrollo y depuración:

- `python main.py --dry-run`: Simula el despacho a Telegram mostrando las tarjetas formateadas en consola sin enviarlas a la red.
- `python main.py --use-cache`: Carga las noticias desde el snapshot local `data/latest_articles.json` (ahorra tiempo y peticiones de red).
- `python main.py --skip-llm`: Ejecuta solo la fase de ingesta (RSS + Reddit) sin consumir cuota de Gemini.
- `python main.py --skip-telegram`: Evalúa las oportunidades y actualiza `history.json` omitiendo el envío a Telegram.

## Pruebas Automatizadas

El proyecto cuenta con una suite completa de pruebas unitarias y de integración:

```bash
pytest tests/
```

## Automatización con GitHub Actions

El flujo en `.github/workflows/daily_radar.yml` ejecuta el radar automáticamente todas las mañanas:

- **Programación:** Cron a las 10:30 UTC (07:30 AM CLT en verano / 06:30 AM CLT en invierno).
- **Ejecución Manual:** Pestaña *Actions > Daily Data Newsjacking Radar > Run workflow* (soporta opciones `dry_run` y `skip_llm`).
- **Persistencia:** Commitea y pushea automáticamente las nuevas oportunidades a `data/history.json` con `[skip ci]`.
- **Alertas de Fallo:** Si la ejecución en GitHub Actions falla, envía una alerta instantánea a Telegram con enlace al log.

### Configuración en GitHub:

1. **Secrets:** En el repositorio de GitHub, ir a `Settings > Secrets and variables > Actions > Repository secrets` y agregar:
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
2. **Permisos de Escritura:** En `Settings > Actions > General > Workflow permissions`, asegurarse de seleccionar **"Read and write permissions"** para permitir que el workflow actualice `data/history.json`.
