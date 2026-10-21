# (7/11) Containerization

업계 이름: Containerization.
이번 화면에서: 화면과 서버를 이미지 하나에 담고, Compose가 Postgres를 같이 띄운다.

목표: Dockerfile 하나로 앱을 만들고, `docker-compose.yaml`이 앱과 Postgres를 함께 올린다.
완료: `http://127.0.0.1:8001/` 에서 결제 화면이 열리고, 같은 주소의 `POST /authorizations` 가 응답한다.
하지 말 것: 공개 배포, Render, git, 8/11, 텔레메트리 스택, 테스트 파일 수정.

이미 있는 것:
- `E:\IT_SPACES\AI\Projects\aidt\signet\app\main.py`
- `E:\IT_SPACES\AI\Projects\aidt\signet\preview\index.html`
- `E:\IT_SPACES\AI\Projects\aidt\signet\requirements.txt`
- `E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml` (지금은 Postgres만 있다)
- Dockerfile 모양은 이전 프로젝트 `E:\IT_SPACES\AI\Projects\aidt\fault-plate\Dockerfile`을 가져온다. 포트와 복사할 폴더만 Signet에 맞춘다.

## 1. 앱이 미리보기를 연다

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\app\main.py`
파일 맨 위 import 구역에 두 줄을 더하고, `authorize` 함수 **위**에 홈 경로를 넣는다. 다른 승인·카드 코드는 건드리지 않는다.

용도: 같은 서버가 결제 화면 HTML을 돌려준다.
기능: `/` 가 `preview/index.html` 을 연다.
이유: 이미지 하나에 화면과 API가 같이 있어야 Compose로 결제 화면이 열린다.

import에 추가:

```python
from pathlib import Path

from fastapi.responses import FileResponse
```

`startup` 함수 아래에 추가:

```python
PREVIEW = Path(__file__).resolve().parent.parent / "preview"


@app.get("/")
def home():
    return FileResponse(PREVIEW / "index.html")
```

## 2. Dockerfile

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\Dockerfile`
새 파일이다.

용도: 화면과 서버를 이미지 하나에 담는다.
기능: 패키지를 설치하고 `app`과 `preview`를 넣은 뒤 8001에서 uvicorn을 켠다.
이유: 로컬 Compose와 나중 배포가 같은 이미지를 쓴다.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY preview ./preview
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

## 3. docker-compose.yaml

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml`
파일 전체를 아래로 바꾼다. Postgres 데이터는 계속 E:에 둔다.

용도: 앱 이미지와 Postgres를 같이 띄운다.
기능: 앱은 `postgres` 이름으로 DB에 붙고, 이 PC의 8001로 화면을 연다.
이유: 이번 게이트 완료는 로컬 Compose로 결제 화면이 열리는 것이다.

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
  app:
    build: .
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgresql://signet:signet@postgres:5432/signet
    depends_on:
      - postgres
```

## 4. 실행

Docker Desktop이 Engine running이어야 한다. 예전에 켜 둔 호스트 uvicorn이 8001을 쓰면 Ctrl+C로 끈다.

```powershell
. E:\IT_SPACES\AI\scripts\use_e_drive.ps1
Set-Location E:\IT_SPACES\AI\Projects\aidt\signet
docker compose -f E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml up -d --build
```

용도: 이미지를 만들고 앱과 Postgres를 백그라운드로 올린다.
기능: `signet-app-1`과 `signet-postgres-1`이 Up이 된다.
이유: 브라우저가 컨테이너 안의 화면을 열게 한다.

Postgres가 받기 전에 앱이 한 번 실패하면 잠시 뒤 다시 올린다.

```powershell
docker compose -f E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml up -d
docker compose -f E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml ps
```

브라우저 주소창에 `http://127.0.0.1:8001/` 을 넣고 엔터한다. Signet 결제 화면이 보여야 한다.

창 B에서 승인 한 번:

```powershell
Set-Content -Path E:\IT_SPACES\AI\Projects\aidt\signet\_body.json -Value '{"amount":128,"card":"4242424242424242"}' -Encoding ascii -NoNewline
curl.exe -s -H "Content-Type: application/json" --data-binary "@E:\IT_SPACES\AI\Projects\aidt\signet\_body.json" http://127.0.0.1:8001/authorizations
```

용도: Compose로 뜬 같은 서버에 승인 POST를 보낸다.
기능: `Payment completed.` JSON이 돌아온다.
이유: 화면만 열린 것이 아니라 API도 이미지 안에서 산다.

확인:
1. 브라우저에 Signet 결제 화면이 있다. Authorize와 Ops가 보인다.
2. `docker compose ... ps` 에 app과 postgres가 Up이다.
3. 승인 curl의 `sentence` 가 `Payment completed.` 이다.
4. 응답에 카드 번호 전체가 없다.

화면이 열리면 그 창을 캡처해 가져온다.
