from aiohttp import web


async def _health(request: web.Request) -> web.Response:
    return web.Response(status=200)


def create_app(pool) -> web.Application:
    app = web.Application()
    app["pool"] = pool
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    return app
