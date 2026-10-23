import asyncio

import pytest

from bot.google_exports import (
    GoogleExportTooLarge,
    fetch_google_doc,
    fetch_google_sheet,
)


class _Content:
    def __init__(self, chunks):
        self.chunks = chunks

    async def iter_chunked(self, size):
        for chunk in self.chunks:
            yield chunk


class _Response:
    def __init__(self, chunks, status=200, content_length=None):
        self.content = _Content(chunks)
        self.status = status
        self.content_length = content_length

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _Session:
    def __init__(self, response, timeout):
        self.response = response
        self.timeout = timeout

    def get(self, url):
        self.url = url
        return self.response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def test_fetch_google_sheet_reads_export_with_timeout(monkeypatch):
    sessions = []

    def make_session(**kwargs):
        session = _Session(_Response([b"xlsx"]), **kwargs)
        sessions.append(session)
        return session

    monkeypatch.setattr("bot.google_exports.aiohttp.ClientSession", make_session)

    content = asyncio.run(fetch_google_sheet("sheet_123"))

    assert content == b"xlsx"
    assert "docs.google.com/spreadsheets/d/sheet_123/export?format=xlsx" in sessions[0].url
    assert sessions[0].timeout.total == 20


def test_fetch_google_doc_returns_none_for_non_200(monkeypatch):
    monkeypatch.setattr(
        "bot.google_exports.aiohttp.ClientSession",
        lambda **kw: _Session(_Response([], status=404), **kw),
    )

    assert asyncio.run(fetch_google_doc("doc_123")) is None


def test_fetch_google_sheet_rejects_oversized_stream(monkeypatch):
    monkeypatch.setattr(
        "bot.google_exports.MAX_SHEET_BYTES", 4
    )
    monkeypatch.setattr(
        "bot.google_exports.aiohttp.ClientSession",
        lambda **kw: _Session(_Response([b"123", b"45"]), **kw),
    )

    with pytest.raises(GoogleExportTooLarge):
        asyncio.run(fetch_google_sheet("sheet_123"))


def test_fetch_google_doc_rejects_large_declared_body(monkeypatch):
    monkeypatch.setattr("bot.google_exports.MAX_DOC_BYTES", 4)
    monkeypatch.setattr(
        "bot.google_exports.aiohttp.ClientSession",
        lambda **kw: _Session(_Response([], content_length=5), **kw),
    )

    with pytest.raises(GoogleExportTooLarge):
        asyncio.run(fetch_google_doc("doc_123"))
