# Opciones para la Programación del Radar (Cron Confiable)

## Diagnóstico del Cron Nativo de GitHub Actions

El trigger nativo `schedule` en GitHub Actions opera bajo una política de **mejor esfuerzo (best-effort)** y prioridad baja:
- **Retrasos de horas:** Si los servidores de GitHub tienen alta demanda (especialmente en horas punta de la mañana europea y americana), los workflows programados se retrasan entre 1 y 7 horas.
- **Descartes silenciosos (*dropped*):** Durante incidentes de plataforma o saturación de cola de runners, GitHub descarta ejecuciones completas sin iniciar el runner y sin emitir notificaciones de error.

Para garantizar que el reporte llegue a tu Telegram **exactamente a las 07:23 CLT (10:23 UTC)** todos los días, se recomiendan las siguientes alternativas:

---

## Opción 1: Webhook Externo Gratuito (Recomendada - 100% en la Nube)

Mantiene la ejecución en los runners de GitHub Actions (sin gastar recursos de tu máquina local), pero sustituye el temporizador interno de GitHub por un servicio de cron externo de alta precisión.

### Cómo configurarlo con [cron-job.org](https://cron-job.org):
1. **Crear una cuenta gratis** en [cron-job.org](https://cron-job.org).
2. **Crear un nuevo Cronjob:**
   * **Title:** `DNR Daily Trigger`
   * **URL:** `https://api.github.com/repos/surzua/DNR/actions/workflows/daily_radar.yml/dispatches`
   * **Request Method:** `POST`
   * **Schedule:** Todos los días a las `07:23` (Horario Santiago de Chile / `America/Santiago`) o `10:23 UTC`.
3. **Configurar Headers HTTP:**
   * `Authorization`: `Bearer <TU_GITHUB_PERSONAL_ACCESS_TOKEN>`
   * `Accept`: `application/vnd.github+json`
   * `User-Agent`: `cron-job-org`
   * `Content-Type`: `application/json`
4. **Configurar Request Body:**
   ```json
   {"ref": "main"}
   ```
5. *(Opcional)*: Para crear el token en GitHub:
   * Ve a **GitHub** > **Settings** > **Developer Settings** > **Personal access tokens (classic)**.
   * Genera un token con permisos `repo` y `workflow`.

> **Ventaja:** Como `workflow_dispatch` es un evento prioritario, GitHub inicia el runner en menos de 10 segundos y el cron-job externo nunca se retrasa.

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
