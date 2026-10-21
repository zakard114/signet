# (4/11) Backend Implementation

업계 이름: Backend Implementation.
이번 화면에서: 계약의 승인 POST가 한도, 자릿수, 승인 카드, 거절 카드에 따라 다른 JSON을 돌려준다.

목표: Signet 서버가 POST /authorizations 만 응답한다. GET /plates 는 Fault Plate를 읽는다.
완료: 아래 네 요청의 JSON이 확인된다.
하지 말 것: Postgres, Docker, 화면 수정, 테스트 파일, git, 5/11.

폴더: E:\IT_SPACES\AI\Projects\aidt\signet\

만들 파일 1. requirements.txt

```text
fastapi
uvicorn
```

만들 파일 2. app\__init__.py
빈 파일이다.

만들 파일 3. app\main.py

```python
import json
import os
import urllib.request
from typing import Literal, Optional

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Signet", version="0.1.0")
LIMIT = 500
PLATE_URL = os.environ.get(
    "FAULT_PLATE_URL", "https://fault-plate.onrender.com/plates"
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


def digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def plate_decline() -> AuthorizationResponse:
    try:
        with urllib.request.urlopen(PLATE_URL, timeout=10) as response:
            body = json.loads(response.read().decode())
        return AuthorizationResponse(
            stop_step=5,
            sentence=body["user_facing_message"],
            http_status=body["http_status"],
            log_field=body["log_fields"],
            retry=body["retry_allowed"],
        )
    except Exception:
        return AuthorizationResponse(
            stop_step=5,
            sentence="We could not complete your payment.",
            http_status=400,
            log_field="amount",
            retry="not_retryable",
        )


@app.post("/authorizations")
def authorize(body: AuthorizationRequest) -> AuthorizationResponse:
    pan = digits(body.card)
    if body.amount <= 0 or body.amount > LIMIT:
        return AuthorizationResponse(
            stop_step=2,
            sentence="This amount is above the limit.",
            http_status=400,
            log_field="amount",
            retry="retryable",
        )
    if not 13 <= len(pan) <= 19:
        return AuthorizationResponse(
            stop_step=3,
            sentence="The card number length is not valid.",
            http_status=400,
            log_field="card",
            retry="retryable",
        )
    if pan == "4000000000000002":
        return plate_decline()
    if pan == "4242424242424242":
        return AuthorizationResponse(
            sentence="Payment completed.",
            http_status=200,
            log_field="amount",
            retry="not_retryable",
            amount=body.amount,
        )
    return AuthorizationResponse(
        stop_step=5,
        sentence="There is no decline rule for this card.",
        http_status=400,
        log_field="card",
        retry="not_retryable",
    )
```

응답 JSON에 card 필드는 없다.

실행. 창 A. 이 창은 닫지 않는다.

```powershell
. E:\IT_SPACES\AI\scripts\use_e_drive.ps1
Set-Location E:\IT_SPACES\AI\Projects\aidt\signet
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

용도: E: 캐시 뒤에 서버를 띄운다.
기능: 8001에서 승인 POST를 받는다.
이유: 계약의 네 갈래를 이 게이트에서 확인한다. 8000은 Fault Plate가 쓸 수 있다.

창 B. 서버 창이 떠 있는 동안 네 번 호출한다.

PowerShell 5는 curl.exe에 넘기는 JSON의 큰따옴표를 지운다. 본문을 파일에 쓴 뒤 `--data-binary`로 보낸다.

```powershell
Set-Content -Path E:\IT_SPACES\AI\Projects\aidt\signet\_body.json -Value '{"amount":860,"card":"4242424242424242"}' -Encoding ascii -NoNewline
curl.exe -s -H "Content-Type: application/json" --data-binary "@E:\IT_SPACES\AI\Projects\aidt\signet\_body.json" http://127.0.0.1:8001/authorizations
Set-Content -Path E:\IT_SPACES\AI\Projects\aidt\signet\_body.json -Value '{"amount":128,"card":"4242"}' -Encoding ascii -NoNewline
curl.exe -s -H "Content-Type: application/json" --data-binary "@E:\IT_SPACES\AI\Projects\aidt\signet\_body.json" http://127.0.0.1:8001/authorizations
Set-Content -Path E:\IT_SPACES\AI\Projects\aidt\signet\_body.json -Value '{"amount":128,"card":"4242424242424242"}' -Encoding ascii -NoNewline
curl.exe -s -H "Content-Type: application/json" --data-binary "@E:\IT_SPACES\AI\Projects\aidt\signet\_body.json" http://127.0.0.1:8001/authorizations
Set-Content -Path E:\IT_SPACES\AI\Projects\aidt\signet\_body.json -Value '{"amount":128,"card":"4000000000000002"}' -Encoding ascii -NoNewline
curl.exe -s -H "Content-Type: application/json" --data-binary "@E:\IT_SPACES\AI\Projects\aidt\signet\_body.json" http://127.0.0.1:8001/authorizations
```

용도: 네 갈래 JSON을 깨지지 않게 보낸다.
기능: 본문 파일을 8001의 승인 POST에 붙인다.
이유: 한 줄 `-d`는 PowerShell이 따옴표를 지워 JSON decode error가 난다.

확인:
1. 860 은 stop_step 2, sentence 는 This amount is above the limit.
2. 4242 는 stop_step 3, sentence 는 The card number length is not valid.
3. 4242424242424242 는 sentence 가 Payment completed. 이고 amount 가 128 이다. stop_step 은 null 이다.
4. 4000000000000002 는 stop_step 5 이다. Fault Plate가 응답하면 그 문장이고, 실패하면 We could not complete your payment. 이다.
5. 네 JSON 어디에도 카드 번호 전체는 없다.

이 게이트의 스크린샷은 없다.
