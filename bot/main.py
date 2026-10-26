import asyncio
import logging
import os
import signal
import time

import aiohttp
import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands, tasks

import storage
from bot.web import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("coc-bot")

INTENTS = discord.Intents.default()


class InstrumentedCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        interaction.extras["_coc_started_at"] = time.monotonic()
        command = getattr(interaction.command, "qualified_name", "unknown")
        logger.info(
            "Slash command received interaction_id=%s command=%s",
            interaction.id,
            command,
        )
        return True


def _log_command_result(interaction: discord.Interaction, command: str, outcome: str) -> None:
    started = interaction.extras.get("_coc_started_at")
    duration_ms = round((time.monotonic() - started) * 1000) if started is not None else -1
    acknowledged = interaction.response.is_done()
    logger.info(
        "Slash command %s interaction_id=%s command=%s command_duration_ms=%s "
        "acknowledged_at_completion=%s",
        outcome,
        interaction.id,
        command,
        duration_ms,
        acknowledged,
    )


class CoCBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!coc-unused!",
            intents=INTENTS,
            tree_cls=InstrumentedCommandTree,
        )
        self.pool = None
        self._web_runner: web.AppRunner | None = None

    async def setup_hook(self) -> None:
        self.pool = await storage.create_pool(
            os.environ.get("DATABASE_PATH", "data/coc-bot.sqlite3")
        )
        # Bind the port before Discord setup (extension loads, tree.sync) so
        # Render's health check succeeds even if Discord-side startup is slow.
        await self._start_web_server()
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

    async def _start_web_server(self) -> None:
        port = os.environ.get("PORT")
        if not port:
            return
        app = create_app()
        self._web_runner = web.AppRunner(app)
        await self._web_runner.setup()
        site = web.TCPSite(self._web_runner, "0.0.0.0", int(port))
        await site.start()

    async def close(self) -> None:
        logger.info("Shutdown started")
        self._self_ping.cancel()
        steps = []
        if self._web_runner is not None:
            steps.append(("web", self._web_runner.cleanup))
        if self.pool is not None:
            steps.append(("database", self.pool.close))
        steps.append(("discord", super().close))
        first_failure = None
        for name, cleanup in steps:
            started = time.monotonic()
            logger.info("Shutdown step started step=%s", name)
            try:
                await cleanup()
            except Exception as exc:
                if first_failure is None:
                    first_failure = f"{name} shutdown failed ({type(exc).__name__})"
                logger.error(
                    "Shutdown step failed step=%s duration_ms=%s error_type=%s",
                    name,
                    round((time.monotonic() - started) * 1000),
                    type(exc).__name__,
                )
            else:
                logger.info(
                    "Shutdown step complete step=%s duration_ms=%s",
                    name,
                    round((time.monotonic() - started) * 1000),
                )
        logger.info("Shutdown complete failures=%s", first_failure is not None)
        if first_failure is not None:
            raise RuntimeError(first_failure) from None

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
    command = getattr(interaction.command, "qualified_name", "unknown")
    _log_command_result(interaction, command, "failed")
    logger.error("Slash command exception_type=%s", type(error).__name__)
    original = getattr(error, "original", error)
    message = str(original) if isinstance(original, ValueError) else "명령어 처리 중 오류가 발생했습니다."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


@bot.listen("app_command_completion")
async def on_app_command_completion(
    interaction: discord.Interaction, command: app_commands.Command
) -> None:
    _log_command_result(interaction, command.qualified_name, "completed")


def main() -> None:
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")
    asyncio.run(_run_bot(token))


async def _run_bot(token: str) -> None:
    loop = asyncio.get_running_loop()
    task = asyncio.create_task(bot.start(token))
    loop.add_signal_handler(signal.SIGTERM, task.cancel)
    try:
        await task
    except asyncio.CancelledError:
        pass
    finally:
        loop.remove_signal_handler(signal.SIGTERM)
        await bot.close()


if __name__ == "__main__":
    main()
