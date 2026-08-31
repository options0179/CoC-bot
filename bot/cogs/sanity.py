import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import sanity_embed
from dice import sanity_check


class SanityCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="산정", description="SAN 체크를 굴립니다.")
    @app_commands.describe(
        현재san="현재 SAN 값",
        손실식="성공손실/실패손실 형식 (예: 1/1d4+1)",
    )
    async def sanity(
        self,
        interaction: discord.Interaction,
        현재san: app_commands.Range[int, 0, 99],
        손실식: str,
    ) -> None:
        result = sanity_check(현재san, 손실식)
        await interaction.response.send_message(embed=sanity_embed(result))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SanityCog(bot))
