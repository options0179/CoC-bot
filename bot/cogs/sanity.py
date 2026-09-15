import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import sanity_embed
from dice import sanity_check
from storage import get_pc_character, update_san_current


class SanityCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.pool = bot.pool

    @app_commands.command(name="산정", description="SAN 체크를 굴립니다.")
    @app_commands.describe(손실식="성공손실/실패손실 형식 (예: 1/1d4+1)")
    @app_commands.guild_only()
    async def sanity(self, interaction: discord.Interaction, 손실식: str) -> None:
        character = await get_pc_character(self.pool, interaction.guild_id, interaction.user.id)
        if character is None:
            await interaction.response.send_message("등록된 캐릭터가 없습니다.", ephemeral=True)
            return
        if character["is_retired"]:
            await interaction.response.send_message(
                "이미 영구적 광기로 퇴장한 캐릭터입니다.", ephemeral=True
            )
            return

        current_san = character["san_current"]
        result = sanity_check(current_san, 손실식)
        await update_san_current(
            self.pool, interaction.guild_id, interaction.user.id, result.remaining_san
        )

        warnings = []
        if result.loss >= 5:
            warnings.append("이번 손실이 5 이상 — 일시적 광기 판정 필요(INT 판정, 키퍼 재량으로 진행)")
        if current_san > 0 and result.loss >= current_san / 5:
            warnings.append("이번 손실이 직전 SAN의 1/5 이상 — 부정형 광기 위험")
        if result.remaining_san == 0:
            warnings.append("SAN 0 도달 — 영구적 광기로 퇴장 처리되었습니다")
        await interaction.response.send_message(embed=sanity_embed(result, warnings))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SanityCog(bot))
