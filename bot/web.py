from aiohttp import web

from storage import get_valid_registration_token


async def _health(request: web.Request) -> web.Response:
    return web.Response(status=200)


async def _get_registration_status(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    row = await get_valid_registration_token(request.app["pool"], token)
    if row is None:
        return web.json_response({"valid": False}, status=404)
    return web.json_response({"valid": True, "role": row["role"]})


def create_app(pool) -> web.Application:
    app = web.Application()
    app["pool"] = pool
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    app.router.add_get("/api/register/{token}", _get_registration_status)
    return app
