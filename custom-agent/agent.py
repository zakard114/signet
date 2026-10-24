import json
import sys
import urllib.request

PLATES_URL = "http://127.0.0.1:8001/plates"
KEYS = ("name", "user_facing_message", "http_status", "log_fields", "retry_allowed")


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


def main() -> int:
    request = urllib.request.Request(PLATES_URL, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read().decode("utf-8")
    except Exception as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1
    if has_pan(raw):
        sys.stderr.write("blocked: full card number\n")
        return 1
    body = json.loads(raw)
    card = {key: body[key] for key in KEYS}
    sys.stdout.write(json.dumps(card, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
