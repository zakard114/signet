from pathlib import Path

PREVIEW = Path(__file__).resolve().parents[1] / "preview" / "index.html"


def test_preview_has_approve_and_decline_paths():
    text = PREVIEW.read_text(encoding="utf-8")
    assert "Authorize" in text
    assert "Ops" in text
    assert "4242424242424242" in text
    assert "Payment completed." in text
    assert "4000000000000002" in text
    assert "We could not complete your payment." in text

