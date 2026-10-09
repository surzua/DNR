# Opciones para la Programación del Radar (Cron Confiable)

## Diagnóstico del Cron Nativo de GitHub Actions

El trigger nativo `schedule` en GitHub Actions opera bajo una política de **mejor esfuerzo (best-effort)** y prioridad baja:
- **Retrasos de horas:** Si los servidores de GitHub tienen alta demanda (especialmente en horas punta de la mañana europea y americana), los workflows programados se retrasan entre 1 y 7 horas.
- **Descartes silenciosos (*dropped*):** Durante incidentes de plataforma o saturación de cola de runners, GitHub descarta ejecuciones completas sin iniciar el runner y sin emitir notificaciones de error.

Para garantizar que el reporte se ejecute sin retrasos ni colas (por ejemplo a las **11:37 CLT / 14:37 UTC** o a la hora exacta que definas), se recomiendan las siguientes alternativas:

---

## Opción 1: Webhook Externo Gratuito (Recomendada - 100% en la Nube)

Mantiene la ejecución en los runners de GitHub Actions (sin gastar recursos de tu máquina local), pero sustituye el temporizador interno de GitHub por un servicio de cron externo de alta precisión.

### Cómo configurarlo con [cron-job.org](https://cron-job.org):

1. **Crear o tener a mano tu GitHub Personal Access Token:**
   * En GitHub ve a **Settings** > **Developer Settings** > **Personal access tokens** > **Tokens (classic)**.
   * Haz clic en **Generate new token (classic)**.
   * Nota: `cron-job-org` | Expiración: la que prefieras.
   * Marca los permisos: `repo` y `workflow`.
   * Copia el token generado (`ghp_...`).

2. **Crear un nuevo Cronjob en [cron-job.org](https://console.cron-job.org/jobs):**
   * Haz clic en el botón azul **"CREATE CRONJOB"**.
   * **Title:** `DNR Daily Trigger`
   * **URL:** `https://api.github.com/repos/surzua/DNR/actions/workflows/daily_radar.yml/dispatches`
   * **Schedule:** Selecciona `Every day at` -> `11:37` (Asegúrate de que la zona horaria sea `America/Santiago`, o en UTC a las `14:37`).

3. **Configurar la pestaña "Advanced" (Avanzado):**
   * Haz clic en la pestaña o sección **"Advanced"**.
   * **Request method:** Cambia de `GET` a **`POST`**.
   * **Request body:** Pega exactamente:
     ```json
     {"ref": "main"}
     ```
   * **Headers (Request headers):** Agrega estas 4 filas haciendo clic en **"+ Add"** / **"+ Add header"**:
     | Header (Nombre) | Value (Valor) |
     | :--- | :--- |
     | `Authorization` | `Bearer ghp_TU_TOKEN_DE_GITHUB_AQUI` |
     | `Accept` | `application/vnd.github+json` |
     | `Content-Type` | `application/json` |
     | `User-Agent` | `cron-job-org` |

4. **Guardar y Probar:**
   * Haz clic en **"CREATE"** o **"SAVE"**.
   * En la lista de jobs, haz clic en el menú `...` del cronjob y selecciona **"Test run"** (o "Execute now").
   * Debe responder **HTTP 204**, y verás que en GitHub Actions el runner inicia de inmediato en menos de 2 segundos.

> **Ventaja:** Como `workflow_dispatch` es un evento prioritario, GitHub inicia el runner en menos de 10 segundos y el cron-job externo nunca se retrasa ni depende de tener tu Mac encendida.

---

## Ejecuciones Manuales Retroactivas (`--days`)

Si por alguna razón el cron no se ejecutó en uno o más días (por ejemplo, fin de semana o días previos), el sistema soporta una ventana ampliada de búsqueda para capturar noticias atrasadas sin repetir temas ya cubiertos:

### 1. Desde tu terminal local (disparo remoto en GitHub Actions):
```bash
# Analizar los últimos 3 días (72 horas)
python3 scripts/trigger_remote_radar.py --days 3

# Analizar la última semana completa (7 días)
python3 scripts/trigger_remote_radar.py --days 7

# Simulación sin enviar a Telegram
python3 scripts/trigger_remote_radar.py --days 3 --dry-run
```

### 2. Desde la interfaz web de GitHub Actions:
1. Ve a **Actions** > **Daily Data Newsjacking Radar**.
2. Haz clic en **Run workflow**.
3. En el campo **"Ventana de días hacia atrás..."**, escribe `3` o `7`.
4. Haz clic en el botón verde **Run workflow**.

### 3. Ejecución directa en local:
```bash
python3 main.py --days 3
```

> **Protección inteligente:** Gracias al historial en `data/history.json`, el radar no repetirá temas sobre los cuales ya haya alertado en los últimos 7 días, enfocándose solo en nuevas oportunidades detectadas dentro de esa ventana.

---

## Opción 2: Temporizador Local en macOS con `launchd`

Si tu Mac suele estar encendida en las mañanas, puedes programar un daemon nativo de macOS para que corra el script localmente o llame al disparador remoto:

### Archivo de configuración `~/Library/LaunchAgents/com.dnr.dailyradar.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dnr.dailyradar</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/sebastianfelipeurzuaborquez/Proyectos/DNR/.venv/bin/python</string>
        <string>/Users/sebastianfelipeurzuaborquez/Proyectos/DNR/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/sebastianfelipeurzuaborquez/Proyectos/DNR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>23</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/sebastianfelipeurzuaborquez/Proyectos/DNR/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/sebastianfelipeurzuaborquez/Proyectos/DNR/logs/launchd_err.log</string>
</dict>
</plist>
```

Para activarlo en macOS:
```bash
launchctl load ~/Library/LaunchAgents/com.dnr.dailyradar.plist
```
