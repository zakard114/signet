# (3/11) API Contract

업계 이름: API Contract.
이번 화면에서: 승인 요청과 Fault Plate 카드 읽기가 어떤 JSON인지를 파일 하나로 고정한다.

목표: `openapi.yaml` 파일을 새로 만든다.
완료: 그 파일에 POST /authorizations 와 GET /plates 만 있다.
하지 말 것: 서버 코드, 설치, git, Postgres, Docker, 화면 수정, 4/11.

경로: `E:\IT_SPACES\AI\Projects\aidt\signet\openapi.yaml`
폴더 `E:\IT_SPACES\AI\Projects\aidt\signet\` 에 새 파일을 만들고 아래 내용만 넣는다.

```yaml
openapi: 3.0.3
info:
  title: Signet
  version: 0.1.0
paths:
  /authorizations:
    post:
      summary: Request authorization
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [amount, card]
              properties:
                amount:
                  type: number
                card:
                  type: string
      responses:
        "200":
          description: Approved or stopped
          content:
            application/json:
              schema:
                type: object
                required: [sentence, http_status, log_field, retry]
                properties:
                  stop_step:
                    type: integer
                    nullable: true
                  sentence:
                    type: string
                  http_status:
                    type: integer
                  log_field:
                    type: string
                  retry:
                    type: string
                    enum: [retryable, not_retryable]
                  amount:
                    type: number
  /plates:
    get:
      summary: Read the one Fault Plate card
      responses:
        "200":
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
        "404":
          description: No card saved
          content:
            application/json:
              schema:
                type: object
                required: [detail]
                properties:
                  detail:
                    type: string
```

응답에는 카드 번호 전체를 넣지 않는다. 이 게이트의 스크린샷은 없다.

확인: 파일을 다시 열었을 때 paths 아래에 /authorizations 와 /plates 만 보인다.
