import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import check_embed
from dice import is_success, roll_check


class PushView(discord.ui.View):
    def __init__(self, skill: int, bonus: int, penalty: int) -> None:
        super().__init__(timeout=300)
        self.skill = skill
        self.bonus = bonus
        self.penalty = penalty
        self.pushed = False

    @discord.ui.button(label="푸시", style=discord.ButtonStyle.danger)
    async def push(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.pushed:
            await interaction.response.send_message("이미 푸시했습니다.", ephemeral=True)
            return
        self.pushed = True
        button.disabled = True
        result = roll_check(self.skill, bonus=self.bonus, penalty=self.penalty)
        embed = check_embed(result, label="푸시 판정")
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=embed)


class CheckCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="판정", description="CoC 스킬 판정을 굴립니다.")
    @app_commands.describe(
        스킬값="판정할 스킬 값 (0-100)",
        보너스="보너스 주사위 개수 (0-2)",
        페널티="페널티 주사위 개수 (0-2)",
    )
    async def check(
        self,
        interaction: discord.Interaction,
        스킬값: app_commands.Range[int, 0, 100],
        보너스: app_commands.Range[int, 0, 2] = 0,
        페널티: app_commands.Range[int, 0, 2] = 0,
    ) -> None:
        result = roll_check(스킬값, bonus=보너스, penalty=페널티)
        embed = check_embed(result)
        view = None if is_success(result.level) else PushView(스킬값, 보너스, 페널티)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CheckCog(bot))
