# CoC-Bot

Call of Cthulhu 7판 판정(스킬 체크, SAN 체크, 대립판정, 푸시 롤)을 자동화하는
디스코드 슬래시 커맨드 봇. 캐릭터시트나 시나리오는 저장하지 않는다 — 사람 키퍼가
직접 진행하고, 봇은 판정 계산만 담당한다.

## 커맨드

- `/판정 스킬값 [보너스] [페널티]` — d100 판정, 실패 시 푸시 버튼 첨부
- `/산정 현재san 손실식` — SAN 체크 (손실식 예: `1/1d4+1`)
- `/대립 내스킬 상대스킬` — 대립판정
- `/캐릭터등록열기` — 캐릭터 등록창을 연다 (연 사람만 닫을 수 있음)
- `/캐릭터등록닫기` — 본인이 연 등록창을 닫는다
- `/캐릭터등록 파일:<xlsx>` — 등록창이 열려있을 때 캐릭터시트를 업로드해 등록(재업로드 시 덮어쓰기)
- `/캐릭터조회 [유저]` — 등록된 캐릭터 조회 (생략 시 본인)

## 작동 원리

**상태 없는(stateless) 구조.** 캐릭터시트나 시나리오 데이터를 어디에도 저장하지
않는다. `/판정`이면 스킬값을, `/산정`이면 현재 SAN을 커맨드 인자로 받아 그 자리에서
계산하고 결과만 응답한다. DB나 파일 기반 저장소가 전혀 없으므로 배포/운영이
프로세스 하나만 계속 떠 있으면 되는 수준으로 단순하다.

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

**봇 기동.** `bot/main.py`의 `main()`이 `DISCORD_TOKEN` 환경변수를 읽어 봇을
실행한다. 연결되면 `CoCBot.setup_hook()`이 세 cog(`check`/`sanity`/`opposed`)를
로드하고 `tree.sync()`로 슬래시 커맨드를 Discord에 등록한다.

## 프로젝트 구조

```
CoC-Bot/
├── dice.py                      # CoC 7판 판정 로직 전체 (discord 비의존 순수 함수)
├── bot/
│   ├── main.py                  # 봇 엔트리포인트, cog 로더, 전역 에러 핸들러
│   ├── embeds.py                # 판정 결과 → 한국어 Discord 임베드 포맷
│   └── cogs/
│       ├── check.py             # /판정 커맨드 + PushView(재도전 버튼)
│       ├── sanity.py            # /산정 커맨드
│       └── opposed.py           # /대립 커맨드
├── tests/                       # bot/, dice.py 구조를 그대로 미러링하는 pytest 테스트
├── requirements.txt              # 의존성 고정 (discord.py, pytest)
├── pytest.ini                    # pytest 설정 (pythonpath=.)
├── Dockerfile                    # 컨테이너 이미지 빌드 정의
├── .dockerignore                 # Docker 빌드 컨텍스트 제외 목록 (.env 등 시크릿 방지)
├── .env.example                  # 환경변수 템플릿 (DISCORD_TOKEN)
├── .gitignore                    # git 추적 제외 목록
└── docs/superpowers/              # 설계 스펙 · 구현 계획 문서
```

파일별 상세:

| 경로 | 역할 |
|---|---|
| `dice.py` | d100 판정/성공등급, 보너스·페널티 주사위, 다이스 표기(`XdY+Z`) 파서, SAN 체크, 대립판정 — 판정 계산 로직 전부가 여기 있다. |
| `bot/__init__.py`, `bot/cogs/__init__.py` | 빈 패키지 초기화 파일 |
| `bot/main.py` | `CoCBot`(discord.py `Bot` 서브클래스), 모듈 수준 `bot` 인스턴스, cog 로더(`setup_hook`), 전역 슬래시 커맨드 에러 핸들러, `main()` 진입점 |
| `bot/embeds.py` | `CheckResult`/`SanityResult`/`OpposedResult`를 한국어 Discord 임베드로 포맷 |
| `bot/cogs/check.py` | `/판정` 슬래시 커맨드, 판정 실패 시 붙는 `PushView`(푸시 롤 버튼) |
| `bot/cogs/sanity.py` | `/산정` 슬래시 커맨드 |
| `bot/cogs/opposed.py` | `/대립` 슬래시 커맨드 |
| `tests/test_dice_check.py` | 기본 판정·성공등급·보너스/페널티 로직 테스트, `FakeRng` 결정론적 난수 테스트 헬퍼 |
| `tests/test_dice_notation.py` | 다이스 표기 파서 테스트 |
| `tests/test_sanity.py` | SAN 체크 로직 테스트 |
| `tests/test_opposed.py` | 대립판정 로직 테스트 |
| `tests/test_embeds.py` | 임베드 포맷 테스트 |
| `tests/test_main.py` | 봇 엔트리포인트(토큰 미설정 시 종료) 테스트 |
| `tests/test_check_cog.py` / `test_sanity_cog.py` / `test_opposed_cog.py` | 각 슬래시 커맨드 cog 테스트 (Discord Interaction은 mock으로 대체) |
| `requirements.txt` | 고정 의존성: `discord.py`, `pytest` |
| `pytest.ini` | 프로젝트 루트를 `sys.path`에 추가해 `dice.py`/`bot` 임포트가 되도록 설정 |
| `Dockerfile` | `python:3.12-slim` 베이스, 의존성 설치 후 소스 복사, `python -m bot.main`으로 기동 |
| `.dockerignore` | 이미지 빌드 시 `.env`/`.git`/`.venv`/`tests/` 등을 제외해 시크릿 유출과 이미지 비대화를 방지 |
| `.env.example` | `DISCORD_TOKEN=` 만 담은 환경변수 템플릿 (실제 값은 커밋하지 않음) |
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
python -m bot.main
```

## Docker로 실행

```bash
docker build -t coc-bot .
docker run -e DISCORD_TOKEN=발급받은_토큰 coc-bot
```

## 저비용 호스팅

캐릭터시트 등록 기능부터 Postgres가 필요하다. Railway, Supabase, Neon 등 무료/저가 티어의
관리형 Postgres를 `DATABASE_URL`로 연결해 쓰면 되고, 봇 프로세스 자체는 여전히 1 vCPU /
512MB급 저사양 인스턴스로 충분하다.

## 테스트

```bash
pytest -v
```
