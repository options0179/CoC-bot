import re

import aiohttp
import discord
from asyncpg import UniqueViolationError
from discord import app_commands
from discord.ext import commands

from bot.embeds import scenario_embed
from scenario_parser import parse_scenario_html
from storage import (
    bind_scenario_channel,
    create_scenario,
    get_roster,
    get_scenario_by_channel,
    get_scenario_by_title,
)

_EXPORT_URL_TEMPLATE = "https://docs.google.com/document/d/{doc_id}/export?format=html"
_DOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")


def _extract_doc_id(url: str) -> str | None:
    match = _DOC_ID_RE.search(url)
    return match.group(1) if match else None


class ScenarioCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.pool = bot.pool

    @app_commands.command(name="시나리오등록", description="구글독스 시나리오 문서를 등록합니다.")
    @app_commands.describe(
        제목="시나리오 이름", 링크="구글독스 문서 링크(링크가 있는 모든 사용자에게 공개)"
    )
    @app_commands.guild_only()
    async def register(self, interaction: discord.Interaction, 제목: str, 링크: str) -> None:
        doc_id = _extract_doc_id(링크)
        if doc_id is None:
            await interaction.response.send_message(
                "구글독스 문서 링크가 아닙니다.", ephemeral=True
            )
            return
        await interaction.response.defer()
        export_url = _EXPORT_URL_TEMPLATE.format(doc_id=doc_id)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(export_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            "문서를 가져올 수 없습니다. 링크 공개 설정을 확인하세요.",
                            ephemeral=True,
                        )
                        return
                    html = await resp.text()
        except aiohttp.ClientError as exc:
            await interaction.followup.send(f"문서를 가져오는 중 오류: {exc}", ephemeral=True)
            return
        structure = parse_scenario_html(html)
        if not structure:
            await interaction.followup.send(
                "문서에서 Keeper 낭독 구간을 찾지 못했습니다.", ephemeral=True
            )
            return
        try:
            await create_scenario(
                self.pool, interaction.guild_id, 제목, interaction.user.id, 링크, structure
            )
        except UniqueViolationError:
            await interaction.followup.send(
                f"이미 '{제목}' 이름의 시나리오가 등록돼 있습니다.", ephemeral=True
            )
            return
        await interaction.followup.send(f"'{제목}' 시나리오를 등록했습니다. (장면 {len(structure)}개)")

    @app_commands.command(name="시나리오시작", description="현재 채널을 시나리오에 배정합니다.")
    @app_commands.describe(시나리오="등록된 시나리오 이름")
    @app_commands.guild_only()
    async def start(self, interaction: discord.Interaction, 시나리오: str) -> None:
        scenario = await get_scenario_by_title(self.pool, interaction.guild_id, 시나리오)
        if scenario is None:
            await interaction.response.send_message("등록된 시나리오가 아닙니다.", ephemeral=True)
            return
        if scenario["keeper_user_id"] != interaction.user.id:
            await interaction.response.send_message(
                "이 시나리오의 키퍼만 시작할 수 있습니다.", ephemeral=True
            )
            return
        bound = await bind_scenario_channel(
            self.pool, interaction.guild_id, 시나리오, interaction.channel_id
        )
        if not bound:
            await interaction.response.send_message(
                "이 채널에는 이미 다른 시나리오가 배정돼 있습니다.", ephemeral=True
            )
            return
        await interaction.response.send_message(f"이 채널을 '{시나리오}' 시나리오에 배정했습니다.")

    @app_commands.command(name="시나리오조회", description="현재 채널의 시나리오 정보를 조회합니다.")
    @app_commands.guild_only()
    async def info(self, interaction: discord.Interaction) -> None:
        scenario = await get_scenario_by_channel(self.pool, interaction.channel_id)
        if scenario is None:
            await interaction.response.send_message(
                "이 채널에 배정된 시나리오가 없습니다.", ephemeral=True
            )
            return
        roster = await get_roster(self.pool, scenario["id"])
        embed = scenario_embed(scenario, roster)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ScenarioCog(bot))
