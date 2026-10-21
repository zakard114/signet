# (8/11) Deployment

업계 이름: Deployment.
이번 화면에서: `main`은 개발 주소로 올라가고, 프로덕션은 사람이 실행한다. 공개 주소가 응답하고, 이전 이미지로 되돌리는 문장이 문서에 있다.

목표: Signet을 GitHub에 두고 Render에 Docker로 한 번 배포한다. Postgres도 Render에 붙인다.
완료: 공개 URL의 `/` 가 결제 화면을 주고, `POST /authorizations` 가 응답한다. README에 되돌리기 문장이 있다.
하지 말 것: AWS, Fault Plate를 다시 배포하기, 9/11 텔레메트리, 로컬 Compose 삭제, `AIDT_proj_signet.txt` 커밋.

이미 있는 것:
- `E:\IT_SPACES\AI\Projects\aidt\signet\Dockerfile`
- `E:\IT_SPACES\AI\Projects\aidt\signet\docker-compose.yaml`
- 로컬 Compose는 그대로 둔다. 공개 배포는 별도다.
- 배포 형식은 이전 프로젝트 Fault Plate의 Render Docker를 가져온다. 저장소와 서비스 이름만 Signet이다. Fault Plate 서비스를 지우지 않아도 되고, 슬롯이 모자라면 그 서비스를 나중에 지운다.

## 1. Dockerfile이 Render PORT를 읽게 한다

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\Dockerfile`
파일 전체를 아래로 바꾼다.

용도: 공개 호스트가 주는 포트에서 서버가 뜬다.
기능: `PORT` 환경 변수가 있으면 그 번호를 쓰고, 없으면 8001을 쓴다.
이유: Render는 컨테이너 포트를 `PORT`로 넘긴다. 로컬 Compose는 그대로 8001이다.

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY preview ./preview
EXPOSE 8001
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
```

## 2. .gitignore

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\.gitignore`
새 파일이다.

용도: 가상환경, 캐시, 개인 메모, 임시 JSON을 저장소에 넣지 않는다.
기능: Git이 그 경로를 무시한다.
이유: 공개 저장소에 카드 본문 파일과 로컬 DB 폴더가 올라가면 안 된다.

```text
.venv/
.pytest_cache/
__pycache__/
*.pyc
docker/pgdata/
_body.json
_plate.json
_home.html
AIDT_proj_signet.txt
.env
```

## 3. 공개 README (영어)

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\README.md`
새 파일이다. 공개 문서라 영어다. 아래 전체를 넣는다. Live URL은 배포 뒤 실제 주소로 바꾼다.

용도: 공개 주소와 되돌리기 방법을 한 문서에 둔다.
기능: 미션, 로컬 Compose, Render 배포, rollback 문장을 적는다.
이유: 이번 게이트 완료 조건에 이전 이미지로 되돌리는 문장이 있다.

README.md에 넣을 본문 (이 블록 전체를 파일에 그대로 둔다):

~~~~
# Signet

One checkout screen. Six steps. The stop sentence stays on the same panel.

**Live app:** (paste the Render URL here after deploy)

## Local

docker compose -f docker-compose.yaml up -d --build

Open http://127.0.0.1:8001/

## Deploy

Render web service, Docker, branch `main`, free instance, plus Render Postgres.

Set `DATABASE_URL` to the Render Postgres connection string.

`main` auto-deploys to the development service. Production is a manual deploy the human starts in the Render dashboard (or a deploy hook the human triggers).

The image listens on Render's `PORT`:

uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}

## Rollback

Keep the previous deploy in Render. To go back, open the service → Events (or Deploys) → select the earlier successful deploy → Rollback. The previous image serves again. Do not delete that older deploy until the new one is confirmed.
~~~~

## 4. GitHub에 올린다

이 폴더에 Git이 아직 없다. 파워셸에서:

```powershell
. E:\IT_SPACES\AI\scripts\use_e_drive.ps1
Set-Location E:\IT_SPACES\AI\Projects\aidt\signet
git init
git add Dockerfile docker-compose.yaml requirements.txt openapi.yaml README.md .gitignore app preview tests docs/packets SPEC.md ROADMAP.md
git status
```

용도: 공개에 올릴 파일만 스테이징한다.
기능: `git status`에 `.venv`, `AIDT_proj_signet.txt`, `_body.json`이 없어야 한다.
이유: 개인 메모와 로컬 데이터는 커밋하지 않는다.

스테이징이 맞으면:

```powershell
git commit -m "Add Signet app with Compose and Render-ready image"
gh repo create signet --public --source=. --remote=origin --push
```

용도: GitHub에 공개 저장소를 만들고 `main`을 올린다.
기능: `gh`가 origin을 만들고 첫 push를 한다.
이유: Render가 그 저장소의 Docker 빌드를 받게 한다.

`gh` 로그인 창이 뜨면 브라우저에서 승인한다. 저장소 이름이 이미 있으면 `signet-checkout`처럼 다른 이름을 쓴다. 나온 GitHub URL을 메모한다.

## 5. Render에 배포한다

브라우저에서 https://dashboard.render.com 을 연다.

1. **New +** → **Postgres** → Free. 이름은 `signet-db`. Create 후 **Connections**의 Internal Database URL을 복사한다.
2. **New +** → **Web Service** → Signet GitHub 저장소를 고른다.
3. Runtime은 **Docker**. Branch는 `main`.
4. Instance는 Free.
5. Environment에 `DATABASE_URL` = 방금 복사한 Postgres URL.
6. Health Check Path는 비운다. (Fault Plate와 같다.)
7. Create Web Service.

용도: 공개 주소 하나와 DB 하나를 Signet에만 둔다.
기능: `main` push가 개발 서비스를 다시 빌드한다. 프로덕션은 대시보드에서 사람이 Manual Deploy한다.
이유: 로드맵의 “main은 개발 주소, 프로덕션은 사람이 실행”이다. Fault Plate 앱을 두 번째로 올리지 않는다.

서비스가 Live가 되면 공개 URL을 복사해 `README.md`의 Live app 줄에 넣고 다시 커밋·push한다.

## 6. 공개 주소 확인

브라우저에서 그 공개 URL을 연다. Signet 결제 화면이 보여야 한다.

파워셸에서 (URL은 본인 주소로 바꾼다):

```powershell
Set-Content -Path E:\IT_SPACES\AI\Projects\aidt\signet\_body.json -Value '{"amount":128,"card":"4242424242424242"}' -Encoding ascii -NoNewline
curl.exe -s -H "Content-Type: application/json" --data-binary "@E:\IT_SPACES\AI\Projects\aidt\signet\_body.json" https://YOUR-SERVICE.onrender.com/authorizations
```

용도: 공개 서버에 승인 POST를 보낸다.
기능: `Payment completed.` JSON이 돌아온다.
이유: 화면만 열린 것이 아니라 API와 Postgres도 공개 주소에서 산다.

확인:
1. 공개 URL의 `/` 에 Signet 결제 화면이 있다.
2. 승인 curl의 `sentence` 가 `Payment completed.` 이다. 카드 번호 전체가 없다.
3. `README.md`에 Rollback 절이 있다.
4. Render 서비스는 Signet 하나다. Fault Plate를 이 게이트에서 다시 만들지 않았다.

공개 URL 화면 캡처 한 장을 가져온다. 처음 요청은 free instance 깨우는 데 수십 초 걸릴 수 있다.
