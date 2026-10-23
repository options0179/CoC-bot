import json
from pathlib import Path

from aiohttp import web

from sheet_parser import SKILL_NAMES
from storage import get_valid_registration_token, register_character_with_token

POOL_KEY: web.AppKey = web.AppKey("pool")

_TEXT_FIELDS = ["name", "occupation", "sex", "residence", "birthplace"]
_INT_FIELDS = ["age", "str", "dex", "pow", "con", "app", "edu", "siz", "int", "mov"]

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
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError, web.HTTPBadRequest):
        return web.json_response(
            {"ok": False, "error": "요청 형식이 올바르지 않습니다."}, status=400
        )

    if not isinstance(payload, dict):
        return web.json_response(
            {"ok": False, "error": "요청 형식이 올바르지 않습니다."}, status=400
        )

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return web.json_response({"ok": False, "error": "이름을 입력해주세요."}, status=400)
    if len(name.strip()) > 100:
        return web.json_response({"ok": False, "error": "이름은 100자 이하여야 합니다."}, status=400)

    data = {"name": name.strip()}
    for field in _TEXT_FIELDS[1:]:
        value = payload.get(field, "")
        if value is None:
            value = ""
        if not isinstance(value, str) or len(value) > 500:
            return web.json_response(
                {"ok": False, "error": f"{field}은(는) 500자 이하의 문자열이어야 합니다."},
                status=400,
            )
        data[field] = value.strip()

    for field in _INT_FIELDS:
        value = payload.get(field)
        if value is None or value == "":
            data[field] = None
            continue
        if isinstance(value, bool):
            return web.json_response(
                {"ok": False, "error": f"{field}은(는) 숫자여야 합니다."}, status=400
            )
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
    skills = payload.get("skills", {})
    if not isinstance(skills, dict) or not all(
        isinstance(name, str)
        and name.strip()
        and type(value) is int
        and 0 <= value <= 999
        for name, value in skills.items()
    ):
        return web.json_response({"ok": False, "error": "기능 값은 숫자여야 합니다."}, status=400)
    data["skills"] = {name.strip(): value for name, value in skills.items()}

    if not await register_character_with_token(pool, token, data):
        return web.json_response(
            {"ok": False, "error": "링크가 만료되었거나 이미 사용되었습니다."}, status=404
        )
    return web.json_response({"ok": True, "name": data["name"]})


def create_app(pool) -> web.Application:
    app = web.Application(client_max_size=64 * 1024)
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
