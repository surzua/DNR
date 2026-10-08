# 📡 Data Newsjacking Radar (DNR)

[![CI Tests](https://github.com/surzua/DNR/actions/workflows/ci.yml/badge.svg)](https://github.com/surzua/DNR/actions/workflows/ci.yml)
[![Daily Radar](https://github.com/surzua/DNR/actions/workflows/daily_radar.yml/badge.svg)](https://github.com/surzua/DNR/actions/workflows/daily_radar.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![Tests](https://img.shields.io/badge/tests-42%20passed-brightgreen.svg)
![LLM](https://img.shields.io/badge/LLM-Gemini%20Flash-orange.svg)
![Alerts](https://img.shields.io/badge/Alerts-Telegram-0088cc.svg)

Sistema autónomo de inteligencia de tendencias diseñado para detectar noticias de alta tracción y viralidad en Chile (políticas, económicas, regulatorias y sociales), evaluando de forma automática su viabilidad como proyectos rápidos de **Data Science, Analytics y Periodismo de Datos**.

El objetivo es aprovechar la ventana dorada de atención pública (**24 a 72 horas**) publicando análisis cuantitativos, visualizaciones interactivas o simuladores que aporten evidencia empírica y contrasten narrativas públicas.

---

## 🧭 ¿Cómo Funciona?

Cada día a las **11:37 AM CLT** (14:37 UTC), el radar se ejecuta de forma desatendida mediante **GitHub Actions** en horario de baja demanda global, completando el siguiente pipeline:

```text
  [ Cron Diario 11:37 CLT / Manual ]
                  │
                  ▼
   ┌──────────────────────────────┐
   │ 1. Ingesta Multicanal        │ ◄── Feeds RSS (BioBío, La Tercera, DF, EMOL)
   │    y Detección de Pulso      │ ◄── Reddit Público (r/chile, r/republicadechile)
   └──────────────┬───────────────┘
                  │ Raw Articles & Threads (+100 noticias)
                  ▼
   ┌──────────────────────────────┐
   │ 2. Deduplicación Semántica   │ ◄── Historial data/history.json (últimos 7 días)
   │    y Filtrado de Novedad     │ ─── Descarta tópicos analizados previamente
   └──────────────┬───────────────┘
                  │ Temas Emergentes no Explorados
                  ▼
   ┌──────────────────────────────┐
   │ 3. Motor de Viabilidad LLM   │ ◄── Gemini Flash (Salida estructurada Pydantic)
   │    (Ganchos & Estrategia)    │ ─── Exige fuentes públicas (APIs, CMF, INE, Wikipedia)
   └──────────────┬───────────────┘
                  │ Top Oportunidades (Viralidad >= 7, Viabilidad >= 6)
                  ▼
   ┌──────────────────────────────┐
   │ 4. Despacho & Persistencia   │ ──► Alerta estructurada a Telegram Bot
   │                              │ ──► Auto-commit y push a data/history.json
   └──────────────────────────────┘
```

---

## 📱 Ejemplo Real de Alerta en Telegram

Cada mañana recibes un briefing ejecutivo con un máximo de 3 tarjetas de oportunidad priorizadas, con formato HTML limpio y enlaces de 1-clic:

```text
🚀 OPORTUNIDAD DE DATA DETECTADA (Score: 8.5/10)

📌 Tema: El Umbral del Apagón: Con cuántos mm de lluvia colapsa la red comunal
📂 Categoría: Sociedad & Tendencias

🎯 Gancho Cognitivo:
Al correlacionar milímetros de agua con clientes sin luz se evidencia que 
comunas de menores recursos sufren cortes masivos con apenas 10 mm de lluvia, 
mientras comunas del sector oriente toleran más de 40 mm sin interrupciones críticas.

📊 Fuentes de Datos Sugeridas:
• Superintendencia de Electricidad y Combustibles (SEC) (Portal Abierto | Fricción: Baja)
  ↳ https://www.sec.cl/interrupciones-en-linea/
• Dirección Meteorológica de Chile (DMC) (API Pública | Fricción: Baja)
  ↳ https://climatologia.meteochile.gob.cl/application/estaciones/datosDescarga/estaciones

⏱️ Entregable: Gráfico Estático de Alto Impacto
🛠️ Plan Rápido (< 4 horas):
1. Extraer registros comunales de clientes afectados reportados por la SEC (48h).
2. Cruzar con precipitaciones acumuladas por estación de la DMC.
3. Graficar scatter plot y mapa coroplético del 'Índice de Fragilidad Eléctrica'.

📰 Noticia Detonante: Lluvia causa estragos en la RM: miles de clientes sin luz
```

---

## 🧠 Criterios de Evaluación del Motor LLM

El motor analítico ([src/analysis/opportunity_eval.py](src/analysis/opportunity_eval.py)) evalúa los artículos basándose en directrices estrictas:

1. **Ganchos Contraintuitivos o Curiosos:** Descarta resúmenes descriptivos tradicionales. Prioriza ángulos del tipo: *"Todo el mundo dice X, pero los datos históricos muestran Y"* o calculadoras de impacto personal (*"¿Cuánto te cuesta a ti la nueva regulación?"*).
2. **Fuentes Abiertas de Baja Fricción:** Identifica fuentes reales accesibles en horas: portales de transparencia, CMF, Banco Central, tablas históricas de Wikipedia, datos del INE o scraping ligero.
3. **Filtro de Umbral Exigente:** Solo califica si `virality_score >= 7` y `technical_feasibility_score >= 6`. Si no hay temas relevantes un día, despacha una notificación de tranquilidad sin generar spam.
4. **Plan Rápido de Ejecución:** Cada tarjeta entrega un roadmap táctico de 3 pasos accionables en menos de 4 horas.

---

## 📂 Estructura del Repositorio

```text
DNR/
├── .github/
│   └── workflows/
│       ├── daily_radar.yml        # Orquestación matutina (07:23 CLT) + alertas de fallo
│       └── ci.yml                 # CI automático con pytest en cada push/PR
├── config/
│   └── sources.yaml               # Catálogo de feeds RSS, subreddits y parámetros
├── data/
│   ├── history.json               # Base histórica de oportunidades y deduplicación
│   └── latest_articles.json       # Cache local de última recolección (ignorado en Git)
├── docs/
│   └── SYSTEM_SPEC.md             # Especificación técnica y arquitectura completa
├── src/
│   ├── analysis/                  # Evaluación LLM con Gemini y schemas Pydantic
│   ├── ingestion/                 # Parsers RSS multicanal y cliente ligero de Reddit
│   ├── models/                    # Modelos de datos fuertemente tipados
│   ├── notifiers/                 # Despachador seguro de Telegram (HTML + fallback)
│   └── storage/                   # Persistencia, control de duplicados y rotación
├── tests/                         # Batería de 42 pruebas unitarias y de integración
├── main.py                        # Entrypoint CLI del pipeline
├── pyproject.toml / requirements.txt
└── README.md
```

---

## ⚙️ Configuración y Variables de Entorno

Crea un archivo local `.env` a partir de la plantilla:

```bash
cp .env.example .env
```

Define las siguientes credenciales:

| Variable | Descripción | ¿Dónde obtenerla? |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Llave de API para Gemini Flash | Gratis en [Google AI Studio](https://aistudio.google.com/) |
| `TELEGRAM_BOT_TOKEN` | Token de acceso del Bot | Chat con [@BotFather](https://t.me/BotFather) en Telegram |
| `TELEGRAM_CHAT_ID` | Tu ID de usuario de Telegram | Reenviando un mensaje a [@userinfobot](https://t.me/userinfobot) |

---

## 🚀 Instalación y Uso Local

```bash
# 1. Crear y activar entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar el radar completo
python main.py
```

### Banderas de la Interfaz de Línea de Comandos (CLI)

```bash
# Simular el despacho mostrando el mensaje formateado en consola sin enviar a Telegram
python main.py --dry-run

# Reutilizar el snapshot local de noticias para no hacer scraping de red nuevamente
python main.py --use-cache

# Probar únicamente la recolección de noticias sin consumir tokens de Gemini
python main.py --skip-llm

# Evaluar oportunidades y actualizar data/history.json sin enviar a Telegram
python main.py --skip-telegram
```

---

## 🧪 Pruebas Automatizadas

El proyecto incluye 42 pruebas unitarias y de integración que validan la ingesta de fuentes, el motor de Gemini, la deduplicación y el despacho a Telegram:

```bash
pytest tests/
```

---

## ☁️ Automatización en GitHub Actions (Desatendido)

El sistema corre en la nube sin costo de servidores gracias a **GitHub Actions**:

- **Frecuencia:** Ejecución diaria a las **14:37 UTC** (`37 14 * * *`), correspondiente a las **11:37 AM CLT** (horario de verano) / **10:37 AM CLT** (horario de invierno). Diseñado para operar en el valle de menor demanda global de GitHub y tras la publicación de portadas matutinas chilenas.
- **Ejecución Manual:** Pestaña *Actions > Daily Data Newsjacking Radar > Run workflow* (permite activar `--dry-run` o `--skip-llm` desde la UI).
- **Persistencia Autónoma:** Actualiza `data/history.json` directamente en el repositorio usando `[skip ci]`.
- **Alertas de Emergencia:** Si ocurre un fallo en los servidores de GitHub, envía una alerta instantánea a Telegram con el link al run para diagnosticar en segundos.

### Configuración requerida en GitHub:
1. En **Settings > Secrets and variables > Actions**, agrega los 3 secrets: `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
2. En **Settings > Actions > General > Workflow permissions**, selecciona **"Read and write permissions"** para autorizar el auto-commit del historial.

---

## 🛠️ Stack Tecnológico

- **Lenguaje:** Python 3.11+
- **Motor de Ingesta:** `feedparser`, `requests`, `pyyaml`
- **Inteligencia Artificial:** Google Gemini Flash (`google-genai`), con schemas estructurados en `pydantic` v2
- **Mensajería:** Telegram Bot API (HTTP REST con sanitización HTML)
- **CI/CD & Cloud:** GitHub Actions, Ubuntu runners y `pytest`
