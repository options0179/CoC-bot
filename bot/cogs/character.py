import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import character_embed
from sheet_parser import parse_character_sheet
from storage import (
    close_registration,
    get_character,
    is_registration_open,
    open_registration,
    upsert_character,
)


class CharacterCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.pool = bot.pool

    @app_commands.command(name="캐릭터등록열기", description="캐릭터 등록창을 엽니다.")
    async def open_window(self, interaction: discord.Interaction) -> None:
        opened = await open_registration(self.pool, interaction.guild_id, interaction.user.id)
        if not opened:
            await interaction.response.send_message(
                "이미 다른 사람이 등록창을 열어뒀습니다.", ephemeral=True
            )
            return
        await interaction.response.send_message("캐릭터 등록창을 열었습니다.")

    @app_commands.command(name="캐릭터등록닫기", description="캐릭터 등록창을 닫습니다.")
    async def close_window(self, interaction: discord.Interaction) -> None:
        closed = await close_registration(self.pool, interaction.guild_id, interaction.user.id)
        if not closed:
            await interaction.response.send_message(
                "본인이 연 등록창만 닫을 수 있습니다.", ephemeral=True
            )
            return
        await interaction.response.send_message("캐릭터 등록창을 닫았습니다.")

    @app_commands.command(name="캐릭터등록", description="엑셀 캐릭터시트를 등록합니다.")
    @app_commands.describe(파일="캐릭터시트 xlsx 파일")
    async def register(
        self, interaction: discord.Interaction, 파일: discord.Attachment
    ) -> None:
        if not await is_registration_open(self.pool, interaction.guild_id):
            await interaction.response.send_message(
                "지금은 등록 기간이 아닙니다.", ephemeral=True
            )
            return
        file_bytes = await 파일.read()
        try:
            data = parse_character_sheet(file_bytes)
        except ValueError as exc:
            await interaction.response.send_message(
                f"시트를 읽을 수 없습니다: {exc}", ephemeral=True
            )
            return
        await upsert_character(self.pool, interaction.guild_id, interaction.user.id, data)
        await interaction.response.send_message(f"{data['name']} 캐릭터를 등록했습니다.")

    @app_commands.command(name="캐릭터조회", description="등록된 캐릭터를 조회합니다.")
    @app_commands.describe(유저="조회할 유저 (생략 시 본인)")
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CharacterCog(bot))
