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
└── README.md
```

## Configuración y Variables de Entorno

Copiar `.env.example` a `.env`:

```bash
cp .env.example .env
```

Configurar:
- `GEMINI_API_KEY`: API Key de Google AI Studio.
- `TELEGRAM_BOT_TOKEN`: Token de bot de Telegram (@BotFather).
- `TELEGRAM_CHAT_ID`: ID del chat de destino.

## Instalación y Ejecución

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
