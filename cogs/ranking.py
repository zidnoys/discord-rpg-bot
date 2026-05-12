import discord
from discord import app_commands
from discord.ext import commands

import database as db
from utils.embeds import get_classes_data


class Ranking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ranking", description="Veja o ranking dos jogadores!"
    )
    @app_commands.describe(categoria="Categoria do ranking")
    @app_commands.choices(
        categoria=[
            app_commands.Choice(name="Nível", value="level"),
            app_commands.Choice(name="Ouro", value="gold"),
            app_commands.Choice(name="Monstros Derrotados", value="monsters_killed"),
            app_commands.Choice(name="Dungeons Completadas", value="dungeons_cleared"),
        ]
    )
    async def ranking(
        self,
        interaction: discord.Interaction,
        categoria: app_commands.Choice[str] | None = None,
    ):
        order_by = categoria.value if categoria else "level"
        cat_name = categoria.name if categoria else "Nível"

        leaderboard = await db.get_leaderboard(order_by=order_by, limit=10)

        if not leaderboard:
            await interaction.response.send_message(
                "📊 Nenhum jogador registrado ainda!", ephemeral=True
            )
            return

        classes_data = get_classes_data()

        embed = discord.Embed(
            title=f"🏆 Ranking — {cat_name}",
            color=discord.Color.gold(),
        )

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, char in enumerate(leaderboard):
            medal = medals[i] if i < 3 else f"`{i + 1}.`"
            cls = classes_data.get(char["char_class"], {})
            emoji = cls.get("emoji", "⚔️")

            value_map = {
                "level": f"Lv.{char['level']}",
                "gold": f"{char['gold']}G",
                "monsters_killed": f"{char['monsters_killed']} monstros",
                "dungeons_cleared": f"{char['dungeons_cleared']} dungeons",
            }

            value = value_map.get(order_by, f"Lv.{char['level']}")
            lines.append(
                f"{medal} {emoji} **{char['name']}** — {value}"
            )

        embed.description = "\n".join(lines)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Ranking(bot))
