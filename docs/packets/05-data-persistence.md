# (5/11) Data Persistence

업계 이름: Data Persistence.
이번 화면에서: 결제 기록과 거절 카드 한 장이 같은 Postgres에 남고, 재시작 후에도 그 문장이 남는다. 배포는 Signet 하나다.

목표: 승인 POST는 카드 번호 없이 한 줄을 남긴다. `POST /plates`가 거절 카드 한 장을 덮고, 거절 승인은 그 줄을 읽는다.
완료: Signet과 Postgres를 다시 띄워도 승인 문장과 카드 문장이 있다.
하지 말 것: Fault Plate 서버를 다시 띄우기, 공개 Render 주소 호출, 앱 이미지, 화면 수정, 테스트 파일, git, 6/11. 카드 코드는 이전 프로젝트 `E:\IT_SPACES\AI\Projects\aidt\fault-plate\app\main.py`의 `Plate`, `create_plate`, `read_plate`, `plate` 표를 가져온다. SQLite 접속과 신호·알림·온콜은 이번 게이트에 넣지 않는다. 저장만 Postgres로 바꾼다.

이미 있는 것:
- `E:\IT_SPACES\AI\Projects\aidt\signet\app\main.py`
- `E:\IT_SPACES\AI\Projects\aidt\signet\requirements.txt`
- `E:\IT_SPACES\AI\Projects\aidt\signet\openapi.yaml`
- 가상환경 `E:\IT_SPACES\AI\Projects\aidt\signet\.venv`

## 1. Postgres만 띄우는 파일

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml`

용도: 결제 기록과 거절 카드 한 장을 담을 데이터베이스만 띄운다.
기능: Postgres 16이 이 PC의 5433번에서 받고, 데이터 폴더는 E:에 남는다.
이유: 앱 이미지는 7/11이다. 이번 게이트는 두 줄을 디스크에 남긴다.

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: signet
      POSTGRES_PASSWORD: signet
      POSTGRES_DB: signet
    ports:
      - "5433:5432"
    volumes:
      - E:/IT_SPACES/AI/Projects/aidt/signet/docker/pgdata:/var/lib/postgresql/data
```

## 2. requirements.txt

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\requirements.txt`
이 세 줄만 남긴다.

용도: Postgres에 접속하는 패키지를 목록에 넣는다.
기능: fastapi, uvicorn, psycopg를 가상환경에 설치할 이름을 적는다.
이유: 기록과 카드 한 장은 SQLite나 다른 서버가 아니라 이 Postgres다.

```text
fastapi
uvicorn
psycopg[binary]
```

## 3. openapi.yaml의 /plates

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\openapi.yaml`
`/plates:` 아래의 `get:` 블록은 그대로 두고, 그 앞에 `post:` 블록만 넣는다. summary 문장도 아래와 같이 바꾼다.

용도: 카드 한 장을 덮는 호출을 계약에 넣는다.
기능: POST는 카드 필드를 받아 201을 돌려주고, GET은 저장된 한 장을 돌려준다.
이유: 카드 저장이 Signet 안에 있으므로 계약도 이 서버의 경로다.

```yaml
  /plates:
    post:
      summary: Overwrite the one decline card
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name, user_facing_message, http_status, log_fields, retry_allowed]
              properties:
                name:
                  type: string
                user_facing_message:
                  type: string
                http_status:
                  type: integer
                log_fields:
                  type: string
                retry_allowed:
                  type: string
                  enum: [retryable, not_retryable]
      responses:
        "201":
          description: The saved card
          content:
            application/json:
              schema:
                type: object
                required: [name, user_facing_message, http_status, log_fields, retry_allowed]
                properties:
                  name:
                    type: string
                  user_facing_message:
                    type: string
                  http_status:
                    type: integer
                  log_fields:
                    type: string
                  retry_allowed:
                    type: string
                    enum: [retryable, not_retryable]
    get:
      summary: Read the one decline card
```

`get:` 아래의 responses는 지금 파일에 있는 것을 유지한다.

## 4. app\main.py

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\app\main.py`
아래 코드로 파일 전체를 바꾼다. 카드 번호 열은 없다. 다른 서버로 나가지 않는다.

용도: 승인 결과와 거절 카드 한 장을 같은 데이터베이스에 남긴다.
기능: 시작 때 두 표를 만들고, 승인마다 한 줄을 넣으며, POST가 카드 한 장을 덮는다.
이유: 프로세스를 다시 띄워도 문장이 남고, Signet 밖의 배포가 필요 없다.

```python
import os
from typing import Literal, Optional

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Signet", version="0.1.0")
LIMIT = 500
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://signet:signet@127.0.0.1:5433/signet",
)


class AuthorizationRequest(BaseModel):
    amount: float
    card: str


class AuthorizationResponse(BaseModel):
    stop_step: Optional[int] = None
    sentence: str
    http_status: int
    log_field: str
    retry: Literal["retryable", "not_retryable"]
    amount: Optional[float] = None


class Plate(BaseModel):
    name: str
    user_facing_message: str
    http_status: int
    log_fields: str
    retry_allowed: Literal["retryable", "not_retryable"]


def digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def init_db() -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS authorization_log (
                id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                stop_step integer,
                sentence text NOT NULL,
                http_status integer NOT NULL,
                log_field text NOT NULL,
                retry text NOT NULL,
                amount double precision,
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS plate (
                id integer PRIMARY KEY CHECK (id = 1),
                name text NOT NULL,
                user_facing_message text NOT NULL,
                http_status integer NOT NULL,
                log_fields text NOT NULL,
                retry_allowed text NOT NULL
            )
            """
        )


def save_log(row: AuthorizationResponse) -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            INSERT INTO authorization_log
                (stop_step, sentence, http_status, log_field, retry, amount)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                row.stop_step,
                row.sentence,
                row.http_status,
                row.log_field,
                row.retry,
                row.amount,
            ),
        )


def plate_decline() -> AuthorizationResponse:
    with psycopg.connect(DATABASE_URL) as conn:
        found = conn.execute(
            """
            SELECT user_facing_message, http_status, log_fields, retry_allowed
            FROM plate
            WHERE id = 1
            """
        ).fetchone()
    if found is None:
        return AuthorizationResponse(
            stop_step=5,
            sentence="We could not complete your payment.",
            http_status=400,
            log_field="amount",
            retry="not_retryable",
        )
    return AuthorizationResponse(
        stop_step=5,
        sentence=found[0],
        http_status=found[1],
        log_field=found[2],
        retry=found[3],
    )


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.post("/plates", status_code=201)
def create_plate(plate: Plate) -> Plate:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
            INSERT INTO plate (
                id, name, user_facing_message, http_status, log_fields, retry_allowed
            )
            VALUES (1, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                user_facing_message = EXCLUDED.user_facing_message,
                http_status = EXCLUDED.http_status,
                log_fields = EXCLUDED.log_fields,
                retry_allowed = EXCLUDED.retry_allowed
            """,
            (
                plate.name,
                plate.user_facing_message,
                plate.http_status,
                plate.log_fields,
                plate.retry_allowed,
            ),
        )
    return plate


@app.get("/plates")
def read_plate() -> Plate:
    with psycopg.connect(DATABASE_URL) as conn:
        found = conn.execute(
            """
            SELECT name, user_facing_message, http_status, log_fields, retry_allowed
            FROM plate
            WHERE id = 1
            """
        ).fetchone()
    if found is None:
        raise HTTPException(status_code=404, detail="no plate")
    return Plate(
        name=found[0],
        user_facing_message=found[1],
        http_status=found[2],
        log_fields=found[3],
        retry_allowed=found[4],
    )


@app.post("/authorizations")
def authorize(body: AuthorizationRequest) -> AuthorizationResponse:
    pan = digits(body.card)
    if body.amount <= 0 or body.amount > LIMIT:
        row = AuthorizationResponse(
            stop_step=2,
            sentence="This amount is above the limit.",
            http_status=400,
            log_field="amount",
            retry="retryable",
        )
    elif not 13 <= len(pan) <= 19:
        row = AuthorizationResponse(
            stop_step=3,
            sentence="The card number length is not valid.",
            http_status=400,
            log_field="card",
            retry="retryable",
        )
    elif pan == "4000000000000002":
        row = plate_decline()
    elif pan == "4242424242424242":
        row = AuthorizationResponse(
            sentence="Payment completed.",
            http_status=200,
            log_field="amount",
            retry="not_retryable",
            amount=body.amount,
        )
    else:
        row = AuthorizationResponse(
            stop_step=5,
            sentence="There is no decline rule for this card.",
            http_status=400,
            log_field="card",
            retry="not_retryable",
        )
    save_log(row)
    return row
```

## 5. 창 A. Postgres와 Signet

Docker Desktop이 떠 있어야 한다. 이 창은 서버가 있는 동안 닫지 않는다. Fault Plate 폴더는 열지 않는다.

```powershell
. E:\IT_SPACES\AI\scripts\use_e_drive.ps1
Set-Location E:\IT_SPACES\AI\Projects\aidt\signet
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose -f E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml up -d
$env:DATABASE_URL = "postgresql://signet:signet@127.0.0.1:5433/signet"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

용도: E: 캐시로 패키지를 넣고, Postgres 다음에 Signet만 띄운다.
기능: 5433의 signet DB에 기록 표와 카드 표를 만든다.
이유: 카드 문장과 결제 기록이 같은 데이터베이스에 남는다.

`Application startup complete`가 보여야 한다. DB 연결 오류가 나면 그 글을 가져온다.

## 6. 창 B. 기록과 카드

본문은 파일로 보낸다.

```powershell
Set-Content -Path E:\IT_SPACES\AI\Projects\aidt\signet\_body.json -Value '{"amount":128,"card":"4242424242424242"}' -Encoding ascii -NoNewline
curl.exe -s -H "Content-Type: application/json" --data-binary "@E:\IT_SPACES\AI\Projects\aidt\signet\_body.json" http://127.0.0.1:8001/authorizations
Set-Content -Path E:\IT_SPACES\AI\Projects\aidt\signet\_plate.json -Value '{"name":"declined","user_facing_message":"This card was declined.","http_status":400,"log_fields":"amount","retry_allowed":"not_retryable"}' -Encoding ascii -NoNewline
curl.exe -s -D - -H "Content-Type: application/json" --data-binary "@E:\IT_SPACES\AI\Projects\aidt\signet\_plate.json" http://127.0.0.1:8001/plates
```

용도: 승인 한 줄과 거절 카드 한 장을 같은 서버에 남긴다.
기능: 승인 JSON이 먼저 나오고, 카드 POST는 `HTTP/1.1 201`과 방금 쓴 문장을 돌려준다.
이유: 두 번째 배포 없이 덮어쓰기가 이 서버에서 끝나는지 본다.

창 A에서 Ctrl+C로 Signet만 끄고, 같은 `DATABASE_URL` 다음에 uvicorn 줄을 다시 실행한다.
Postgres 컨테이너도 한 번 재시작한다.

```powershell
docker compose -f E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml restart
docker compose -f E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml exec -e PGPASSWORD=signet postgres psql -U signet -d signet -c "SELECT sentence, amount FROM authorization_log ORDER BY id DESC LIMIT 3;"
curl.exe -s http://127.0.0.1:8001/plates
Set-Content -Path E:\IT_SPACES\AI\Projects\aidt\signet\_body.json -Value '{"amount":128,"card":"4000000000000002"}' -Encoding ascii -NoNewline
curl.exe -s -H "Content-Type: application/json" --data-binary "@E:\IT_SPACES\AI\Projects\aidt\signet\_body.json" http://127.0.0.1:8001/authorizations
```

용도: 프로세스를 끈 뒤에도 두 줄이 남았는지 읽는다.
기능: Postgres에서 승인 문장을 읽고, 8001의 카드를 다시 읽어 그 문장으로 거절 POST를 보낸다.
이유: 이번 게이트의 완료는 재시작 후의 기록과 카드 문장이다.

확인:
1. psql 결과에 `Payment completed.` 와 `128` 이 있다. 카드 번호 열도 카드 번호 전체도 없다.
2. `GET /plates` 의 `user_facing_message` 는 `This card was declined.` 이다.
3. 거절 POST의 `sentence` 도 `This card was declined.` 이고 `stop_step` 은 5 이다.
4. 출력 어디에도 `4242424242424242` 와 `4000000000000002` 는 없다.
5. 호출 주소는 모두 `127.0.0.1:8001` 이다.

이 게이트의 스크린샷은 없다.
