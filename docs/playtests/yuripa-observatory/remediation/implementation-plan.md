# 시나리오 인식 플레이 안정화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 장면 규칙에 따른 검증 가능한 행동 판정과 분기 서술을 제공하고, 외부 API·Discord 버튼·SQLite 로컬 실행의 장애가 플레이 기록을 끊지 않게 한다.

**Architecture:** Google Docs에서 선택적 구조화 규칙을 파싱한다. Gemini는 플레이어 행동을 등록된 규칙 ID에 연결하고, Python 코드가 캐릭터 기능값·굴림·결과 문구를 결정한다. 낭독 뷰는 데이터베이스에 저장된 진행 위치로 재등록되며 SQLite는 Docker named volume을 쓴다.

**Tech Stack:** Python 3.12, discord.py, google-genai, SQLite, Docker Compose, pytest.

**Spec:** `docs/playtests/yuripa-observatory/remediation/design.md`

## Global Constraints

- 외부 배포 없이 로컬 Docker에서 검증한다.
- 새 의존성을 추가하지 않는다.
- 규칙 없는 기존 시나리오 파싱을 유지한다.
- 모델은 주사위 결과, 기능값, 성공 등급 또는 임의의 분기 문구를 결정하지 않는다.
- API 오류는 비밀 키나 전체 요청 본문을 공개하지 않는다.
- SQLite 런타임 데이터는 호스트 파일 bind mount가 아닌 named volume에 둔다.

## Review Focus

- 규칙이 없는 문서에서 기존 `/행동` 응답과 낭독이 깨지는 경우: parser 및 action 기본 동작 테스트.
- 모델이 알 수 없는 규칙 ID나 다른 스킬을 반환하는 경우: 거부하고 굴림하지 않는 테스트.
- 모델 요청이 503/429/제한시간/파싱 오류를 반환하는 경우: 짧고 구체적인 후속 응답 테스트.
- 재시작 뒤 낡은 버튼/투표가 남는 경우: 현재 위치 검증과 투표 재설정 테스트.
- 마지막 줄 완료와 Docker named volume 재기동 상태: 저장소 및 compose 실행 검증.

---

### Task 1: 시나리오별 판정 규칙 파싱

**Files:**
- Modify: `scenario_parser.py`
- Modify: `docs/playtests/yuripa-observatory/scenario.md`
- Test: `tests/test_scenario_parser.py`

**Interfaces:** 장면 데이터에 선택적 `checks` 배열을 추가한다. 각 규칙은 고정 `id`, 권장 `skill`, 행동 설명, 성공 문구, 실패 문구를 가진다. `lines`는 기존과 같은 순서·형식으로 유지한다.

규칙은 해당 장면의 `Checks` 제목 아래 Docs export HTML 표에서만 읽는다. 표 헤더는 `id`, `skill`, `action`, `success`, `failure`이며 parser는 ID 중복, 빈 값, 미등록 기능명을 가진 행을 건너뛴다. 기존 `h1/h2/h3/p` 추출은 바꾸지 않는다. 실제 Google Docs export와 같은 heading/paragraph/table 구조의 fixture로 호환성을 고정한다. Markdown 자체는 현재 지원하지 않는다.

- [ ] 구조화 판정 헤더를 포함한 HTML fixture를 추가하고 규칙 ID/기능/성공·실패 문구를 검증한다.
- [ ] 기존 문서 fixture를 실행해 기존 장면/문장이 그대로 파싱되는지 확인한다.
- [ ] Google Docs export HTML의 고정 `Checks` 제목/표 행 형식으로 parser를 구현한다. Markdown parser는 추가하지 않는다.
- [ ] `pytest tests/test_scenario_parser.py -q`로 통과를 확인한다.

### Task 2: 시나리오 인식 행동 분석과 안전한 굴림

**Files:**
- Modify: `intent_analyzer.py`
- Modify: `bot/cogs/action.py`
- Modify: `bot/embeds.py` (필요한 경우만)
- Test: `tests/test_intent_analyzer.py`, `tests/test_action_cog.py`

**Interfaces:** analyzer에 허용 규칙 후보를 전달하고 `check_id`를 반환한다. 기존 시나리오가 없거나 규칙 후보가 없으면 자동 분기/굴림을 가장하지 않는다. action cog는 현재 채널 시나리오 위치와 PC를 조회한다.

판정 결과 등급은 기존 `dice.determine_success_level()`을 쓴다. critical/extreme/hard/regular은 성공, fail/fumble은 실패 문구로 매핑한다. 후보가 없거나 매칭 ID가 없거나 알 수 없거나 모델 confidence가 0.6 미만이면 굴리지 않고 `/판정` 안내를 보낸다. 모델이 지정한 skill은 참고하지 않고, ID에 저장된 skill과 등록된 기능값만 굴림 입력으로 쓴다. 외부 요청은 재시도하지 않는다. HTTP 401/403, 429, 5xx, network/timeout, 빈 응답, 안전 차단, malformed JSON/schema를 각각 사용자 안내로 종료하고 민감한 prompt/response를 로그에 쓰지 않는다.

- [ ] 시나리오 규칙 후보를 포함하는 analyzer 테스트를 먼저 추가하고 실패를 확인한다.
- [ ] 미등록 `check_id`, 기능 불일치, 불확실한 결과가 굴림을 만들지 않는 테스트를 추가한다.
- [ ] API 503/429, 네트워크 오류, 제한시간 및 응답 파싱 오류를 별도 사용자 안내로 끝내는 테스트를 추가한다.
- [ ] 해당 테스트를 통과하도록 action 흐름을 수정한다. 자동 재시도는 구현하지 않는다.
- [ ] 규칙별 기능값으로 주사위를 굴리고, 결과 등급으로 성공/실패 서술을 선택하는 테스트를 추가한다.
- [ ] 성공/실패 결과가 사용자 응답에 기록되며 기존 시나리오의 수동 동작이 보존되는지 확인한다.
- [ ] `pytest tests/test_intent_analyzer.py tests/test_action_cog.py -q` 실행.

### Task 3: 재시작 안전 낭독과 완료 표시

**Files:**
- Modify: `bot/cogs/narration.py`
- Modify: `bot/main.py`
- Modify: `bot/cogs/scenario.py` 또는 `bot/embeds.py` (완료 상태 표시 위치에 따라)
- Test: `tests/test_narration_cog.py`, `tests/test_narration_view.py`, `tests/test_embeds.py`, 필요 시 `tests/test_main.py`

**Interfaces:** persistent custom ID에 시나리오 및 낭독 위치를 포함한다. 봇 시작 시 저장된 모든 시나리오의 모든 줄 위치를 등록해 재시작 전 메시지의 오래된 custom ID도 라우팅한다. callback은 DB 위치를 재검증해 낡은 버튼을 처리한다. 투표는 메모리 상태이므로 재시작 시 초기화한다. 같은 Discord ID가 Keeper/PC 양쪽이면 고유 참가자 한 명이다.

- [ ] 중복/낡은 위치와 참가자 정족수(특히 같은 Discord ID가 Keeper/PC에 쓰이는 경우)를 검증하는 테스트를 먼저 추가한다.
- [ ] 마지막 진행 위치가 `len(structure)`일 때 완료를 반환하고 조회가 “완료”를 표시하는 테스트를 추가한다.
- [ ] Persistent view 등록 및 재시작 후 현재 버튼 재개 동작을 구현한다. 모든 저장된 시나리오 위치의 custom ID를 등록해 과거 메시지의 버튼도 callback으로 받고 stale 응답을 준다.
- [ ] 모든 낭독 테스트와 `pytest tests/test_narration_cog.py tests/test_narration_view.py tests/test_embeds.py tests/test_main.py -q`를 실행한다.

### Task 4: Named volume 로컬 Docker 실행 및 절차 문서화

**Files:**
- Create: `compose.yaml`
- Modify: `README.md`
- Test: 실행 절차 self-check 또는 Docker 검증 기록

**Interfaces:** `docker compose up --build`가 `.env`를 사용하고 `coc-bot-data` named volume을 `/app/data`에 연결한다. host port는 loopback에만 노출한다.

기존 volume 이름이 있으면 명시적으로 재사용한다. 새 빈 volume은 자동으로 기존 `./data`를 가져오지 않는다. 기존 bind-mount SQLite를 이전하는 운영 절차는 봇을 중지한 뒤 SQLite backup API로 복제하고, volume 내부로 가져온 후 `PRAGMA integrity_check`를 확인하는 방식으로 README에 기록한다. 라이브 DB/WAL 직접 복사는 금지한다.

- [ ] compose 설정이 named volume을 쓰고 host `./data` bind mount를 쓰지 않는지 확인한다.
- [ ] 비밀 값 없이 `.env.example`로 실행 변수를 설명한다.
- [ ] 실제 `.env` 내용을 출력하지 않고 `docker compose config -q`, named volume 이름 확인, 로컬 컨테이너 기동, `/health` 200, `PRAGMA integrity_check`, DB 진행 위치 변경 후 `docker compose down` / `up` 뒤 동일 진행 위치를 검증한다. 출력은 비밀 없이 기록한다.

### Task 5: 원인 재현 및 종합 검증 기록

**Files:**
- Create: `docs/playtests/yuripa-observatory/remediation/reproduction-and-root-causes.md`
- Create: `docs/playtests/yuripa-observatory/remediation/verification-results.md`

- [ ] 과거 실행의 재현 가능한 증거와 이번 자동화 테스트 결과를 분리한다.
- [ ] 오류 횟수, 외부 API/Discord/SQLite 원인, 해결 커밋과 남은 제한을 기록한다.
- [ ] 전체 `pytest -q`를 실행하고 출력의 모든 실패/경고를 기록한다.
- [ ] Docker health, `PRAGMA integrity_check`, 재시작 후 진행 위치를 확인한다.
- [ ] 실제 Discord 정상 흐름이 필요한 경우 전용 채널에서 등록·장면 판정·SAN·분기·완료를 확인하되, Discord 주사위는 고정 RNG 증거로 사용하지 않는다.
- [ ] `/시나리오조회`가 마지막 줄 진행 후 완료로 표시되는지 assertion을 기록한다.

### Task 6: 커밋과 브랜치 정리

- [ ] 변경을 영역별 커밋으로 저장한다.
- [ ] `.mcp.json` 등 작업과 무관한 untracked 파일을 stage하지 않는다.
- [ ] 새 브랜치의 전체 diff와 최종 테스트 상태를 검토한다.

## 실행 규칙과 선후 관계

- Task 1에서 parser 계약을 고정하고 Task 2가 이를 소비한다.
- Task 2와 Task 3은 `bot/embeds.py`를 동시에 편집하지 않는다. Task 2 완료/검토 후 Task 3을 시작한다.
- Task 3은 storage API, narration cog, startup 등록을 함께 변경한다. Task 4 Compose는 별도로 진행할 수 있지만 구현 작업자는 하나씩 투입한다.
- 각 작업자는 자기 Task의 지정 파일만 수정하고 테스트 결과를 보고한다. 다음 Task 전 독립 검토를 진행한다.
- 각 도메인 변경은 테스트와 검토 완료 후 별도 커밋한다. 보고서와 README/Compose는 문서/운영 커밋으로 분리한다.
