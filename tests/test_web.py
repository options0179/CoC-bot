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


def test_post_registration_rejected_for_invalid_token(monkeypatch):
    async def _body():
        monkeypatch.setattr(
            "bot.web.get_valid_registration_token", AsyncMock(return_value=None)
        )
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/api/register/badtoken", json={"name": "탐사자"})
            assert resp.status == 404
            body = await resp.json()
            assert body["ok"] is False

    asyncio.run(_body())


def test_post_registration_rejects_malformed_json(monkeypatch):
    async def _body():
        monkeypatch.setattr(
            "bot.web.get_valid_registration_token",
            AsyncMock(
                return_value={
                    "guild_id": 1,
                    "discord_user_id": 100,
                    "role": "PC",
                    "scenario_id": None,
                }
            ),
        )
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok",
                data="not valid json",
                headers={"Content-Type": "application/json"},
            )
            assert resp.status == 400
            body = await resp.json()
            assert "형식" in body["error"]

    asyncio.run(_body())


def test_post_registration_rejects_missing_name(monkeypatch):
    async def _body():
        monkeypatch.setattr(
            "bot.web.get_valid_registration_token",
            AsyncMock(
                return_value={
                    "guild_id": 1,
                    "discord_user_id": 100,
                    "role": "PC",
                    "scenario_id": None,
                }
            ),
        )
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/api/register/tok", json={"name": "   "})
            assert resp.status == 400
            body = await resp.json()
            assert "이름" in body["error"]

    asyncio.run(_body())


def test_post_registration_rejects_non_numeric_attribute(monkeypatch):
    async def _body():
        monkeypatch.setattr(
            "bot.web.get_valid_registration_token",
            AsyncMock(
                return_value={
                    "guild_id": 1,
                    "discord_user_id": 100,
                    "role": "PC",
                    "scenario_id": None,
                }
            ),
        )
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok", json={"name": "탐사자", "str": "abc"}
            )
            assert resp.status == 400
            body = await resp.json()
            assert "str" in body["error"]

    asyncio.run(_body())


def test_post_registration_succeeds_and_consumes_token(monkeypatch):
    async def _body():
        monkeypatch.setattr(
            "bot.web.get_valid_registration_token",
            AsyncMock(
                return_value={
                    "guild_id": 1,
                    "discord_user_id": 100,
                    "role": "PC",
                    "scenario_id": None,
                }
            ),
        )
        upsert_mock = AsyncMock()
        monkeypatch.setattr("bot.web.upsert_character", upsert_mock)
        consume_mock = AsyncMock()
        monkeypatch.setattr("bot.web.consume_registration_token", consume_mock)

        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok",
                json={"name": "탐사자", "str": 50, "skills": {"회계": 40}},
            )
            assert resp.status == 200
            body = await resp.json()
            assert body == {"ok": True, "name": "탐사자"}

        upsert_mock.assert_awaited_once()
        args, kwargs = upsert_mock.call_args
        assert args[1] == 1  # guild_id
        assert args[2] == 100  # user_id
        assert args[3]["name"] == "탐사자"
        assert args[3]["str"] == 50
        assert args[3]["skills"] == {"회계": 40}
        assert kwargs["role"] == "PC"
        assert kwargs["scenario_id"] is None
        consume_mock.assert_awaited_once_with(None, "tok")

    asyncio.run(_body())
