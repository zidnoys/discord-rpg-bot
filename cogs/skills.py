import discord
from discord import app_commands
from discord.ext import commands

import database as db
from utils.embeds import get_classes_data, get_skills_data


class Skills(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="habilidades", description="Veja as habilidades da sua classe."
    )
    async def habilidades(self, interaction: discord.Interaction):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        skills_data = get_skills_data()
        classes_data = get_classes_data()
        char_class = char["char_class"]
        cls = classes_data.get(char_class, {})
        skills = skills_data.get(char_class, [])

        embed = discord.Embed(
            title=f"{cls.get('emoji', '⚔️')} Habilidades — {cls.get('name', char_class)}",
            description=f"Nível atual: **{char['level']}**",
            color=discord.Color.purple(),
        )

        for skill in skills:
            unlocked = char["level"] >= skill["level_required"]
            status = "✅" if unlocked else "🔒"

            details = [f"MP: {skill['mp_cost']}"]
            if "damage_multiplier" in skill:
                details.append(f"Dano: x{skill['damage_multiplier']}")
            if "hits" in skill:
                details.append(f"Hits: {skill['hits']}")
            if skill.get("element", "none") != "none":
                element_emojis = {
                    "fogo": "🔥",
                    "gelo": "❄️",
                    "raio": "⚡",
                    "agua": "💧",
                    "terra": "🌍",
                    "luz": "✨",
                    "trevas": "🌙",
                }
                elem = skill["element"]
                details.append(f"Elemento: {element_emojis.get(elem, '')} {elem}")
            if "crit_bonus" in skill:
                details.append(f"Crit+: {int(skill['crit_bonus'] * 100)}%")
            if "stun_chance" in skill:
                details.append(f"Stun: {int(skill['stun_chance'] * 100)}%")
            if "armor_pierce" in skill:
                details.append(f"Perfurar: {int(skill['armor_pierce'] * 100)}%")

            name = f"{status} {skill['emoji']} {skill['name']}"
            if not unlocked:
                name += f" (Lv.{skill['level_required']})"

            embed.add_field(
                name=name,
                value=f"{skill['description']}\n`{' | '.join(details)}`",
                inline=False,
            )

        embed.set_footer(
            text="Use habilidades durante o combate com o botão 🎯 Habilidade!"
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Skills(bot))
