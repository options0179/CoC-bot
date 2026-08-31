# CoC-Bot

Call of Cthulhu 7판 판정(스킬 체크, SAN 체크, 대립판정, 푸시 롤)을 자동화하는
디스코드 슬래시 커맨드 봇. 캐릭터시트나 시나리오는 저장하지 않는다 — 사람 키퍼가
직접 진행하고, 봇은 판정 계산만 담당한다.

## 커맨드

- `/판정 스킬값 [보너스] [페널티]` — d100 판정, 실패 시 푸시 버튼 첨부
- `/산정 현재san 손실식` — SAN 체크 (손실식 예: `1/1d4+1`)
- `/대립 내스킬 상대스킬` — 대립판정

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
python -m bot.main
```

## Docker로 실행

```bash
docker build -t coc-bot .
docker run -e DISCORD_TOKEN=발급받은_토큰 coc-bot
```

## 저비용 호스팅

DB 없이 프로세스 하나만 24/7 떠 있으면 되므로, 1 vCPU / 512MB급의 저사양
인스턴스로 충분하다. 무료/저가 티어를 제공하는 컨테이너 호스팅(Fly.io, Railway
등)이나 소형 VPS 어디에 올려도 된다.

## 테스트

```bash
pytest -v
```
