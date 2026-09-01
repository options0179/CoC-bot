import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import check_embed, narration_embed
from dice import roll_check
from intent_analyzer import analyze_intent
from storage import get_skill_value

logger = logging.getLogger(__name__)


class ActionCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.pool = bot.pool

    @app_commands.command(
        name="행동", description="자유 서술 행동을 분석해 필요한 판정을 자동으로 굴립니다."
    )
    @app_commands.describe(설명="캐릭터가 하려는 행동을 문장으로 적어주세요.")
    @app_commands.guild_only()
    async def action(self, interaction: discord.Interaction, 설명: str) -> None:
        await interaction.response.defer()
        try:
            intent = await asyncio.to_thread(analyze_intent, 설명, "")
        except ValueError:
            logger.exception("Failed to analyze intent")
            await interaction.followup.send(
                "행동을 분석하지 못했습니다. 다시 서술해 주세요.", ephemeral=True
            )
            return

        if not intent.requires_roll or intent.target_skill == "unknown":
            await interaction.followup.send(
                embed=narration_embed(intent.action_summary, intent.purpose)
            )
            return

        skill_value = await get_skill_value(
            self.pool, interaction.guild_id, interaction.user.id, intent.target_skill
        )
        if skill_value is None:
            await interaction.followup.send(
                f"{intent.target_skill} 스킬 값을 캐릭터 시트에서 찾을 수 없습니다.",
                ephemeral=True,
            )
            return

        result = roll_check(skill_value)
        await interaction.followup.send(
            embed=check_embed(result, label=f"{intent.target_skill} 판정")
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ActionCog(bot))
