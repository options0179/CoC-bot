# CoC-Bot

Call of Cthulhu 7판 판정(스킬 체크, SAN 체크, 대립판정, 푸시 롤)을 자동화하는
디스코드 슬래시 커맨드 봇. 판정 명령어 자체는 여전히 상태 없이(stateless) 그 자리에서
계산만 하지만, 이제 캐릭터시트 등록/조회 기능도 지원한다 — 플레이어가 구글 스프레드시트
링크나 웹 등록 폼으로 캐릭터시트를 등록하면 Postgres에 저장해두고 언제든 다시 조회할 수 있다.

## 커맨드

- `/판정 스킬값 [보너스] [페널티]` — d100 판정, 실패 시 푸시 버튼 첨부
- `/산정 현재san 손실식` — SAN 체크 (손실식 예: `1/1d4+1`)
- `/대립 내스킬 상대스킬` — 대립판정
- `/캐릭터등록열기` — 캐릭터 등록창을 연다 (연 사람만 닫을 수 있음)
- `/캐릭터등록닫기` — 본인이 연 등록창을 닫는다
- `/캐릭터등록 [링크]` — 등록창이 열려있을 때 캐릭터시트를 등록(재등록 시 덮어쓰기). `링크`(구글
  스프레드시트)를 생략하면 대신 웹 등록 폼 링크를 ephemeral로 받는다(30분·1회용)
- `/캐릭터조회 [유저]` — 등록된 캐릭터 조회 (생략 시 본인)
- `/시나리오등록 제목 링크:<구글독스 URL>` — 링크 공개된 구글독스 시나리오 문서를 가져와
  아웃라인(부/장면/Keeper 낭독)을 파싱해 등록한다
- `/시나리오시작 시나리오` — 현재 채널을 등록된 시나리오에 배정한다(그 시나리오의 키퍼만 가능)
- `/시나리오참가` — 본인의 PC를 현재 채널에 배정된 시나리오의 참가자 로스터에 추가한다
- `/시나리오조회` — 현재 채널에 배정된 시나리오의 진행 상황과 참가자를 보여준다
- `/시나리오캐릭터등록 시나리오 직책:<KPC|NPC> [링크]` — 그 시나리오의 키퍼만 KPC/NPC
  캐릭터시트를 등록할 수 있다(PC와 동일한 양식). `링크`를 생략하면 웹 등록 폼 링크를 받는다
- `/낭독시작` — 현재 채널 시나리오의 Keeper 낭독을 문장 단위로 출력하고, 참가자(PC+키퍼)의
  2/3가 "다음" 버튼에 동의하면 다음 문장으로 진행한다(KPC 대사는 자동화하지 않음)
- `/행동 설명` — 자유 서술 행동을 분석해 필요하면 스킬 판정을 자동으로 굴린다 (판정이 필요 없으면 서술만 응답)

## 작동 원리

**상태 없는(stateless) 구조 + 선택적 데이터 저장.** 기본 판정 명령어(`/판정`, `/산정`,
`/대립`)은 어디에도 데이터를 저장하지 않는다. 스킬값이나 현재 SAN을 커맨드 인자로
받아 그 자리에서 계산하고 결과만 응답한다. 다만 캐릭터시트 등록 기능(`/캐릭터등록열기`,
`/캐릭터등록닫기`, `/캐릭터등록`, `/캐릭터조회`)은 사용자의 등록된 캐릭터를 Postgres에
저장하고 조회한다. `CoCBot.setup_hook()`이 cog를 로드하기 전에 DB 커넥션 풀부터
만들기 때문에, 판정 명령어만 쓰더라도 Postgres 연결은 봇을 기동하는 데 필수다 —
`DATABASE_URL`이 없거나 접속에 실패하면 `/판정`, `/산정`, `/대립`을 포함해 봇 전체가
뜨지 않는다. 관리형 Postgres(Railway, Supabase 등)를 `DATABASE_URL`로 연결해서 쓰면 된다.

**3개 계층으로 분리:**

1. **`dice.py`** — CoC 7판 판정 규칙을 구현한, discord 라이브러리에 전혀 의존하지
   않는 순수 함수 모음. d100을 굴려 스킬값과 비교해 성공등급(크리티컬 → 익스트림
   → 하드 → 일반 → 실패 → 펌블)을 매기고, 보너스/페널티 주사위(10의 자리 주사위를
   추가로 굴려 유리한/불리한 값을 채택, 최대 ±2 상쇄), SAN 체크, 대립판정을
   계산한다. 이 파일만 떼어내서 discord 없이도 그대로 테스트할 수 있다.
2. **`bot/embeds.py`** — `dice.py`가 반환한 결과 객체를 한국어 Discord 임베드로
   포맷하는 순수 함수들. 여기에는 판정 로직이 전혀 없고 이미 계산된 결과를
   보여주는 방법만 담당한다.
3. **`bot/cogs/*.py`** — 실제 슬래시 커맨드로 노출하는 얇은 어댑터. 사용자 입력을
   받아 `dice.py` 함수를 호출하고, 결과를 `embeds.py`로 포맷해 Discord에 응답할
   뿐 자체적인 판정 로직은 갖지 않는다.

**요청 흐름 예시 (`/판정`):** 사용자가 `/판정 스킬값:60`을 입력하면
`CheckCog.check`가 `dice.roll_check(60)`을 호출 → 반환된 `CheckResult`를
`embeds.check_embed()`로 임베드에 담음 → 판정이 실패/펌블이면 재도전용
`PushView`(버튼)를 함께 첨부 → 완성된 메시지를 응답으로 보낸다.

**유일한 "상태": 푸시 롤 버튼.** `/판정`이 실패하면 붙는 `PushView`는
`discord.ui.View`로, 메모리에서 직전 판정 정보(스킬값·보너스·페널티)를 5분간
들고 있다가 버튼이 눌리면 재판정한다. DB에 쓰지 않으므로 프로세스가 재시작되면
사라지는데, 이는 의도된 트레이드오프다.

**에러 처리.** `bot/main.py`의 전역 에러 핸들러(`on_app_command_error`)가
`dice.py`에서 던진 `ValueError`(잘못된 다이스 표기, SAN 손실식 형식 오류 등)를
잡아 한국어 메시지로 사용자에게만 보이게(ephemeral) 응답한다. 각 cog는 이런
입력 검증 오류를 직접 처리하지 않고 이 전역 핸들러에 위임한다.

**봇 기동.** `bot/main.py`의 `main()`이 `DISCORD_TOKEN`, `DATABASE_URL`, `GEMINI_API_KEY`
환경변수를 모두 확인하고, 하나라도 없으면 기동을 중단한다. 연결되면 `CoCBot.setup_hook()`이
가장 먼저 `storage.create_pool()`로 Postgres 커넥션 풀을 만들고(스키마도 이때
생성/확인한다), 곧바로 `bot/web.py`의 aiohttp 웹 서버를 기동한다(Render의 헬스체크가
Discord 쪽 초기화 지연과 무관하게 통과하도록, cog 로드나 `tree.sync()`보다 먼저 포트를
연다). 이어서 일곱 cog(`check`/`sanity`/`opposed`/`character`/`scenario`/
`narration`/`action`)를 로드한 뒤 `tree.sync()`로 슬래시 커맨드를 Discord에 등록한다.

## 프로젝트 구조

```
CoC-Bot/
├── dice.py                      # CoC 7판 판정 로직 전체 (discord 비의존 순수 함수)
├── storage.py                    # Postgres 스키마 생성 + 등록창/캐릭터 CRUD (asyncpg)
├── sheet_parser.py                # xlsx 캐릭터시트 파싱 (openpyxl)
├── scenario_parser.py             # 구글독스 export?format=html → 부/장면/Keeper 낭독 파싱 (표준 라이브러리 html.parser)
├── intent_analyzer.py             # 자유 서술 텍스트 → 플레이어 의도 분석 (Gemini)
├── bot/
│   ├── main.py                  # 봇 엔트리포인트, DB 풀 생성, 웹 서버 기동, cog 로더, 전역 에러 핸들러
│   ├── web.py                    # 캐릭터 등록 API + 폼 페이지(web/dist)를 서빙하는 aiohttp 웹 서버
│   ├── embeds.py                # 판정/캐릭터/시나리오/낭독 결과 → 한국어 Discord 임베드 포맷
│   └── cogs/
│       ├── check.py             # /판정 커맨드 + PushView(재도전 버튼)
│       ├── sanity.py            # /산정 커맨드
│       ├── opposed.py           # /대립 커맨드
│       ├── character.py         # /캐릭터등록열기, /캐릭터등록닫기, /캐릭터등록, /캐릭터조회, /시나리오캐릭터등록 커맨드
│       ├── scenario.py          # /시나리오등록, /시나리오시작, /시나리오참가, /시나리오조회 커맨드
│       ├── narration.py         # /낭독시작 커맨드 + NarrationView(2/3 동의 투표 버튼)
│       └── action.py            # /행동 커맨드
├── tests/                       # bot/, dice.py, storage.py, sheet_parser.py 구조를 그대로 미러링하는 pytest 테스트
├── requirements.txt              # 의존성 고정 (discord.py, pytest, asyncpg, openpyxl, google-generativeai)
├── pytest.ini                    # pytest 설정 (pythonpath=.)
├── Dockerfile                    # 컨테이너 이미지 빌드 정의
├── .dockerignore                 # Docker 빌드 컨텍스트 제외 목록 (.env 등 시크릿 방지)
├── .env.example                  # 환경변수 템플릿 (DISCORD_TOKEN, DATABASE_URL, GEMINI_API_KEY)
├── .gitignore                    # git 추적 제외 목록
└── docs/superpowers/              # 설계 스펙 · 구현 계획 문서
```

파일별 상세:

| 경로 | 역할 |
|---|---|
| `dice.py` | d100 판정/성공등급, 보너스·페널티 주사위, 다이스 표기(`XdY+Z`) 파서, SAN 체크, 대립판정 — 판정 계산 로직 전부가 여기 있다. |
| `storage.py` | Postgres 스키마(`guild_settings`, `characters`, `scenarios`, `scenario_participants`, `registration_tokens`) 생성, 등록창 열기/닫기/조회, 캐릭터 upsert/조회(PC/KPC/NPC 역할·시나리오 귀속 포함), 시나리오 CRUD·채널 배정·참가자 로스터·낭독 진행 위치, 등록 토큰 발급/조회/소비 — DB 접근 전부가 여기 있다. |
| `sheet_parser.py` | 업로드된 xlsx 캐릭터시트를 openpyxl로 읽어 라벨-값 쌍을 딕셔너리로 파싱, 형식이 잘못되면 `ValueError` (PC/KPC/NPC 공통 양식) |
| `scenario_parser.py` | 구글독스 `export?format=html`을 `html.parser.HTMLParser`로 파싱해 h1(부)/h2(장면)/h3(소제목) 아웃라인을 읽고, "Keeper"로 시작하는 h3 구간의 본문만 문장 단위로 추출한다. 「」로 감싼 대사는 한 문장으로 유지 |
| `intent_analyzer.py` | 플레이어의 자유 서술 텍스트를 Gemini로 분석해 `IntentResult`(행동 요약, 판정 필요 여부, 대상 스킬 등)로 변환 |
| `bot/__init__.py`, `bot/cogs/__init__.py` | 빈 패키지 초기화 파일 |
| `bot/main.py` | `CoCBot`(discord.py `Bot` 서브클래스), 모듈 수준 `bot` 인스턴스, DB 풀 생성 + 웹 서버 기동 + cog 로더(`setup_hook`), 전역 슬래시 커맨드 에러 핸들러, `main()` 진입점(토큰·DB URL·Gemini API 키 가드) |
| `bot/web.py` | 캐릭터 등록 토큰 상태 조회(`GET /api/register/{token}`)와 등록 제출(`POST /api/register/{token}`)을 처리하고, `web/dist`에 빌드된 폼 페이지(`GET /register/{token}`)와 정적 자산(`GET /assets/...`), 기능명 목록(`GET /api/skills`)을 서빙하는 aiohttp 웹 서버. `PORT` 환경변수가 있을 때만 기동한다 |
| `bot/embeds.py` | `CheckResult`/`SanityResult`/`OpposedResult`, 캐릭터(역할 배지 포함)/시나리오/Keeper 낭독 딕셔너리를 한국어 Discord 임베드로 포맷 |
| `bot/cogs/check.py` | `/판정` 슬래시 커맨드, 판정 실패 시 붙는 `PushView`(푸시 롤 버튼) |
| `bot/cogs/sanity.py` | `/산정` 슬래시 커맨드 |
| `bot/cogs/opposed.py` | `/대립` 슬래시 커맨드 |
| `bot/cogs/character.py` | 캐릭터 등록창 열기/닫기, 구글시트 링크로 PC 등록(`defer()` 후 `asyncio.to_thread`로 파싱) 또는 링크 생략 시 웹 등록 폼 토큰 링크 발급(`RENDER_EXTERNAL_URL` 기준, 로컬은 `http://localhost:$PORT`로 대체), 캐릭터 조회, `/시나리오캐릭터등록`(그 시나리오의 키퍼만 KPC/NPC 등록 가능, 마찬가지로 링크 생략 시 토큰 링크 발급) |
| `bot/cogs/scenario.py` | `/시나리오등록`(구글독스 링크를 `aiohttp`로 fetch → `scenario_parser`로 파싱 → 저장), `/시나리오시작`(현재 채널 배정, 키퍼 전용), `/시나리오참가`(본인 PC를 로스터에 추가), `/시나리오조회` |
| `bot/cogs/narration.py` | `/낭독시작` 슬래시 커맨드, `NarrationView`(참가자(PC+키퍼)의 2/3 동의로 다음 문장 진행, `PushView`와 같은 메모리 상태 패턴) |
| `bot/cogs/action.py` | `/행동` 슬래시 커맨드. 자유 서술을 `intent_analyzer.analyze_intent()`(`defer()` 후 `asyncio.to_thread`로 호출)로 분석해 판정이 필요 없으면 서술 임베드를, 필요하면 캐릭터 스킬값을 조회해 `dice.roll_check()`로 판정한다 |
| `tests/test_dice_check.py` | 기본 판정·성공등급·보너스/페널티 로직 테스트, `FakeRng` 결정론적 난수 테스트 헬퍼 |
| `tests/test_dice_notation.py` | 다이스 표기 파서 테스트 |
| `tests/test_sanity.py` | SAN 체크 로직 테스트 |
| `tests/test_opposed.py` | 대립판정 로직 테스트 |
| `tests/test_embeds.py` | 임베드 포맷 테스트 |
| `tests/test_main.py` | 봇 엔트리포인트(토큰/DB URL 미설정 시 종료) 테스트 |
| `tests/test_check_cog.py` / `test_sanity_cog.py` / `test_opposed_cog.py` / `test_character_cog.py` / `test_scenario_cog.py` / `test_narration_cog.py` | 각 슬래시 커맨드 cog 테스트 (Discord Interaction은 mock으로 대체) |
| `tests/test_narration_view.py` | `NarrationView`의 2/3 동의 투표 로직 테스트 |
| `tests/test_sheet_parser.py` | xlsx 파싱(정상/누락 라벨/숫자 아님/빈 이름/스킬) 테스트 |
| `tests/test_scenario_parser.py` | 구글독스 HTML 아웃라인 파싱, 문장 분리(대사 보존 포함) 테스트 |
| `tests/test_storage_registration.py` / `test_storage_characters.py` / `test_storage_scenarios.py` | `storage.py` 통합 테스트, `TEST_DATABASE_URL` 환경변수가 없으면 스킵 |
| `requirements.txt` | 고정 의존성: `discord.py`, `pytest`, `asyncpg`, `openpyxl`, `google-generativeai`, `aiohttp` |
| `pytest.ini` | 프로젝트 루트를 `sys.path`에 추가해 `dice.py`/`bot` 임포트가 되도록 설정 |
| `Dockerfile` | `python:3.12-slim` 베이스, 의존성 설치 후 소스 복사, `python -m bot.main`으로 기동 |
| `.dockerignore` | 이미지 빌드 시 `.env`/`.git`/`.venv`/`tests/` 등을 제외해 시크릿 유출과 이미지 비대화를 방지 |
| `.env.example` | `DISCORD_TOKEN=`, `DATABASE_URL=`, `GEMINI_API_KEY=` 를 담은 환경변수 템플릿 (실제 값은 커밋하지 않음) |
| `docs/superpowers/specs/…design.md` | 설계 스펙 (요구사항, 아키텍처 결정) |
| `docs/superpowers/plans/…coc-discord-bot.md` | 태스크별 TDD 구현 계획 |

## 로컬 실행

1. [Discord Developer Portal](https://discord.com/developers/applications)에서
   애플리케이션/봇을 만들고 토큰을 발급받는다.
2. `applications.commands`, `bot` 스코프로 서버에 초대한다.
3. 의존성 설치 및 실행:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DISCORD_TOKEN=발급받은_토큰
export DATABASE_URL=postgres://user:password@localhost/coc_bot
export GEMINI_API_KEY=발급받은_Gemini_API_키
python -m bot.main
```

## Docker로 실행

```bash
docker build -t coc-bot .
docker run -e DISCORD_TOKEN=발급받은_토큰 -e DATABASE_URL=postgres://user:password@host/coc_bot -e GEMINI_API_KEY=발급받은_Gemini_API_키 coc-bot
```

## 저비용 호스팅

봇을 기동하려면 Postgres가 필수다(판정 명령어만 쓰더라도 마찬가지). Railway, Supabase,
Neon 등 무료/저가 티어의 관리형 Postgres를 `DATABASE_URL`로 연결해 쓰면 되고, 봇 프로세스
자체는 여전히 1 vCPU / 512MB급 저사양 인스턴스로 충분하다.

## 웹 폼 수정 시 주의사항

`web/src/` 아래를 수정했다면 반드시 다음을 실행해서 빌드 결과물을 커밋해야 한다:

```bash
cd web && npm run build
```

봇은 `web/dist/`에 커밋된 결과물을 서빙하지, `web/src/`를 직접 서빙하지 않는다.
빌드 후 `web/dist/` 변경분을 커밋하지 않으면 배포된 폼은 아무 에러 없이 예전
JS/CSS를 계속 서빙한다.

## 테스트

```bash
pytest -v
```
