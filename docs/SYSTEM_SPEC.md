# Data Newsjacking Radar (DNR) \- System Specification

## 1\. Executive Summary & Purpose

El **Data Newsjacking Radar (DNR)** es un sistema automatizado de inteligencia de tendencias diseñado para detectar noticias de alta tracción (políticas, económicas, deportivas o sociales) en Chile y evaluar de forma autónoma su viabilidad como proyectos rápidos de Data Science / Analytics.

El objetivo es maximizar la visibilidad y el alcance profesional mediante la publicación oportuna (dentro de una ventana de 24 a 72 horas) de visualizaciones, análisis exploratorios, simuladores o modelos que aporten evidencia cuantitativa o contrasten narrativas públicas.

---

## 2\. Architecture & Data Flow

\[Cron: GitHub Actions (07:30 CLT)\]

                │

                ▼

   ┌────────────────────────┐

   │ 1\. Ingestion Layer     │ ◄── RSS Feeds (Emol, DF, La Tercera, BioBio)

   │    (Sources Scraper)   │ ◄── Reddit JSON API (r/chile, r/republicadechile)

   │                        │ ◄── Google Trends (Pytrends / Daily Trends)

   └────────────┬───────────┘

                │ Raw Articles & Threads (últimas 24h)

                ▼

   ┌────────────────────────┐

   │ 2\. Deduplication &     │ ◄── Lee \`data/history.json\` (últimos 7 días)

   │    Filtering           │ ─── Descarta tópicos previamente analizados

   └────────────┬───────────┘

                │ Unseen Trending Clusters

                ▼

   ┌────────────────────────┐

   │ 3\. LLM Strategy &      │ ◄── Gemini Flash (Structured JSON Output)

   │    Feasibility Engine  │ ─── Evalúa potencial viral, ángulo analítico y

   │                        │     fuentes públicas (APIs, Wikipedia, .gob)

   └────────────┬───────────┘

                │ Scored Opportunities (Score \>= 7/10)

                ▼

   ┌────────────────────────┐

   │ 4\. Dispatch & Storage  │ ──► Envía alerta formateada a Telegram Bot

   │    Pipeline            │ ──► Actualiza \`data/history.json\` & Git commit

   └────────────────────────┘

---

## 3\. Project Structure

data-newsjacking-radar/

├── .github/

│   └── workflows/

│       └── daily\_radar.yml        \# Cron workflow de GitHub Actions

├── config/

│   └── sources.yaml               \# URLs de feeds RSS, subreddits y parámetros

├── data/

│   └── history.json               \# Registro histórico de oportunidades analizadas

├── docs/

│   └── SYSTEM\_SPEC.md             \# Esta especificación

├── src/

│   ├── \_\_init\_\_.py

│   ├── ingestion/

│   │   ├── \_\_init\_\_.py

│   │   ├── news\_rss.py            \# Parser de feeds RSS de prensa chilena

│   │   ├── reddit\_client.py       \# Scraper ligero vía endpoints JSON públicos

│   │   └── trends\_client.py       \# Extractor de tendencias en búsquedas

│   ├── analysis/

│   │   ├── \_\_init\_\_.py

│   │   ├── prompt\_templates.py    \# Prompts del sistema y de análisis

│   │   └── opportunity\_eval.py    \# Integración con Gemini API \+ Pydantic schema

│   ├── storage/

│   │   ├── \_\_init\_\_.py

│   │   └── history\_manager.py     \# Manejo de lectura/escritura y deduplicación

│   └── notifiers/

│       ├── \_\_init\_\_.py

│       └── telegram\_bot.py        \# Despachador de mensajes a Telegram

├── main.py                        \# Entrypoint de ejecución del pipeline

├── pyproject.toml / requirements.txt

└── README.md

---

## 4\. Component Details & Technical Requirements

### 4.1 Ingestion Layer

* **`news_rss.py`**: Utiliza `feedparser` y `requests`.  
  * Fuentes iniciales:  
    * EMOL (Nacional, Economía, Deportes).  
    * Diario Financiero (Economía, Empresas, Mercados).  
    * La Tercera (Nacional, Política, Pulso).  
    * BioBioChile (Nacional, Economía).  
  * Extrae: `title`, `link`, `summary`, `published_at`.  
* **`reddit_client.py`**:  
  * Consume endpoints públicos `.json` de Reddit (por ejemplo subreddits `chile` y `republicadechile`) usando cabeceras `User-Agent` descriptivas.  
  * Filtra hilos con alto engagement (`score > 50` o `num_comments > 30`).  
* **Resiliencia:** Si una fuente falla (HTTP 4xx/5xx o timeout), el scraper registra un warning y continúa con las demás.

### 4.2 Storage & Deduplication (`history_manager.py`)

* Estructura de `data/history.json`:  
    
  \[  
    
    {  
    
      "id": "2026-10-06-001",  
    
      "timestamp": "2026-10-06T10:30:00Z",  
    
      "topic": "Polémica por licitación de luminarias públicas",  
    
      "category": "Política / Transparencia",  
    
      "viral\_hook\_type": "Desmitificador",  
    
      "analytical\_angle": "Simulador de costo por luminaria vs. presupuesto comunal",  
    
      "data\_sources": \[  
    
        {"name": "Mercado Público", "type": "API / Portal Abierto", "query": "Licitaciones alumbrado público"},  
    
        {"name": "Wikipedia \- Comunas de Chile", "type": "HTML Table", "query": "Población y presupuesto comunal"}  
    
      \],  
    
      "feasibility\_score": 8,  
    
      "virality\_score": 9,  
    
      "recommended\_deliverable": "Static chart \+ LinkedIn thread",  
    
      "status": "candidate"  
    
    }  
    
  \]  
    
* En cada corrida, inyecta los temas de los últimos 7 días al prompt del LLM para descartar repeticiones.

### 4.3 Evaluation Engine (`opportunity_eval.py`)

Utiliza la API de Gemini con `response_mime_type="application/json"` y un esquema Pydantic estricto.

#### Pydantic Schema:

from pydantic import BaseModel, Field

from typing import List, Literal

class DataSource(BaseModel):

    name: str

    type: Literal\["API Pública", "Tabla Wikipedia", "Portal Abierto", "Scraping HTML", "Dataset Descargable"\]

    potential\_url\_or\_query: str

    friction\_level: Literal\["Baja (Horas)", "Media (1-2 días)", "Alta (Requiere peticiones de transparencia)"\]

class Opportunity(BaseModel):

    headline: str

    category: Literal\["Economía & Finanzas", "Política & Estado", "Deportes", "Sociedad & Tendencias"\]

    why\_is\_trending: str

    contrarian\_or\_curious\_angle: str \= Field(description="El gancho cognitivo: qué mito se desmiente o qué duda resuelve")

    suggested\_deliverable: Literal\["Gráfico Estático de Alto Impacto", "App Interactiva (Streamlit)", "Análisis Predictivo/Optimización"\]

    data\_sources: List\[DataSource\]

    virality\_score: int \= Field(ge=1, le=10)

    technical\_feasibility\_score: int \= Field(ge=1, le=10)

    fast\_execution\_strategy: str \= Field(description="Plan de acción concreto en 3 pasos para construirlo en menos de 4 horas")

class RadarResponse(BaseModel):

    evaluated\_topics\_count: int

    top\_opportunities: List\[Opportunity\]

#### Core System Prompt Rules:

1. **Buscar datos no estructurados:** No limitarse a portales de gobierno (`.gob`). Buscar activamente tablas históricas de Wikipedia (e.g. resultados de elecciones, planteles deportivos, datos censales comunales) o sitios con HTML estructurado (Transfermarkt, CMF, Banco Central).  
2. **Pensar en el gancho ("Hook"):** Descartar resúmenes aburridos. Formular ángulos contrarios a la intuición (*"Todo el mundo dice X, pero la data histórica muestra Y"*) o simuladores de impacto personal (*"¿Cuánto te afecta a ti?"*).  
3. **Filtro de umbral:** Solo retornar oportunidades donde `virality_score >= 7` y `technical_feasibility_score >= 6`. Máximo 3 por ejecución para no saturar.

### 4.4 Notification Layer (`telegram_bot.py`)

* Envía cada oportunidad como un mensaje formateado en Markdown:  
    
  🚀 \*OPORTUNIDAD DE DATA DETECTADA\* (Score: 8.5/10)  
    
  📌 \*Tema:\* Polémica por precios de arriendos en comunas céntricas  
    
  🎯 \*Ángulo Analítico:\* "¿Realmente cayeron los arriendos o solo se redujo el metraje cuadrado promedio?"  
    
  📊 \*Fuentes de Datos:\*  
    
  • Portales inmobiliarios (Scraping de precios por m²)  
    
  • INE / SII (Avalúo fiscal y series históricas)  
    
  ⏱️ \*Entregable sugerido:\* Gráfico estático anotado estilo periodismo de datos.  
    
  🛠️ \*Plan rápido:\* 1\. Script BeautifulSoup para 500 avisos | 2\. Boxplot precio/m² por comuna | 3\. Post con hallazgo clave.

---

## 5\. Automation: GitHub Actions Workflow

Archivo `.github/workflows/daily_radar.yml`:

name: Daily Data Newsjacking Radar

on:

  schedule:

    \# Corre todos los días a las 10:30 UTC (07:30 AM CLT en UTC-3)

    \- cron: '30 10 \* \* \*'

  workflow\_dispatch: \# Permite ejecución manual desde la UI de GitHub

jobs:

  run-radar:

    runs-on: ubuntu-latest

    steps:

      \- name: Check out repository

        uses: actions/checkout@v4

        with:

          token: \${{ secrets.GITHUB\_TOKEN }}

      \- name: Set up Python

        uses: actions/setup-python@v5

        with:

          python-version: '3.11'

          cache: 'pip'

      \- name: Install dependencies

        run: |

          python \-m pip install \--upgrade pip

          pip install \-r requirements.txt

      \- name: Run Radar Pipeline

        env:

          GEMINI\_API\_KEY: \${{ secrets.GEMINI\_API\_KEY }}

          TELEGRAM\_BOT\_TOKEN: \${{ secrets.TELEGRAM\_BOT\_TOKEN }}

          TELEGRAM\_CHAT\_ID: \${{ secrets.TELEGRAM\_CHAT\_ID }}

        run: python main.py

      \- name: Commit and push history updates

        run: |

          git config \--local user.email "github-actions\[bot\]@users.noreply.github.com"

          git config \--local user.name "github-actions\[bot\]"

          git add data/history.json

          git diff \--quiet && git diff \--staged \--quiet || (git commit \-m "chore: update radar history \[skip ci\]" && git push)

---

## 6\. Environment Variables Required

Configurar en `Settings > Secrets and variables > Actions`:

* `GEMINI_API_KEY`: API Key obtenida gratis en Google AI Studio.  
* `TELEGRAM_BOT_TOKEN`: Token obtenido al crear el bot con `@BotFather`.  
* `TELEGRAM_CHAT_ID`: Tu ID de chat personal (obtenible reenviando un mensaje a `@userinfobot`).

---

## 7\. Immediate Next Steps for Implementation

1. Inicializar el repositorio Git con la estructura de carpetas definida en la sección 3\.  
2. Implementar `src/ingestion/news_rss.py` probando los 4 feeds RSS chilenos básicos.  
3. Configurar la llamada a Gemini con salida tipada (`Pydantic`) en `src/analysis/opportunity_eval.py`.  
4. Probar la ejecución local de `main.py` verificando que llegue la alerta a Telegram y se actualice `data/history.json`.  
5. Subir a GitHub y activar el workflow de Actions.