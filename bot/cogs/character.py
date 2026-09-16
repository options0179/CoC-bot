import os

import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import character_embed
from storage import create_registration_token, get_character, get_scenario_by_title


def _build_registration_url(token: str) -> str:
    base_url = (
        os.environ.get("RENDER_EXTERNAL_URL")
        or f"http://localhost:{os.environ.get('PORT', '8080')}"
    ).rstrip("/")
    return f"{base_url}/register/{token}"


class CharacterCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.pool = bot.pool

    @app_commands.command(name="캐릭터등록", description="캐릭터시트를 등록합니다.")
    @app_commands.guild_only()
    async def register(self, interaction: discord.Interaction) -> None:
        token = await create_registration_token(
            self.pool, interaction.guild_id, interaction.user.id, role="PC"
        )
        url = _build_registration_url(token)
        await interaction.response.send_message(
            f"아래 링크에서 캐릭터를 등록하세요 (30분간 유효, 1회용):\n{url}",
            ephemeral=True,
        )

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
        name="시나리오캐릭터등록", description="시나리오의 KPC/NPC 캐릭터시트를 등록합니다."
    )
    @app_commands.describe(시나리오="시나리오 이름", 직책="KPC 또는 NPC")
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

        token = await create_registration_token(
            self.pool,
            interaction.guild_id,
            interaction.user.id,
            role=직책.value,
            scenario_id=scenario["id"],
        )
        url = _build_registration_url(token)
        await interaction.response.send_message(
            f"아래 링크에서 {직책.value}를 등록하세요 (30분간 유효, 1회용):\n{url}",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CharacterCog(bot))
