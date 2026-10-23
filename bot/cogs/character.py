import asyncio
import re

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import character_embed
from bot.google_exports import GoogleExportTooLarge, fetch_google_sheet
from sheet_parser import parse_character_sheet
from storage import get_character, get_scenario_by_title, upsert_character

_SHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)")


def _extract_sheet_id(url: str) -> str | None:
    match = _SHEET_ID_RE.search(url)
    return match.group(1) if match else None


class CharacterCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.pool = bot.pool

    @app_commands.command(name="캐릭터등록", description="구글 스프레드시트 캐릭터시트를 등록합니다.")
    @app_commands.describe(링크="캐릭터시트 구글 스프레드시트 링크(링크가 있는 모든 사용자에게 공개)")
    @app_commands.guild_only()
    async def register(
        self, interaction: discord.Interaction, 링크: str
    ) -> None:
        sheet_id = _extract_sheet_id(링크)
        if sheet_id is None:
            await interaction.response.send_message(
                "구글 스프레드시트 링크가 아닙니다.", ephemeral=True
            )
            return
        await interaction.response.defer()
        try:
            file_bytes = await fetch_google_sheet(sheet_id)
        except GoogleExportTooLarge:
            await interaction.followup.send("시트 파일이 10MB 제한을 초과했습니다.", ephemeral=True)
            return
        except (aiohttp.ClientError, TimeoutError) as exc:
            await interaction.followup.send(f"시트를 가져오는 중 오류: {exc}", ephemeral=True)
            return
        if file_bytes is None:
            await interaction.followup.send(
                "시트를 가져올 수 없습니다. 링크 공개 설정을 확인하세요.", ephemeral=True
            )
            return
        try:
            data = await asyncio.to_thread(parse_character_sheet, file_bytes)
        except ValueError as exc:
            await interaction.followup.send(
                f"시트를 읽을 수 없습니다: {exc}", ephemeral=True
            )
            return
        await upsert_character(self.pool, interaction.guild_id, interaction.user.id, data)
        await interaction.followup.send(f"{data['name']} 캐릭터를 등록했습니다.")

    @app_commands.command(name="캐릭터조회", description="등록된 캐릭터를 조회합니다.")
    @app_commands.describe(유저="조회할 유저 (생략 시 본인)")
    @app_commands.guild_only()
    async def lookup(
        self,
        interaction: discord.Interaction,
        유저: discord.Member | None = None,
    ) -> None:
        target = 유저 or interaction.user
        character = await get_character(self.pool, interaction.guild_id, target.id)
        if character is None:
            await interaction.response.send_message(
                "등록된 캐릭터가 없습니다.", ephemeral=True
            )
            return
        embed = character_embed(character, target.display_name)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="시나리오캐릭터등록", description="시나리오의 KPC/NPC 구글 스프레드시트 캐릭터시트를 등록합니다."
    )
    @app_commands.describe(
        시나리오="시나리오 이름", 직책="KPC 또는 NPC", 링크="캐릭터시트 구글 스프레드시트 링크(링크가 있는 모든 사용자에게 공개)"
    )
    @app_commands.choices(
        직책=[
            app_commands.Choice(name="KPC", value="KPC"),
            app_commands.Choice(name="NPC", value="NPC"),
        ]
    )
    @app_commands.guild_only()
    async def register_scenario_character(
        self,
        interaction: discord.Interaction,
        시나리오: str,
        직책: app_commands.Choice[str],
        링크: str,
    ) -> None:
        scenario = await get_scenario_by_title(self.pool, interaction.guild_id, 시나리오)
        if scenario is None:
            await interaction.response.send_message("등록된 시나리오가 아닙니다.", ephemeral=True)
            return
        if scenario["keeper_user_id"] != interaction.user.id:
            await interaction.response.send_message(
                "이 시나리오의 키퍼만 등록할 수 있습니다.", ephemeral=True
            )
            return
        sheet_id = _extract_sheet_id(링크)
        if sheet_id is None:
            await interaction.response.send_message(
                "구글 스프레드시트 링크가 아닙니다.", ephemeral=True
            )
            return
        await interaction.response.defer()
        try:
            file_bytes = await fetch_google_sheet(sheet_id)
        except GoogleExportTooLarge:
            await interaction.followup.send("시트 파일이 10MB 제한을 초과했습니다.", ephemeral=True)
            return
        except (aiohttp.ClientError, TimeoutError) as exc:
            await interaction.followup.send(f"시트를 가져오는 중 오류: {exc}", ephemeral=True)
            return
        if file_bytes is None:
            await interaction.followup.send(
                "시트를 가져올 수 없습니다. 링크 공개 설정을 확인하세요.", ephemeral=True
            )
            return
        try:
            data = await asyncio.to_thread(parse_character_sheet, file_bytes)
        except ValueError as exc:
            await interaction.followup.send(f"시트를 읽을 수 없습니다: {exc}", ephemeral=True)
            return
        await upsert_character(
            self.pool,
            interaction.guild_id,
            interaction.user.id,
            data,
            role=직책.value,
            scenario_id=scenario["id"],
        )
        await interaction.followup.send(f"{data['name']} ({직책.value})을(를) 등록했습니다.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CharacterCog(bot))
