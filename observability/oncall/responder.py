"""Wake on the shopper HTTP 5xx alert and restart the local app.

This command stays on this PC. It does not call Render, it does not deploy
Grafana, and it does not POST /plates.
"""

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = "http://127.0.0.1:8001/"


def has_pan(text: str) -> bool:
    run = 0
    for ch in text:
        if ch.isdigit():
            run += 1
            if run >= 13:
                return True
        else:
            run = 0
    return False


def shopper_alert_firing(payload: dict) -> bool:
    if payload.get("status") != "firing":
        return False
    for alert in payload.get("alerts") or []:
        if alert.get("status") != "firing":
            continue
        labels = alert.get("labels") or {}
        if labels.get("impact") == "shopper":
            return True
    return False


def restart_local_app() -> int:
    completed = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.yaml", "restart", "app"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        sys.stdout.write("fix failed: local app did not restart\n")
        return 1
    try:
        with urllib.request.urlopen(APP, timeout=20) as response:
            status = response.status
    except (urllib.error.URLError, TimeoutError, OSError):
        sys.stdout.write("fix failed: local app did not answer after restart\n")
        return 1
    if status >= 500:
        sys.stdout.write(f"fix failed: local app answered HTTP {status}\n")
        return 1
    sys.stdout.write(f"fixed: restarted local app, HTTP {status}\n")
    sys.stdout.write("did not POST /plates and did not start a production deploy\n")
    return 0


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] != "--alert":
        sys.stdout.write("usage: python observability/oncall/responder.py --alert FILE\n")
        return 2
    path = Path(sys.argv[2])
    text = path.read_text(encoding="utf-8")
    if has_pan(text):
        sys.stdout.write("blocked: full card number\n")
        return 1
    payload = json.loads(text)
    if not shopper_alert_firing(payload):
        sys.stdout.write("not firing: no local restart\n")
        return 0
    sys.stdout.write("alert firing: shopper HTTP 5xx\n")
    return restart_local_app()


if __name__ == "__main__":
    raise SystemExit(main())
