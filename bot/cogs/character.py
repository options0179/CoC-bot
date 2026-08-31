import discord
from discord import app_commands
from discord.ext import commands

from storage import close_registration, open_registration


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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CharacterCog(bot))
