import asyncio
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import check_embed, narration_embed
from dice import is_success, roll_check
from intent_analyzer import IntentResponseBlocked, IntentResponseEmpty, analyze_intent
from sheet_parser import SKILL_NAMES
from storage import get_roster, get_scenario_by_channel, get_skill_value

logger = logging.getLogger(__name__)

_MANUAL_CHECK = "현재 장면에서 자동 판정 규칙을 확인할 수 없습니다. 필요하면 /판정 명령으로 진행해 주세요."


def _analysis_error_message(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, IntentResponseBlocked):
        return "blocked", "안전 필터가 행동 분석을 차단했습니다. 표현을 바꿔 다시 시도해 주세요."
    if isinstance(exc, IntentResponseEmpty):
        return "empty", "행동 분석 응답이 비어 있습니다. 잠시 후 다시 시도해 주세요."
    if isinstance(exc, ValueError):
        return "malformed", "행동 분석 응답 형식이 올바르지 않습니다. 잠시 후 다시 시도해 주세요."
    code = getattr(exc, "code", None)
    if code in (401, 403):
        return "auth", "Gemini 인증 또는 권한을 확인해야 합니다. 관리자에게 알려 주세요."
    if code == 404:
        return "model_not_found", "Gemini 모델을 사용할 수 없습니다. 모델 이름과 API 접근 권한을 확인해 주세요."
    if code == 429:
        return "rate_limit", "Gemini 요청 제한에 도달했습니다. 잠시 후 다시 시도해 주세요."
    if isinstance(code, int) and 500 <= code < 600:
        return "service", "Gemini 서비스 오류로 행동을 분석하지 못했습니다. 잠시 후 다시 시도해 주세요."
    if isinstance(exc, (OSError, TimeoutError)) or type(exc).__module__.startswith(("httpx.", "httpcore.")):
        return "network", "Gemini 연결 또는 제한시간 오류입니다. 잠시 후 다시 시도해 주세요."
    return "provider", "Gemini 행동 분석에 실패했습니다. 잠시 후 다시 시도해 주세요."


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
        if not os.environ.get("GEMINI_API_KEY"):
            await interaction.response.send_message(
                "/행동 기능은 GEMINI_API_KEY 설정이 필요합니다.", ephemeral=True
            )
            return
        await interaction.response.defer()
        scenario = await get_scenario_by_channel(self.pool, interaction.channel_id)
        scene = None
        if scenario and scenario["guild_id"] == interaction.guild_id:
            index = scenario["current_scene_index"]
            if 0 <= index < len(scenario["structure"]):
                scene = scenario["structure"][index]
        checks = scene.get("checks", []) if scene else []
        line_index = scenario["current_line_index"] if scene else 0
        line = scene["lines"][line_index] if scene and 0 <= line_index < len(scene["lines"]) else ""
        context = f"{scenario['title']} / {scene['scene']}\n{line}" if scene else ""
        try:
            intent = await asyncio.to_thread(analyze_intent, 설명, context, checks)
        except Exception as exc:
            category, message = _analysis_error_message(exc)
            logger.warning("Gemini action analysis failed: %s", category)
            await interaction.followup.send(message, ephemeral=True)
            return

        rule = next((check for check in checks if check["id"] == intent.check_id), None)
        if not intent.requires_roll and not rule:
            await interaction.followup.send(
                embed=narration_embed(intent.action_summary, intent.purpose)
            )
            return

        if not rule or intent.confidence < 0.6 or rule["skill"] not in SKILL_NAMES:
            await interaction.followup.send(_MANUAL_CHECK, ephemeral=True)
            return

        roster = await get_roster(self.pool, scenario["id"])
        if interaction.user.id not in {pc["discord_user_id"] for pc in roster}:
            await interaction.followup.send("시나리오에 참가한 PC가 필요합니다. 참가 후 시도하거나 /판정을 사용해 주세요.", ephemeral=True)
            return

        skill_value = await get_skill_value(
            self.pool, interaction.guild_id, interaction.user.id, rule["skill"]
        )
        if type(skill_value) is not int or not 0 <= skill_value <= 100:
            await interaction.followup.send(
                f"{rule['skill']} 기능값을 캐릭터 시트에서 확인할 수 없습니다. /판정을 사용해 주세요.",
                ephemeral=True,
            )
            return

        current = await get_scenario_by_channel(self.pool, interaction.channel_id)
        if not current or (current["id"], current["current_scene_index"], current["current_line_index"]) != (
            scenario["id"], scenario["current_scene_index"], scenario["current_line_index"]
        ):
            await interaction.followup.send("처리하는 동안 장면이 이동했습니다. /행동 명령을 다시 입력해 주세요.", ephemeral=True)
            return

        result = roll_check(skill_value)
        embed = check_embed(result, label=f"{rule['skill']} 판정")
        embed.add_field(name="이야기", value=rule["success"] if is_success(result.level) else rule["failure"], inline=False)
        await interaction.followup.send(
            embed=embed
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ActionCog(bot))
