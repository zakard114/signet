"""Read the local request board and say whether shoppers are seeing server errors.

This is the on-call check for this PC. It does not page anyone, it does not
call the public site, and it does not start a deploy.
"""

import json
import sys
import urllib.error
import urllib.request

BOARD = "http://127.0.0.1:8001/ops/board"


def server_error_count(board: dict) -> int:
    count = 0
    for row in board.get("logs") or []:
        try:
            status = int(row.get("status") or 0)
        except (TypeError, ValueError):
            continue
        if status >= 500:
            count += 1
    return count


def main() -> int:
    try:
        with urllib.request.urlopen(BOARD, timeout=5) as response:
            board = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        sys.stdout.write("user impact: unknown\n")
        sys.stdout.write("the local board did not answer\n")
        sys.stdout.write("recovery: docker compose -f docker-compose.yaml ps\n")
        sys.stdout.write("do not start a production deploy from this check\n")
        return 2
    errors = server_error_count(board)
    if errors:
        sys.stdout.write("user impact: shoppers are receiving HTTP 5xx\n")
        sys.stdout.write(f"count in the board window: {errors}\n")
        sys.stdout.write("recovery: open local Grafana at http://127.0.0.1:3001 and read the trace id\n")
        sys.stdout.write("a normal decline is not this alert\n")
        sys.stdout.write("do not start a production deploy from this check\n")
        return 1
    sys.stdout.write("user impact: no HTTP 5xx in the local board window\n")
    sys.stdout.write("recovery: none\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
