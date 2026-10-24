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


def read_decline_card() -> dict:
    request = urllib.request.Request(PLATES_URL, method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        raw = response.read().decode("utf-8")
    if has_pan(raw):
        raise RuntimeError("blocked: full card number")
    body = json.loads(raw)
    return {key: body[key] for key in KEYS}


def send(message: dict) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def handle(message: dict) -> None:
    method = message.get("method")
    message_id = message.get("id")
    if method == "initialize":
        send(
            {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "signet-local", "version": "0.1.0"},
                },
            }
        )
        return
    if method == "notifications/initialized":
        return
    if method == "tools/list":
        send(
            {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "tools": [
                        {
                            "name": "read_decline_card",
                            "description": "Read the one local decline card. No full card number. No writes.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": False,
                            },
                        }
                    ]
                },
            }
        )
        return
    if method == "tools/call":
        name = message.get("params", {}).get("name")
        if name != "read_decline_card":
            send(
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {"code": -32602, "message": "unknown tool"},
                }
            )
            return
        try:
            text = json.dumps(read_decline_card(), separators=(",", ":"))
            send(
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "content": [{"type": "text", "text": text}],
                        "isError": False,
                    },
                }
            )
        except Exception as exc:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": {
                        "content": [{"type": "text", "text": str(exc)}],
                        "isError": True,
                    },
                }
            )
        return
    if message_id is not None:
        send(
            {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {"code": -32601, "message": "method not found"},
            }
        )


def once() -> int:
    try:
        card = read_decline_card()
    except Exception as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1
    sys.stdout.write(json.dumps(card, separators=(",", ":")) + "\n")
    return 0


def main() -> int:
    if "--once" in sys.argv:
        return once()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        handle(json.loads(line))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
