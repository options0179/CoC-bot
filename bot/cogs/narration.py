import math

import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import keeper_narration_embed
from storage import advance_narration_position, get_roster, get_scenario_by_channel


class NarrationView(discord.ui.View):
    def __init__(self, roster_user_ids: set[int], keeper_user_id: int) -> None:
        super().__init__(timeout=None)
        self.roster_user_ids = roster_user_ids
        self.keeper_user_id = keeper_user_id
        self.votes: set[int] = set()

    def _required_votes(self) -> int:
        denominator = len(self.roster_user_ids) + 1
        return math.ceil(denominator * 2 / 3)

    @discord.ui.button(label="다음", style=discord.ButtonStyle.primary)
    async def advance(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        user_id = interaction.user.id
        if user_id != self.keeper_user_id and user_id not in self.roster_user_ids:
            await interaction.response.send_message(
                "이 시나리오의 참가자만 투표할 수 있습니다.", ephemeral=True
            )
            return
        if user_id in self.votes:
            await interaction.response.send_message("이미 동의했습니다.", ephemeral=True)
            return
        self.votes.add(user_id)
        required = self._required_votes()
        if len(self.votes) < required:
            await interaction.response.send_message(
                f"동의 {len(self.votes)}/{len(self.roster_user_ids) + 1} ({required}표 필요)",
                ephemeral=True,
            )
            return
        button.disabled = True
        self.stop()
        await interaction.response.edit_message(view=self)


def _next_position(
    structure: list[dict], scene_index: int, line_index: int
) -> tuple[int, int] | None:
    if line_index + 1 < len(structure[scene_index]["lines"]):
        return scene_index, line_index + 1
    next_scene = scene_index + 1
    if next_scene < len(structure):
        return next_scene, 0
    return None


class NarrationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.pool = bot.pool

    @app_commands.command(name="낭독시작", description="Keeper 낭독을 문장 단위로 진행합니다.")
    @app_commands.guild_only()
    async def start(self, interaction: discord.Interaction) -> None:
        scenario = await get_scenario_by_channel(self.pool, interaction.channel_id)
        if scenario is None:
            await interaction.response.send_message(
                "이 채널에 배정된 시나리오가 없습니다.", ephemeral=True
            )
            return
        structure = scenario["structure"]
        scene_index = scenario["current_scene_index"]
        line_index = scenario["current_line_index"]
        if scene_index >= len(structure):
            await interaction.response.send_message(
                "낭독할 내용이 남아있지 않습니다.", ephemeral=True
            )
            return

        roster = await get_roster(self.pool, scenario["id"])
        roster_user_ids = {character["discord_user_id"] for character in roster}
        keeper_user_id = scenario["keeper_user_id"]

        scene = structure[scene_index]
        embed = keeper_narration_embed(scene["scene"], scene["lines"][line_index])
        view = NarrationView(roster_user_ids, keeper_user_id)
        await interaction.response.send_message(embed=embed, view=view)

        while True:
            await view.wait()
            nxt = _next_position(structure, scene_index, line_index)
            if nxt is None:
                await interaction.followup.send(
                    "이 장면의 낭독은 여기까지입니다. 이후는 키퍼가 진행해주세요."
                )
                return
            scene_index, line_index = nxt
            await advance_narration_position(self.pool, scenario["id"], scene_index, line_index)
            scene = structure[scene_index]
            embed = keeper_narration_embed(scene["scene"], scene["lines"][line_index])
            view = NarrationView(roster_user_ids, keeper_user_id)
            await interaction.followup.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NarrationCog(bot))
