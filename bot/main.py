import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("coc-bot")

INTENTS = discord.Intents.default()


class CoCBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!coc-unused!", intents=INTENTS)
        self.pool = None

    async def setup_hook(self) -> None:
        self.pool = await storage.create_pool(os.environ["DATABASE_URL"])
        await self.load_extension("bot.cogs.check")
        await self.load_extension("bot.cogs.sanity")
        await self.load_extension("bot.cogs.opposed")
        await self.load_extension("bot.cogs.character")
        await self.load_extension("bot.cogs.scenario")
        await self.load_extension("bot.cogs.narration")
        await self.load_extension("bot.cogs.action")
        await self.tree.sync()
        if os.environ.get("RENDER_EXTERNAL_URL"):
            self._self_ping.start()

    async def close(self) -> None:
        self._self_ping.cancel()
        if self.pool is not None:
            await self.pool.close()
        await super().close()

    @tasks.loop(minutes=10)
    async def _self_ping(self) -> None:
        url = os.environ["RENDER_EXTERNAL_URL"]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url):
                    pass
        except aiohttp.ClientError:
            logger.exception("Self-ping failed")


bot = CoCBot()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    logger.exception("Slash command error", exc_info=error)
    original = getattr(error, "original", error)
    message = str(original) if isinstance(original, ValueError) else "명령어 처리 중 오류가 발생했습니다."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def _run_health_check_server() -> None:
    port = os.environ.get("PORT")
    if not port:
        return

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args) -> None:
            pass

    server = HTTPServer(("0.0.0.0", int(port)), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def main() -> None:
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
    _run_health_check_server()
    bot.run(token)


if __name__ == "__main__":
    main()
