import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import keeper_narration_embed
from storage import advance_narration_position, get_roster, get_scenario_by_channel


class NarrationView(discord.ui.View):
    def __init__(
        self,
        pool,
        scenario_id: int,
        structure: list[dict],
        scene_index: int,
        line_index: int,
        eligible_user_ids: set[int],
    ) -> None:
        super().__init__(timeout=900)
        self.pool = pool
        self.scenario_id = scenario_id
        self.structure = structure
        self.scene_index = scene_index
        self.line_index = line_index
        self.eligible_user_ids = eligible_user_ids
        self.votes: set[int] = set()
        self.required_votes = (2 * len(eligible_user_ids) + 2) // 3

    @discord.ui.button(label="다음", style=discord.ButtonStyle.primary)
    async def advance(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        user_id = interaction.user.id
        if user_id not in self.eligible_user_ids:
            await interaction.response.send_message(
                "시나리오 참가자만 투표할 수 있습니다.", ephemeral=True
            )
            return
        if user_id in self.votes:
            await interaction.response.send_message("이미 투표했습니다.", ephemeral=True)
            return

        self.votes.add(user_id)
        if len(self.votes) < self.required_votes:
            button.label = f"다음 ({len(self.votes)}/{self.required_votes})"
            await interaction.response.edit_message(view=self)
            return

        next_position = _next_position(self.structure, self.scene_index, self.line_index)
        target = next_position or (len(self.structure), 0)
        advanced = await advance_narration_position(
            self.pool,
            self.scenario_id,
            self.scene_index,
            self.line_index,
            *target,
        )
        if not advanced:
            self.stop()
            await interaction.response.edit_message(
                content="다른 낭독 진행에서 이미 장면이 이동했습니다.", embed=None, view=None
            )
            return
        if next_position is None:
            self.stop()
            await interaction.response.edit_message(
                content="낭독이 완료되었습니다.", embed=None, view=None
            )
            return

        scene_index, line_index = next_position
        scene = self.structure[scene_index]
        view = NarrationView(
            self.pool,
            self.scenario_id,
            self.structure,
            scene_index,
            line_index,
            self.eligible_user_ids,
        )
        await interaction.response.edit_message(
            embed=keeper_narration_embed(scene["scene"], scene["lines"][line_index]),
            view=view,
        )


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

    @app_commands.command(name="낭독시작", description="Keeper 낭독을 참가자 2/3 동의로 진행합니다.")
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
        if line_index >= len(structure[scene_index]["lines"]):
            await interaction.response.send_message(
                "시나리오 진행 위치가 올바르지 않습니다.", ephemeral=True
            )
            return

        keeper_user_id = scenario["keeper_user_id"]
        roster = await get_roster(self.pool, scenario["id"])
        eligible_user_ids = {keeper_user_id} | {
            character["discord_user_id"] for character in roster
        }
        if interaction.user.id not in eligible_user_ids:
            await interaction.response.send_message(
                "키퍼 또는 시나리오 참가 PC만 낭독을 시작할 수 있습니다.", ephemeral=True
            )
            return

        scene = structure[scene_index]
        view = NarrationView(
            self.pool,
            scenario["id"],
            structure,
            scene_index,
            line_index,
            eligible_user_ids,
        )
        await interaction.response.send_message(
            embed=keeper_narration_embed(scene["scene"], scene["lines"][line_index]),
            view=view,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NarrationCog(bot))
