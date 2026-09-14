import asyncio
from unittest.mock import AsyncMock

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


def test_get_registration_status_valid_token(monkeypatch):
    async def _body():
        monkeypatch.setattr(
            "bot.web.get_valid_registration_token",
            AsyncMock(
                return_value={
                    "role": "PC",
                    "guild_id": 1,
                    "discord_user_id": 100,
                    "scenario_id": None,
                }
            ),
        )
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/api/register/sometoken")
            assert resp.status == 200
            body = await resp.json()
            assert body == {"valid": True, "role": "PC"}

    asyncio.run(_body())


def test_get_registration_status_invalid_token(monkeypatch):
    async def _body():
        monkeypatch.setattr(
            "bot.web.get_valid_registration_token", AsyncMock(return_value=None)
        )
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/api/register/badtoken")
            assert resp.status == 404
            body = await resp.json()
            assert body == {"valid": False}

    asyncio.run(_body())
