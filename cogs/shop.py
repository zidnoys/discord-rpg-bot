import discord
from discord import app_commands
from discord.ext import commands

import database as db
from utils.embeds import get_items_data


SHOP_ITEMS = [
    "pocao_pequena",
    "pocao_media",
    "pocao_grande",
    "pocao_mana",
    "elixir",
    "espada_ferro",
    "arco_curto",
    "cajado_aprendiz",
    "escudo_madeira",
    "armadura_couro",
    "espada_aco",
    "katana",
    "rifle_cacador",
    "escudo_ferro",
    "armadura_ferro",
    "manto_mago",
    "anel_sorte",
    "amuleto_vida",
]


class Shop(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="loja", description="Veja os itens disponíveis na loja."
    )
    async def loja(self, interaction: discord.Interaction):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        items_data = get_items_data()
        embed = discord.Embed(
            title="🏪 Loja",
            description=f"💰 Seu ouro: **{char['gold']}G**\n\n"
            f"Use `/comprar <nome>` para comprar e `/vender <nome>` para vender.",
            color=discord.Color.gold(),
        )

        categories = {
            "consumable": ("🧪 Consumíveis", []),
            "weapon": ("⚔️ Armas", []),
            "armor": ("🛡️ Armaduras & Escudos", []),
            "accessory": ("💍 Acessórios", []),
        }

        for item_id in SHOP_ITEMS:
            if item_id not in items_data:
                continue
            item = items_data[item_id]
            if item.get("price", 0) <= 0:
                continue

            cat = item["type"]
            if cat not in categories:
                continue

            line = f"{item['emoji']} **{item['name']}** — {item['price']}G"
            if "stats" in item:
                stat_parts = [f"{k}+{v}" for k, v in item["stats"].items() if v > 0]
                if stat_parts:
                    line += f" ({', '.join(stat_parts)})"
            if item.get("required_level", 1) > 1:
                line += f" [Lv.{item['required_level']}]"
            categories[cat][1].append(line)

        for cat_key, (cat_name, items) in categories.items():
            if items:
                embed.add_field(
                    name=cat_name, value="\n".join(items), inline=False
                )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="comprar", description="Compre um item da loja.")
    @app_commands.describe(
        item="Nome do item para comprar", quantidade="Quantidade (padrão: 1)"
    )
    async def comprar(
        self,
        interaction: discord.Interaction,
        item: str,
        quantidade: int = 1,
    ):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        if quantidade < 1:
            await interaction.response.send_message(
                "❌ Quantidade inválida!", ephemeral=True
            )
            return

        items_data = get_items_data()
        item_lower = item.lower()
        found_id = None

        for item_id in SHOP_ITEMS:
            if item_id in items_data:
                if items_data[item_id]["name"].lower() == item_lower:
                    found_id = item_id
                    break

        if not found_id:
            await interaction.response.send_message(
                f"❌ Item **{item}** não encontrado na loja!", ephemeral=True
            )
            return

        item_data = items_data[found_id]
        total_cost = item_data["price"] * quantidade

        if char["gold"] < total_cost:
            await interaction.response.send_message(
                f"❌ Ouro insuficiente! Precisa: **{total_cost}G** | Tem: **{char['gold']}G**",
                ephemeral=True,
            )
            return

        required_level = item_data.get("required_level", 1)
        if char["level"] < required_level:
            await interaction.response.send_message(
                f"❌ Você precisa ser nível **{required_level}** para comprar este item!",
                ephemeral=True,
            )
            return

        await db.update_character(
            interaction.user.id, gold=char["gold"] - total_cost
        )
        await db.add_item(interaction.user.id, found_id, quantidade)

        qty_text = f" x{quantidade}" if quantidade > 1 else ""
        await interaction.response.send_message(
            f"✅ Comprou **{item_data['emoji']} {item_data['name']}{qty_text}** "
            f"por **{total_cost}G**!\n"
            f"💰 Ouro restante: **{char['gold'] - total_cost}G**"
        )

    @app_commands.command(name="vender", description="Venda um item do inventário.")
    @app_commands.describe(
        item="Nome do item para vender", quantidade="Quantidade (padrão: 1)"
    )
    async def vender(
        self,
        interaction: discord.Interaction,
        item: str,
        quantidade: int = 1,
    ):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        if quantidade < 1:
            await interaction.response.send_message(
                "❌ Quantidade inválida!", ephemeral=True
            )
            return

        items_data = get_items_data()
        inventory = await db.get_inventory(interaction.user.id)

        item_lower = item.lower()
        found_id = None
        for inv_item in inventory:
            iid = inv_item["item_id"]
            if iid in items_data and items_data[iid]["name"].lower() == item_lower:
                if inv_item["quantity"] >= quantidade:
                    found_id = iid
                    break

        if not found_id:
            await interaction.response.send_message(
                f"❌ Item **{item}** não encontrado ou quantidade insuficiente!",
                ephemeral=True,
            )
            return

        item_data = items_data[found_id]
        sell_price = item_data.get("sell_price", 1)
        total_gold = sell_price * quantidade

        success = await db.remove_item(interaction.user.id, found_id, quantidade)
        if not success:
            await interaction.response.send_message(
                "❌ Erro ao remover item!", ephemeral=True
            )
            return

        await db.update_character(
            interaction.user.id, gold=char["gold"] + total_gold
        )

        qty_text = f" x{quantidade}" if quantidade > 1 else ""
        await interaction.response.send_message(
            f"✅ Vendeu **{item_data['emoji']} {item_data['name']}{qty_text}** "
            f"por **{total_gold}G**!\n"
            f"💰 Ouro total: **{char['gold'] + total_gold}G**"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Shop(bot))
