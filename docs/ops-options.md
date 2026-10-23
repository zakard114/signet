# Ops 확인

같은 내용을 보는 방법이 두 가지다. 카드 번호 전체는 어느 쪽에도 넣지 않는다.

## 옵션 1. 주소를 연다

로컬 앱이 떠 있는 동안 주소를 직접 연다.

- 거절 카드: http://127.0.0.1:8001/plates
- 기관 규칙: http://127.0.0.1:8001/rules
- 승인 기록: http://127.0.0.1:8001/logs
- API 문서: http://127.0.0.1:8001/docs
- Grafana: http://127.0.0.1:3001 에서 Loki 질의 `{service_name="signet"}`

Grafana는 이 PC의 Compose에만 있다. 공개 서버에는 올리지 않는다.

## 옵션 2. Ops 탭을 누른다

1. http://127.0.0.1:8001 을 연다.
2. 오른쪽 위의 Ops를 누른다. 결제 애니메이션 중에는 그 버튼이 꺼져 있다.
3. 탭을 하나씩 연다. 한 번에 하나만 보인다.

- Card. 거절 카드 한 장의 이름, 고객 문장, HTTP 상태, 로그 필드, 재시도를 아래로 쌓아 보여 준다.
- Rule. 위에는 기관 규칙, 고객 문장, HTTP 상태, 로그 필드, 재시도, 금액 한도를 직접 고친다. Set rule 아래에는 `Institution rule saved.`가 뜬다. 아래 CSV는 첫 데이터 행으로 같은 규칙을 덮는다. 저장 뒤에는 이전 값과 새 값을 칸마다 대조한다.
- Log. 승인 문장과 금액을 보여 준다. 승인은 연한 녹색, 거절은 붉은색이다. 금액이 저장되지 않은 예전 행은 금액을 비워 둔다.
- API. 이 앱의 경로 목록과 로컬 문서를 보여 준다.
- Grafana. 탭 안에 요청 수, HTTP 에러율, 평균 지연, 상태별 초당 요청, P95와 P99, 감사 로그가 있다. 로그는 시간, 상태, 메서드, 경로, 지연, trace_id 칸으로 고정폭 표다. `/favicon.ico` 같은 브라우저 정적 요청은 표에 넣지 않는다. 로그의 상태 번호와 trace_id를 누르면 그 요청만 남는다. 카드 번호는 없다. 이 PC의 Grafana 전체 화면은 http://127.0.0.1:3001/d/signetpay/signet 이고, 추적 화면은 http://127.0.0.1:3001/d/signettrace/signet-trace 이다. Grafana 서버는 공개 주소로 올리지 않는다.

옵션 1의 주소가 옵션 2 탭 안의 내용과 같다.

## 규칙 파일

Rule file에 붙이는 텍스트의 첫 데이터 행만 기관 규칙이 된다.

- CSV이고 첫 줄에 `code`와 `sentence`가 있으면 그 다음 행을 읽는다. 칸은 `code`, `sentence`, `http_status`, `log_field`(또는 `log_fields`), `retry`, `amount_limit`이다.
- `http_status`는 100에서 599다. 비었거나 그 밖이면 400이다. 이 숫자는 달러가 아니다.
- `amount_limit`는 결제 한도다. 칸이 없으면 500이다. 0보다 크고 100000 이하만 받는다.
- `retry`는 `retryable` 또는 `not_retryable`이다. 그 밖이면 `not_retryable`이다.
- 헤더가 없으면 첫 줄 전체를 고객 문장으로 보고, 코드는 `institution`, 상태는 400, 로그 필드는 `card`, 재시도는 `not_retryable`, 한도는 500이다.
- 파일 이름이나 글에 숫자가 13자리 이상 이어지면 거절하고 저장하지 않는다.

한도는 모든 결제에 적용된다. 고객 문장은 승인 카드와 거절 카드가 아닌, 자릿수가 맞는 카드가 5단계에 도달했을 때만 쓰인다.

예제 파일은 두 개다. 아직 붙이지 않은 파일을 Rule file에서 고르면 What changed가 이전 규칙과 대조한다.

- `samples/institution-limit.csv`. 한도 400. 코드 `unknown_card`, HTTP 400, 로그 필드 `card`, 재시도 `retryable`.
- `samples/institution-higher.csv`. 한도 800. 코드 `raised_limit`, 문장이 다르고, HTTP 403, 로그 필드 `amount`, 재시도 `not_retryable`.
