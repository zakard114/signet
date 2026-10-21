# (6/11) Automated Testing

업계 이름: Automated Testing.
이번 화면에서: 승인 한 번과 거절 한 번을 코드로 확인한다.

목표: 유닛, 통합, 화면 테스트가 그 두 길을 통과한다.
완료: `pytest`가 세 파일을 모두 통과하고, 응답 JSON에 카드 번호 전체가 없다.
하지 말 것: Docker 이미지, 배포, 화면 디자인 수정, git, 7/11, 공개 Render 호출.

이미 있는 것:
- `E:\IT_SPACES\AI\Projects\aidt\signet\app\main.py`
- `E:\IT_SPACES\AI\Projects\aidt\signet\preview\index.html`
- `E:\IT_SPACES\AI\Projects\aidt\signet\requirements.txt`
- 가상환경 `E:\IT_SPACES\AI\Projects\aidt\signet\.venv`
- Postgres는 `docker-compose.yaml`의 5433. 창 A의 uvicorn은 테스트에 필요 없다. TestClient가 앱을 직접 부른다.
- 카드 테스트 모양은 이전 프로젝트 `E:\IT_SPACES\AI\Projects\aidt\fault-plate\tests\test_plates.py`를 참고한다. 파일 통째로 복사하지 않는다.

## 1. requirements.txt

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\requirements.txt`
이 다섯 줄만 남긴다.

용도: 테스트에 쓸 패키지 이름을 목록에 넣는다.
기능: fastapi, uvicorn, psycopg, pytest, httpx를 설치할 이름을 적는다.
이유: TestClient는 httpx가 필요하고, 통합은 Postgres를 친다.

```text
fastapi
uvicorn
psycopg[binary]
pytest
httpx
```

## 2. 유닛 테스트

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\tests\test_unit.py`
`tests` 폴더를 새로 만들고 이 파일을 둔다.

용도: 카드 번호에서 숫자만 남기는 함수를 서버 없이 확인한다.
기능: `digits`가 공백과 하이픈을 지우고 숫자만 남긴다.
이유: 승인·거절 전에 자릿수 검사가 이 함수에 의존한다.

```python
from app.main import digits


def test_digits_keep_numbers_only():
    assert digits("4242-4242-4242-4242") == "4242424242424242"
    assert digits(" 4000 0000 0000 0002 ") == "4000000000000002"
```

## 3. 통합 테스트

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\tests\test_integration.py`
Postgres가 5433에서 떠 있어야 한다.

용도: 승인 한 번과 거절 한 번이 DB를 거쳐 계약대로 돌아가는지 확인한다.
기능: TestClient로 POST /authorizations와 POST /plates를 보내고, 응답에 카드 번호가 없는지 본다.
이유: 명세의 통합 테스트는 그 데이터베이스를 친다.

```python
import os

import psycopg
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://signet:signet@127.0.0.1:5433/signet",
)

from app import main


@pytest.fixture()
def client():
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_tables():
    with psycopg.connect(main.DATABASE_URL) as conn:
        conn.execute("TRUNCATE authorization_log RESTART IDENTITY")
        conn.execute("TRUNCATE plate")
    yield


def test_approve_once(client):
    response = client.post(
        "/authorizations",
        json={"amount": 128, "card": "4242424242424242"},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["sentence"] == "Payment completed."
    assert body["amount"] == 128
    assert body.get("stop_step") is None
    assert "4242424242424242" not in response.text
    with psycopg.connect(main.DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT sentence, amount FROM authorization_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row == ("Payment completed.", 128.0)


def test_decline_once(client):
    plate = {
        "name": "declined",
        "user_facing_message": "This card was declined.",
        "http_status": 400,
        "log_fields": "amount",
        "retry_allowed": "not_retryable",
    }
    saved = client.post("/plates", json=plate)
    assert saved.status_code == 201
    response = client.post(
        "/authorizations",
        json={"amount": 128, "card": "4000000000000002"},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["stop_step"] == 5
    assert body["sentence"] == "This card was declined."
    assert "4000000000000002" not in response.text
```

## 4. 화면 테스트

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\tests\test_screen.py`
브라우저를 열지 않는다. 미리보기 HTML에 두 길이 적혀 있는지 읽는다.

용도: 고객 미리보기가 승인 문장과 거절 문장, Authorize와 Ops를 갖는지 확인한다.
기능: `preview/index.html` 문자열에서 그 네 조각을 찾는다.
이유: 명세의 화면 테스트는 승인 한 번과 거절 한 번을 본다. 이번 게이트는 그 길이 화면에 고정돼 있는지만 본다.

```python
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
```

## 5. 실행

Docker Desktop이 떠 있고 Postgres 컨테이너가 Up이어야 한다. uvicorn 창은 꺼도 된다.

```powershell
. E:\IT_SPACES\AI\scripts\use_e_drive.ps1
Set-Location E:\IT_SPACES\AI\Projects\aidt\signet
docker compose -f E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml up -d
& "E:\IT_SPACES\AI\Projects\aidt\signet\.venv\Scripts\python.exe" -m pip install -r requirements.txt
$env:DATABASE_URL = "postgresql://signet:signet@127.0.0.1:5433/signet"
& "E:\IT_SPACES\AI\Projects\aidt\signet\.venv\Scripts\python.exe" -m pytest -q
```

용도: E: 캐시로 패키지를 넣고, Postgres 다음에 세 테스트 파일을 실행한다.
기능: pytest가 유닛, 통합, 화면 파일을 순서 없이 돌리고 통과 개수를 찍는다.
이유: 승인 한 번과 거절 한 번이 코드로 남았는지 이 게이트에서 닫는다.

확인:
1. 출력에 실패한 테스트가 없다. `passed`만 있다.
2. 통합의 승인 응답과 거절 응답에 카드 번호 전체가 없다.
3. 화면 테스트는 브라우저 창을 열지 않는다.

이 게이트의 스크린샷은 없다.
