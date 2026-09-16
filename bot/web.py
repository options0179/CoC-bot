import json
from pathlib import Path

from aiohttp import web

from sheet_parser import SKILL_NAMES
from storage import consume_registration_token, get_valid_registration_token, upsert_character

POOL_KEY: web.AppKey = web.AppKey("pool")

_TEXT_FIELDS = ["name", "occupation", "sex", "residence", "birthplace"]
_INT_FIELDS = ["age", "str", "dex", "pow", "con", "app", "edu", "siz", "int", "mov"]
# 수동 입력 상태(중상/MP 빈사). 광기 플래그는 /산정이 파생하므로 폼에서 받지 않는다.
_BOOL_FIELDS = ["major_wound", "mp_depleted"]

_WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


async def _get_skills(request: web.Request) -> web.Response:
    return web.json_response(sorted(SKILL_NAMES))


async def _serve_registration_form(request: web.Request) -> web.FileResponse:
    return web.FileResponse(_WEB_DIST / "index.html")


async def _health(request: web.Request) -> web.Response:
    return web.Response(status=200)


async def _get_registration_status(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    row = await get_valid_registration_token(request.app[POOL_KEY], token)
    if row is None:
        return web.json_response({"valid": False}, status=404)
    return web.json_response({"valid": True, "role": row["role"]})


async def _submit_registration(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    pool = request.app[POOL_KEY]
    token_row = await get_valid_registration_token(pool, token)
    if token_row is None:
        return web.json_response(
            {"ok": False, "error": "링크가 만료되었거나 이미 사용되었습니다."}, status=404
        )

    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return web.json_response(
            {"ok": False, "error": "요청 형식이 올바르지 않습니다."}, status=400
        )

    if not isinstance(payload, dict):
        return web.json_response(
            {"ok": False, "error": "요청 형식이 올바르지 않습니다."}, status=400
        )

    name = payload.get("name")
    if not name or not str(name).strip():
        return web.json_response({"ok": False, "error": "이름을 입력해주세요."}, status=400)
    payload["name"] = str(name).strip()

    data = {field: payload.get(field) for field in _TEXT_FIELDS}
    # 플레이어는 폼 입력이 아니라 토큰 발급 시 서버가 캡처한 값만 신뢰한다.
    data["player"] = token_row["player_name"]
    for field in _INT_FIELDS:
        value = payload.get(field)
        if value is None or value == "":
            data[field] = None
            continue
        try:
            data[field] = int(value)
        except (TypeError, ValueError):
            return web.json_response(
                {"ok": False, "error": f"{field}은(는) 숫자여야 합니다."}, status=400
            )
        if not (0 <= data[field] <= 999):
            return web.json_response(
                {"ok": False, "error": f"{field}은(는) 0에서 999 사이의 값이어야 합니다."},
                status=400,
            )
    if data["pow"] is None:
        return web.json_response(
            {"ok": False, "error": "정신력(POW)을 입력해주세요. 이성(SAN) 계산에 필요합니다."},
            status=400,
        )
    data["san_starting"] = data["pow"]
    data["san_current"] = data["pow"]

    for field in _BOOL_FIELDS:
        value = payload.get(field, False)
        if not isinstance(value, bool):
            return web.json_response(
                {"ok": False, "error": f"{field}은(는) true/false여야 합니다."}, status=400
            )
        data[field] = value

    weapons = payload.get("weapons") or []
    if not isinstance(weapons, list) or not all(
        isinstance(w, dict)
        and all(isinstance(v, str) for v in w.values())
        and w.get("name", "").strip()
        for w in weapons
    ):
        return web.json_response(
            {"ok": False, "error": "무기 항목은 이름이 있는 문자열 값들이어야 합니다."},
            status=400,
        )
    data["weapons"] = weapons

    skills = payload.get("skills") or {}
    if not isinstance(skills, dict) or not all(isinstance(v, int) for v in skills.values()):
        return web.json_response({"ok": False, "error": "기능 값은 숫자여야 합니다."}, status=400)
    data["skills"] = skills

    await upsert_character(
        pool,
        token_row["guild_id"],
        token_row["discord_user_id"],
        data,
        role=token_row["role"],
        scenario_id=token_row["scenario_id"],
    )
    await consume_registration_token(pool, token)
    return web.json_response({"ok": True, "name": data["name"]})


def create_app(pool) -> web.Application:
    app = web.Application()
    app[POOL_KEY] = pool
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    app.router.add_get("/api/register/{token}", _get_registration_status)
    app.router.add_post("/api/register/{token}", _submit_registration)
    app.router.add_get("/api/skills", _get_skills)
    app.router.add_get("/register/{token}", _serve_registration_form)
    if (_WEB_DIST / "assets").is_dir():
        app.router.add_static("/assets/", path=_WEB_DIST / "assets")
    return app
