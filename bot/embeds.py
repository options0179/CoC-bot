import discord

from dice import CheckResult, OpposedResult, SanityResult, SuccessLevel

_LEVEL_LABELS = {
    SuccessLevel.CRITICAL: "크리티컬 성공",
    SuccessLevel.EXTREME: "익스트림 성공",
    SuccessLevel.HARD: "하드 성공",
    SuccessLevel.REGULAR: "성공",
    SuccessLevel.FAIL: "실패",
    SuccessLevel.FUMBLE: "펌블",
}

_SUCCESS_COLOR = discord.Color.green()
_FAIL_COLOR = discord.Color.red()


def _level_color(level: SuccessLevel) -> discord.Color:
    return _FAIL_COLOR if level in (SuccessLevel.FAIL, SuccessLevel.FUMBLE) else _SUCCESS_COLOR


def check_embed(result: CheckResult, label: str = "판정") -> discord.Embed:
    embed = discord.Embed(
        title=label,
        description=f"1D100 = **{result.roll}** / 스킬값 {result.skill}",
        color=_level_color(result.level),
    )
    embed.add_field(name="결과", value=_LEVEL_LABELS[result.level])
    return embed


def sanity_embed(result: SanityResult) -> discord.Embed:
    outcome = "성공" if result.success else "실패"
    embed = discord.Embed(
        title="SAN 체크",
        description=f"1D100 = **{result.roll}** / 현재 SAN {result.current_san}",
        color=_SUCCESS_COLOR if result.success else _FAIL_COLOR,
    )
    embed.add_field(name="결과", value=outcome)
    embed.add_field(name="SAN 손실", value=f"-{result.loss}")
    embed.add_field(name="남은 SAN", value=str(result.remaining_san))
    return embed


def opposed_embed(
    result: OpposedResult, label_a: str = "A", label_b: str = "B"
) -> discord.Embed:
    winner_text = {
        "a": f"{label_a} 승리",
        "b": f"{label_b} 승리",
        "tie": "무승부",
    }[result.winner]
    embed = discord.Embed(title="대립판정", color=discord.Color.blurple())
    embed.add_field(
        name=label_a, value=f"{result.a.roll} → {_LEVEL_LABELS[result.a.level]}", inline=True
    )
    embed.add_field(
        name=label_b, value=f"{result.b.roll} → {_LEVEL_LABELS[result.b.level]}", inline=True
    )
    embed.add_field(name="결과", value=winner_text, inline=False)
    return embed


def character_embed(character: dict, owner_name: str) -> discord.Embed:
    embed = discord.Embed(title=character.get("name") or owner_name)
    embed.add_field(name="직업", value=character.get("occupation") or "-", inline=False)
    embed.add_field(
        name="특성치",
        value=(
            f"STR {character['str']} DEX {character['dex']} POW {character['pow']}\n"
            f"CON {character['con']} APP {character['app']} EDU {character['edu']}\n"
            f"SIZ {character['siz']} INT {character['int']} MOV {character['mov']}"
        ),
        inline=False,
    )
    skills = character.get("skills") or {}
    top_skills = sorted(skills.items(), key=lambda kv: kv[1], reverse=True)[:10]
    if top_skills:
        embed.add_field(
            name="주요 기능",
            value="\n".join(f"{name}: {value}" for name, value in top_skills),
            inline=False,
        )
    return embed
