"""Wake on the shopper HTTP 5xx alert and clear the local degrade switch.

This command stays on this PC. It does not restart Docker, it does not call
Render, it does not deploy Grafana, and it does not POST /plates.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = "http://127.0.0.1:8001/"
DEGRADE = ROOT / "observability" / "oncall" / "shopper-degrade"


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


def app_status() -> int | None:
    try:
        with urllib.request.urlopen(APP, timeout=5) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def clear_shopper_degrade() -> None:
    if DEGRADE.is_file():
        DEGRADE.unlink()


def repair_shopper_path() -> int:
    clear_shopper_degrade()
    status = app_status()
    if status is None:
        sys.stdout.write("fix failed: local app did not answer\n")
        return 1
    if status >= 500:
        sys.stdout.write(f"fix failed: local app answered HTTP {status}\n")
        return 1
    sys.stdout.write(f"fixed: cleared shopper degrade, HTTP {status}\n")
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
        sys.stdout.write("not firing: no repair\n")
        return 0
    sys.stdout.write("alert firing: shopper HTTP 5xx\n")
    status = app_status()
    if status is not None and status < 500:
        sys.stdout.write(f"shoppers are being served: HTTP {status}\n")
        sys.stdout.write("no repair\n")
        sys.stdout.write("did not POST /plates and did not start a production deploy\n")
        return 0
    if status is None:
        sys.stdout.write("shopper path did not answer\n")
    else:
        sys.stdout.write(f"shopper path HTTP {status}\n")
    return repair_shopper_path()


if __name__ == "__main__":
    raise SystemExit(main())
