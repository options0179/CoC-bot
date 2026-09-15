import json

from aiohttp import web

from storage import consume_registration_token, get_valid_registration_token, upsert_character

_TEXT_FIELDS = ["name", "occupation", "sex", "residence", "birthplace"]
_INT_FIELDS = ["age", "str", "dex", "pow", "con", "app", "edu", "siz", "int", "mov"]


async def _health(request: web.Request) -> web.Response:
    return web.Response(status=200)


async def _get_registration_status(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    row = await get_valid_registration_token(request.app["pool"], token)
    if row is None:
        return web.json_response({"valid": False}, status=404)
    return web.json_response({"valid": True, "role": row["role"]})


async def _submit_registration(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    pool = request.app["pool"]
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
    app["pool"] = pool
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    app.router.add_get("/api/register/{token}", _get_registration_status)
    app.router.add_post("/api/register/{token}", _submit_registration)
    return app
