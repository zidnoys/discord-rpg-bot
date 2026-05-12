import discord
from discord import app_commands
from discord.ext import commands

import database as db
from config import POINTS_PER_LEVEL
from utils.embeds import get_classes_data, profile_embed
from utils.formulas import xp_for_level
from utils.views import ClassSelectView, ConfirmView


class Character(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="criar", description="Crie seu personagem de RPG!")
    @app_commands.describe(nome="Nome do seu personagem")
    async def criar(self, interaction: discord.Interaction, nome: str):
        existing = await db.get_character(interaction.user.id)
        if existing:
            await interaction.response.send_message(
                f"❌ Você já tem um personagem: **{existing['name']}**!\n"
                f"Use `/deletar` se quiser recomeçar.",
                ephemeral=True,
            )
            return

        if len(nome) > 20:
            await interaction.response.send_message(
                "❌ O nome deve ter no máximo 20 caracteres!", ephemeral=True
            )
            return

        view = ClassSelectView(interaction.user.id)
        classes = get_classes_data()

        desc_lines = []
        for class_id, cls in classes.items():
            stats = cls["base_stats"]
            desc_lines.append(
                f"{cls['emoji']} **{cls['name']}** — {cls['description']}\n"
                f"> HP:{stats['hp']} MP:{stats['mp']} ATK:{stats['attack']} "
                f"DEF:{stats['defense']} MAG:{stats['magic']} SPD:{stats['speed']} LCK:{stats['luck']}"
            )

        embed = discord.Embed(
            title="⚔️ Criação de Personagem",
            description=f"**Nome:** {nome}\n\nEscolha sua classe:\n\n"
            + "\n\n".join(desc_lines),
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()

        if view.selected_class is None:
            await interaction.edit_original_response(
                content="⏰ Tempo esgotado! Use `/criar` novamente.",
                embed=None,
                view=None,
            )
            return

        cls_data = classes[view.selected_class]
        await db.create_character(
            interaction.user.id, nome, view.selected_class, cls_data["base_stats"]
        )

        char = await db.get_character(interaction.user.id)
        equipment = await db.get_equipment(interaction.user.id)
        embed = profile_embed(char, equipment)
        embed.title = f"🎉 Personagem Criado!"
        embed.description = (
            f"Bem-vindo, **{nome}**! Sua jornada como "
            f"**{cls_data['name']}** começa agora!\n\n"
            f"Use `/caçar` para enfrentar monstros e `/perfil` para ver seus status."
        )

        await interaction.edit_original_response(embed=embed, view=None)

    @app_commands.command(name="perfil", description="Veja o perfil do seu personagem.")
    async def perfil(self, interaction: discord.Interaction):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem! Use `/criar` para começar.",
                ephemeral=True,
            )
            return

        equipment = await db.get_equipment(interaction.user.id)
        embed = profile_embed(char, equipment)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="atributos", description="Distribua pontos de atributo."
    )
    @app_commands.describe(
        atributo="Atributo para aumentar",
        pontos="Quantidade de pontos",
    )
    @app_commands.choices(
        atributo=[
            app_commands.Choice(name="HP (+10 por ponto)", value="max_hp"),
            app_commands.Choice(name="MP (+5 por ponto)", value="max_mp"),
            app_commands.Choice(name="Ataque", value="attack"),
            app_commands.Choice(name="Defesa", value="defense"),
            app_commands.Choice(name="Magia", value="magic"),
            app_commands.Choice(name="Velocidade", value="speed"),
            app_commands.Choice(name="Sorte", value="luck"),
        ]
    )
    async def atributos(
        self,
        interaction: discord.Interaction,
        atributo: app_commands.Choice[str],
        pontos: int,
    ):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        if pontos < 1:
            await interaction.response.send_message(
                "❌ Informe pelo menos 1 ponto!", ephemeral=True
            )
            return

        if char["stat_points"] < pontos:
            await interaction.response.send_message(
                f"❌ Você só tem **{char['stat_points']}** pontos disponíveis!",
                ephemeral=True,
            )
            return

        stat_key = atributo.value
        multiplier = 10 if stat_key == "max_hp" else (5 if stat_key == "max_mp" else 1)
        increase = pontos * multiplier

        updates = {
            stat_key: char[stat_key] + increase,
            "stat_points": char["stat_points"] - pontos,
        }

        if stat_key == "max_hp":
            updates["hp"] = char["hp"] + increase
        elif stat_key == "max_mp":
            updates["mp"] = char["mp"] + increase

        await db.update_character(interaction.user.id, **updates)

        stat_names = {
            "max_hp": "HP",
            "max_mp": "MP",
            "attack": "Ataque",
            "defense": "Defesa",
            "magic": "Magia",
            "speed": "Velocidade",
            "luck": "Sorte",
        }

        await interaction.response.send_message(
            f"✅ **{stat_names[stat_key]}** aumentou em **+{increase}**! "
            f"(Pontos restantes: {updates['stat_points']})"
        )

    @app_commands.command(
        name="descansar", description="Descanse para recuperar HP e MP."
    )
    async def descansar(self, interaction: discord.Interaction):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        if char["hp"] == char["max_hp"] and char["mp"] == char["max_mp"]:
            await interaction.response.send_message(
                "💤 Você já está com HP e MP cheios!", ephemeral=True
            )
            return

        cost = max(10, char["level"] * 5)
        if char["gold"] < cost:
            await interaction.response.send_message(
                f"❌ Você precisa de **{cost}G** para descansar e só tem **{char['gold']}G**!",
                ephemeral=True,
            )
            return

        await db.update_character(
            interaction.user.id,
            hp=char["max_hp"],
            mp=char["max_mp"],
            gold=char["gold"] - cost,
        )

        await interaction.response.send_message(
            f"💤 Você descansou e recuperou toda a sua vida e mana!\n"
            f"❤️ HP: {char['max_hp']}/{char['max_hp']} | "
            f"💙 MP: {char['max_mp']}/{char['max_mp']}\n"
            f"💰 Custo: {cost}G"
        )

    @app_commands.command(
        name="deletar", description="Delete seu personagem (irreversível!)."
    )
    async def deletar(self, interaction: discord.Interaction):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        view = ConfirmView(interaction.user.id)
        await interaction.response.send_message(
            f"⚠️ Tem certeza que deseja deletar **{char['name']}** "
            f"(Lv.{char['level']})? Essa ação é **irreversível**!",
            view=view,
        )

        await view.wait()
        if view.confirmed:
            await db.delete_character(interaction.user.id)
            await interaction.edit_original_response(
                content=f"🗑️ **{char['name']}** foi deletado. Use `/criar` para recomeçar.",
                view=None,
            )
        else:
            await interaction.edit_original_response(
                content="✅ Cancelado. Seu personagem está a salvo!",
                view=None,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Character(bot))
