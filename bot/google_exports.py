import aiohttp

MAX_SHEET_BYTES = 10 * 1024 * 1024
MAX_DOC_BYTES = 5 * 1024 * 1024


class GoogleExportTooLarge(ValueError):
    pass


async def _fetch(url: str, max_bytes: int) -> bytes | None:
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            if response.content_length is not None and response.content_length > max_bytes:
                raise GoogleExportTooLarge

            content = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                if len(content) + len(chunk) > max_bytes:
                    raise GoogleExportTooLarge
                content.extend(chunk)
            return bytes(content)


async def fetch_google_sheet(sheet_id: str) -> bytes | None:
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    return await _fetch(url, MAX_SHEET_BYTES)


async def fetch_google_doc(doc_id: str) -> str | None:
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
    content = await _fetch(url, MAX_DOC_BYTES)
    return content.decode("utf-8") if content is not None else None
