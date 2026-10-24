import sys
from pathlib import Path


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
    if len(sys.argv) != 2:
        sys.stderr.write("usage: block_pan.py FILE\n")
        return 2
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    if has_pan(text):
        sys.stdout.write("blocked: full card number\n")
        return 1
    sys.stdout.write("allowed\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
