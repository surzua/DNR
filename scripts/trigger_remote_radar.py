#!/usr/bin/env python3
"""Disparador remoto para el workflow de GitHub Actions de Daily Data Newsjacking Radar.

Este script permite activar el pipeline en GitHub Actions a través de la API REST
(workflow_dispatch), evitando depender de la cola demorada de cron interno de GitHub.
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO_OWNER = "surzua"
REPO_NAME = "DNR"
WORKFLOW_FILE = "daily_radar.yml"


def get_github_token() -> str:
    """Obtiene el token de GitHub desde GITHUB_TOKEN en el entorno o desde el keychain de macOS."""
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token

    # Intentar obtener desde git credential helper (osxkeychain)
    try:
        cmd = 'printf "protocol=https\\nhost=github.com\\n\\n" | git credential fill'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        for line in res.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except Exception:
        pass

    return ""


def trigger_workflow(dry_run: bool = False, skip_llm: bool = False) -> bool:
    """Dispara el workflow en GitHub Actions."""
    token = get_github_token()
    if not token:
        print("❌ Error: No se encontró token de GitHub. Configura GITHUB_TOKEN o autentica con Git.", file=sys.stderr)
        return False

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    payload = json.dumps({
        "ref": "main",
        "inputs": {
            "dry_run": str(dry_run).lower(),
            "skip_llm": str(skip_llm).lower(),
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "DNR-Trigger/1.0",
            "Content-Type": "application/json",
        }
    )

    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                print(f"✅ Workflow '{WORKFLOW_FILE}' disparado exitosamente en GitHub Actions ({REPO_OWNER}/{REPO_NAME}).")
                print(f"👉 Revisa la ejecución en: https://github.com/{REPO_OWNER}/{REPO_NAME}/actions")
                return True
            print(f"⚠️ Respuesta inesperada: HTTP {resp.status}")
            return False
    except urllib.error.HTTPError as e:
        print(f"❌ Error HTTP al disparar workflow: {e.code} - {e.read().decode('utf-8', errors='ignore')}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Error al contactar GitHub API: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    is_skip = "--skip-llm" in sys.argv
    success = trigger_workflow(dry_run=is_dry, skip_llm=is_skip)
    sys.exit(0 if success else 1)
