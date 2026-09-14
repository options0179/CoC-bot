import asyncio

from aiohttp.test_utils import TestClient, TestServer

from bot.web import create_app


def test_health_endpoints_return_200():
    async def _body():
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/health")
            assert resp.status == 200
            resp_root = await client.get("/")
            assert resp_root.status == 200

    asyncio.run(_body())
