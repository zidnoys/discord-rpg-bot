import discord
from discord import app_commands
from discord.ext import commands

import database as db
from utils.embeds import get_items_data
from config import MAX_INVENTORY_SIZE


class Inventory(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="inventario", description="Veja seu inventário de itens."
    )
    async def inventario(self, interaction: discord.Interaction):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        inventory = await db.get_inventory(interaction.user.id)
        items_data = get_items_data()

        if not inventory:
            await interaction.response.send_message(
                "🎒 Seu inventário está vazio!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🎒 Inventário de {char['name']}",
            color=discord.Color.orange(),
        )

        categories = {
            "weapon": ("⚔️ Armas", []),
            "armor": ("🛡️ Armaduras/Escudos", []),
            "accessory": ("💍 Acessórios", []),
            "consumable": ("🧪 Consumíveis", []),
            "material": ("📦 Materiais", []),
        }

        for inv_item in inventory:
            item_id = inv_item["item_id"]
            if item_id not in items_data:
                continue
            item = items_data[item_id]
            item_type = item["type"]
            if item_type not in categories:
                item_type = "material"
            qty = f" x{inv_item['quantity']}" if inv_item["quantity"] > 1 else ""
            line = f"{item['emoji']} **{item['name']}**{qty}"
            if "stats" in item:
                stat_parts = [
                    f"{k.upper()}+{v}" for k, v in item["stats"].items() if v > 0
                ]
                if stat_parts:
                    line += f" ({', '.join(stat_parts)})"
            if "sell_price" in item and item["sell_price"] > 0:
                line += f" [Venda: {item['sell_price']}G]"
            categories[item_type][1].append(line)

        for cat_key, (cat_name, items) in categories.items():
            if items:
                embed.add_field(
                    name=cat_name, value="\n".join(items), inline=False
                )

        total_items = sum(inv["quantity"] for inv in inventory)
        embed.set_footer(text=f"Itens: {total_items}/{MAX_INVENTORY_SIZE}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="equipar", description="Equipe um item do inventário.")
    @app_commands.describe(item="Nome do item para equipar")
    async def equipar(self, interaction: discord.Interaction, item: str):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        inventory = await db.get_inventory(interaction.user.id)
        items_data = get_items_data()

        item_lower = item.lower()
        found_id = None
        for inv_item in inventory:
            iid = inv_item["item_id"]
            if iid in items_data:
                if items_data[iid]["name"].lower() == item_lower:
                    found_id = iid
                    break

        if not found_id:
            for iid, idata in items_data.items():
                if idata["name"].lower() == item_lower:
                    found_id = iid
                    break

        if not found_id:
            await interaction.response.send_message(
                f"❌ Item **{item}** não encontrado no inventário!", ephemeral=True
            )
            return

        item_data = items_data[found_id]

        has_item = any(inv["item_id"] == found_id for inv in inventory)
        if not has_item:
            await interaction.response.send_message(
                f"❌ Você não possui **{item_data['name']}** no inventário!",
                ephemeral=True,
            )
            return

        if item_data["type"] not in ("weapon", "armor", "accessory"):
            await interaction.response.send_message(
                "❌ Este item não pode ser equipado!", ephemeral=True
            )
            return

        slot = item_data.get("slot", item_data["type"])
        required_level = item_data.get("required_level", 1)

        if char["level"] < required_level:
            await interaction.response.send_message(
                f"❌ Você precisa ser nível **{required_level}** para equipar este item!",
                ephemeral=True,
            )
            return

        equipment = await db.get_equipment(interaction.user.id)
        old_item = equipment.get(slot) if equipment else None

        if old_item:
            await db.add_item(interaction.user.id, old_item)

        await db.remove_item(interaction.user.id, found_id)
        await db.equip_item(interaction.user.id, slot, found_id)

        slot_names = {
            "weapon": "Arma",
            "armor": "Armadura",
            "shield": "Escudo",
            "accessory": "Acessório",
        }

        msg = f"✅ Equipou **{item_data['emoji']} {item_data['name']}** no slot de {slot_names.get(slot, slot)}!"
        if old_item and old_item in items_data:
            msg += f"\n📦 **{items_data[old_item]['name']}** foi para o inventário."

        await interaction.response.send_message(msg)

    @app_commands.command(
        name="desequipar", description="Desequipe um item."
    )
    @app_commands.describe(slot="Slot para desequipar")
    @app_commands.choices(
        slot=[
            app_commands.Choice(name="Arma", value="weapon"),
            app_commands.Choice(name="Armadura", value="armor"),
            app_commands.Choice(name="Escudo", value="shield"),
            app_commands.Choice(name="Acessório", value="accessory"),
        ]
    )
    async def desequipar(
        self, interaction: discord.Interaction, slot: app_commands.Choice[str]
    ):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        equipment = await db.get_equipment(interaction.user.id)
        item_id = equipment.get(slot.value) if equipment else None

        if not item_id:
            await interaction.response.send_message(
                f"❌ Nada equipado no slot de **{slot.name}**!", ephemeral=True
            )
            return

        items_data = get_items_data()
        await db.add_item(interaction.user.id, item_id)
        await db.equip_item(interaction.user.id, slot.value, None)

        item_name = items_data[item_id]["name"] if item_id in items_data else item_id
        await interaction.response.send_message(
            f"✅ **{item_name}** desequipado e movido para o inventário!"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Inventory(bot))
