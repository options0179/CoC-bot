import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from aiohttp.test_utils import TestClient, TestServer

from bot.web import create_app


def _mock_valid_token(monkeypatch, **overrides):
    row = {"guild_id": 1, "discord_user_id": 100, "role": "PC", "scenario_id": None, **overrides}
    monkeypatch.setattr("bot.web.get_valid_registration_token", AsyncMock(return_value=row))
    monkeypatch.setattr("bot.web.register_character_with_token", AsyncMock(return_value=True))
    return row


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
        _mock_valid_token(monkeypatch, role="PC")
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
        monkeypatch.setattr("bot.web.register_character_with_token", AsyncMock(return_value=False))
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/api/register/badtoken", json={"name": "탐사자"})
            assert resp.status == 404
            body = await resp.json()
            assert body["ok"] is False

    asyncio.run(_body())


def test_post_registration_rejects_malformed_json(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
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
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/api/register/tok", json={"name": "   "})
            assert resp.status == 400
            body = await resp.json()
            assert "이름" in body["error"]

    asyncio.run(_body())


def test_post_registration_rejects_non_numeric_attribute(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok", json={"name": "탐사자", "str": "abc"}
            )
            assert resp.status == 400
            body = await resp.json()
            assert "str" in body["error"]

    asyncio.run(_body())


def test_post_registration_rejects_attribute_below_zero(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok", json={"name": "탐사자", "str": -1}
            )
            assert resp.status == 400
            body = await resp.json()
            assert "str" in body["error"]

    asyncio.run(_body())


def test_post_registration_rejects_attribute_above_999(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok", json={"name": "탐사자", "str": 1000}
            )
            assert resp.status == 400
            body = await resp.json()
            assert "str" in body["error"]

    asyncio.run(_body())


def test_post_registration_rejects_non_dict_skills(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok", json={"name": "탐사자", "skills": ["x"]}
            )
            assert resp.status == 400
            body = await resp.json()
            assert body["ok"] is False
            assert "기능" in body["error"]

    asyncio.run(_body())


def test_post_registration_rejects_non_int_skill_value(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok",
                json={"name": "탐사자", "skills": {"회계": "abc"}},
            )
            assert resp.status == 400
            body = await resp.json()
            assert body["ok"] is False
            assert "기능" in body["error"]

    asyncio.run(_body())


def test_post_registration_rejects_boolean_skill_value(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok", json={"name": "탐사자", "skills": {"회계": True}}
            )
            assert resp.status == 400

    asyncio.run(_body())


def test_post_registration_rejects_boolean_attribute(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok", json={"name": "탐사자", "str": True}
            )
            assert resp.status == 400

    asyncio.run(_body())


def test_post_registration_rejects_non_string_optional_text(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok", json={"name": "탐사자", "occupation": {"x": 1}}
            )
            assert resp.status == 400

    asyncio.run(_body())


def test_post_registration_rejects_out_of_range_skill_value(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok", json={"name": "탐사자", "skills": {"회계": 1000}}
            )
            assert resp.status == 400

    asyncio.run(_body())


def test_post_registration_rejects_non_dict_body(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/api/register/tok", json=["a", "b"])
            assert resp.status == 400
            body = await resp.json()
            assert body["ok"] is False

    asyncio.run(_body())


def test_post_registration_strips_name_whitespace(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        register_mock = AsyncMock(return_value=True)
        monkeypatch.setattr("bot.web.register_character_with_token", register_mock)

        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok", json={"name": "  탐사자  "}
            )
            assert resp.status == 200
            body = await resp.json()
            assert body == {"ok": True, "name": "탐사자"}

        args, _ = register_mock.call_args
        assert args[2]["name"] == "탐사자"

    asyncio.run(_body())


def test_post_registration_succeeds_and_consumes_token(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        register_mock = AsyncMock(return_value=True)
        monkeypatch.setattr("bot.web.register_character_with_token", register_mock)

        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok",
                json={"name": "탐사자", "str": 50, "skills": {"회계": 40}},
            )
            assert resp.status == 200
            body = await resp.json()
            assert body == {"ok": True, "name": "탐사자"}

        register_mock.assert_awaited_once()
        args, _ = register_mock.call_args
        assert args[1] == "tok"
        assert args[2]["name"] == "탐사자"
        assert args[2]["str"] == 50
        assert args[2]["skills"] == {"회계": 40}

    asyncio.run(_body())


def test_post_registration_returns_expired_when_token_loses_race(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        monkeypatch.setattr(
            "bot.web.register_character_with_token", AsyncMock(return_value=False)
        )
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post("/api/register/tok", json={"name": "탐사자"})
            assert resp.status == 404
            assert (await resp.json())["ok"] is False

    asyncio.run(_body())


def test_post_registration_ignores_body_supplied_identity_fields(monkeypatch):
    async def _body():
        _mock_valid_token(monkeypatch)
        register_mock = AsyncMock(return_value=True)
        monkeypatch.setattr("bot.web.register_character_with_token", register_mock)

        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.post(
                "/api/register/tok",
                json={
                    "name": "탐사자",
                    "guild_id": 999,
                    "discord_user_id": 999,
                    "role": "GM",
                    "scenario_id": 42,
                },
            )
            assert resp.status == 200

        args, _ = register_mock.call_args
        assert args[1] == "tok"

    asyncio.run(_body())


def test_get_skills_returns_sorted_skill_names(monkeypatch):
    async def _body():
        monkeypatch.setattr("bot.web.SKILL_NAMES", {"회계", "심리학", "감정"})
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/api/skills")
            assert resp.status == 200
            body = await resp.json()
            assert body == ["감정", "심리학", "회계"]

    asyncio.run(_body())


def test_register_form_serves_index_html():
    async def _body():
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/register/sometoken")
            assert resp.status == 200
            assert resp.content_type == "text/html"

    asyncio.run(_body())


def test_assets_route_is_registered():
    async def _body():
        app = create_app(pool=None)
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/assets/does-not-exist.js")
            assert resp.status == 404

    asyncio.run(_body())


def test_create_app_does_not_raise_when_dist_assets_missing(monkeypatch):
    async def _body():
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_dist = Path(tmpdir) / "dist"
            fake_dist.mkdir()
            # No "assets" subdirectory created — this is the scenario that used
            # to crash create_app() via add_static's path validation.
            monkeypatch.setattr("bot.web._WEB_DIST", fake_dist)

            app = create_app(pool=None)
            async with TestClient(TestServer(app)) as client:
                resp = await client.get("/health")
                assert resp.status == 200

    asyncio.run(_body())
