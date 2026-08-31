import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import opposed_embed
from dice import opposed_check


class OpposedCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="대립", description="두 스킬을 대립판정합니다.")
    @app_commands.describe(내스킬="내 스킬 값 (0-100)", 상대스킬="상대 스킬 값 (0-100)")
    async def opposed(
        self,
        interaction: discord.Interaction,
        내스킬: app_commands.Range[int, 0, 100],
        상대스킬: app_commands.Range[int, 0, 100],
    ) -> None:
        result = opposed_check(내스킬, 상대스킬)
        embed = opposed_embed(result, label_a="나", label_b="상대")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OpposedCog(bot))
