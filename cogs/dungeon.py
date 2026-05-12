import discord
import random
from discord import app_commands
from discord.ext import commands

import database as db
from config import POINTS_PER_LEVEL
from utils.embeds import (
    combat_embed,
    get_classes_data,
    get_dungeons_data,
    get_items_data,
    get_monsters_data,
    get_skills_data,
)
from utils.formulas import calculate_damage, get_element_text, scale_monster, xp_for_level
from utils.views import CombatView, ItemSelectView


class Dungeon(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_dungeons: set[int] = set()

    @app_commands.command(
        name="dungeons", description="Veja as dungeons disponíveis."
    )
    async def dungeons(self, interaction: discord.Interaction):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        dungeons_data = get_dungeons_data()

        embed = discord.Embed(
            title="🏰 Dungeons Disponíveis",
            description="Use `/dungeon <nome>` para entrar em uma dungeon.",
            color=discord.Color.dark_purple(),
        )

        for dungeon_id, dungeon in dungeons_data.items():
            unlocked = char["level"] >= dungeon["level_required"]
            status = "✅" if unlocked else "🔒"

            embed.add_field(
                name=f"{status} {dungeon['emoji']} {dungeon['name']} (Lv.{dungeon['level_required']})",
                value=(
                    f"{dungeon['description']}\n"
                    f"📊 Andares: {dungeon['floors']} | "
                    f"⭐ XP Bônus: x{dungeon['xp_bonus']} | "
                    f"💰 Ouro Bônus: x{dungeon['gold_bonus']}"
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dungeon", description="Entre em uma dungeon!")
    @app_commands.describe(nome="Nome da dungeon")
    async def dungeon(self, interaction: discord.Interaction, nome: str):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem!", ephemeral=True
            )
            return

        if interaction.user.id in self.active_dungeons:
            await interaction.response.send_message(
                "❌ Você já está em uma dungeon!", ephemeral=True
            )
            return

        if char["hp"] <= 0:
            await interaction.response.send_message(
                "💀 Seu HP está em 0! Use `/descansar` para recuperar.",
                ephemeral=True,
            )
            return

        dungeons_data = get_dungeons_data()
        nome_lower = nome.lower()
        found_id = None

        for did, d in dungeons_data.items():
            if d["name"].lower() == nome_lower:
                found_id = did
                break

        if not found_id:
            names = [d["name"] for d in dungeons_data.values()]
            await interaction.response.send_message(
                f"❌ Dungeon **{nome}** não encontrada!\nDisponíveis: {', '.join(names)}",
                ephemeral=True,
            )
            return

        dungeon = dungeons_data[found_id]

        if char["level"] < dungeon["level_required"]:
            await interaction.response.send_message(
                f"❌ Você precisa ser nível **{dungeon['level_required']}** para esta dungeon!",
                ephemeral=True,
            )
            return

        self.active_dungeons.add(interaction.user.id)
        await interaction.response.send_message(
            f"{dungeon['emoji']} Entrando na **{dungeon['name']}**...\n"
            f"📊 Andares: {dungeon['floors']} | Prepare-se!"
        )

        monsters_data = get_monsters_data()
        items_data = get_items_data()
        skills_data = get_skills_data()
        classes_data = get_classes_data()
        growth = classes_data.get(char["char_class"], {}).get("growth", {})

        char_skills = [
            s
            for s in skills_data.get(char["char_class"], [])
            if s["level_required"] <= char["level"]
        ]

        equipment = await db.get_equipment(interaction.user.id)
        total_xp = 0
        total_gold = 0
        floors_cleared = 0

        for floor in range(1, dungeon["floors"] + 1):
            is_boss = floor == dungeon["floors"]
            monster_id = random.choice(dungeon["monsters"])

            if is_boss:
                monster_id = dungeon["boss"]

            if monster_id not in monsters_data:
                continue

            monster_template = monsters_data[monster_id]
            scaled = scale_monster(
                monster_template["base_stats"],
                char["level"],
                monster_template["level_range"],
            )

            monster = {
                "id": monster_id,
                "name": monster_template["name"],
                "emoji": monster_template["emoji"],
                "element": monster_template["element"],
                "level": scaled["level"],
                **scaled,
            }

            if is_boss:
                mult = dungeon["boss_multiplier"]
                monster["hp"] = int(monster["hp"] * mult)
                monster["attack"] = int(monster["attack"] * mult)
                monster["defense"] = int(monster["defense"] * mult)
                monster["name"] = f"👑 BOSS: {monster['name']}"

            monster_hp = monster["hp"]
            monster_max_hp = monster["hp"]

            total_stats = self._get_total_stats(char, equipment)

            floor_label = f"BOSS" if is_boss else f"{floor}/{dungeon['floors']}"
            turn = 1
            log = (
                f"🏰 **Andar {floor_label}** — "
                f"{monster['emoji']} **{monster['name']}** (Lv.{monster['level']}) apareceu!"
            )

            embed = combat_embed(char, monster, monster_hp, monster_max_hp, turn, log)
            view = CombatView(interaction.user.id, char_skills)
            msg = await interaction.followup.send(embed=embed, view=view)

            while True:
                await view.wait()

                if view.action is None:
                    self.active_dungeons.discard(interaction.user.id)
                    await db.update_character(
                        interaction.user.id, hp=char["hp"], mp=char["mp"]
                    )
                    await msg.edit(
                        content="⏰ Dungeon encerrada por inatividade.",
                        embed=None,
                        view=None,
                    )
                    return

                action = view.action

                if action == "flee":
                    self.active_dungeons.discard(interaction.user.id)
                    await db.update_character(
                        interaction.user.id, hp=char["hp"], mp=char["mp"]
                    )
                    await msg.edit(
                        content=(
                            f"🏃 Você fugiu da dungeon no andar {floor}!\n"
                            f"⭐ XP ganho: {total_xp} | 💰 Ouro: {total_gold}G"
                        ),
                        embed=None,
                        view=None,
                    )
                    await self._apply_dungeon_rewards(
                        interaction.user.id, char, total_xp, total_gold, floors_cleared, growth
                    )
                    return

                elif action == "attack":
                    damage, is_crit = calculate_damage(
                        total_stats["attack"],
                        monster.get("defense", 0),
                        luck=total_stats["luck"],
                    )
                    monster_hp -= damage
                    crit_text = " **CRÍTICO!**" if is_crit else ""
                    log = f"⚔️ Causou **{damage}** de dano!{crit_text}"

                elif action == "skill" and view.skill_index is not None:
                    skill = char_skills[view.skill_index]
                    if char["mp"] < skill["mp_cost"]:
                        log = f"❌ MP insuficiente para **{skill['name']}**!"
                    else:
                        char["mp"] -= skill["mp_cost"]
                        total_damage = self._calc_skill_damage(
                            skill, total_stats, monster
                        )
                        monster_hp -= total_damage
                        element_text = get_element_text(
                            skill.get("element", "none"),
                            monster.get("element", "none"),
                        )
                        log = f"🎯 **{skill['name']}** causou **{total_damage}** de dano!{element_text}"

                        effect = skill.get("effect", {})
                        if "heal_hp_multiplier" in effect:
                            heal = int(total_stats["magic"] * effect["heal_hp_multiplier"])
                            char["hp"] = min(char["max_hp"], char["hp"] + heal)
                            log += f" Curou **{heal}** HP!"

                elif action == "item":
                    inventory = await db.get_inventory(interaction.user.id)
                    consumables = []
                    for inv_item in inventory:
                        iid = inv_item["item_id"]
                        if iid in items_data and items_data[iid]["type"] == "consumable":
                            consumables.append({
                                **items_data[iid],
                                "item_id": iid,
                                "quantity": inv_item["quantity"],
                            })

                    if not consumables:
                        log = "❌ Sem itens consumíveis!"
                    else:
                        item_view = ItemSelectView(interaction.user.id, consumables)
                        item_msg = await interaction.followup.send(
                            "🧪 Escolha um item:", view=item_view, ephemeral=True
                        )
                        await item_view.wait()

                        if item_view.selected_item:
                            sel_item = items_data[item_view.selected_item]
                            await db.remove_item(interaction.user.id, item_view.selected_item)
                            effect = sel_item.get("effect", {})
                            heal_hp = effect.get("heal_hp", 0)
                            heal_mp = effect.get("heal_mp", 0)
                            char["hp"] = min(char["max_hp"], char["hp"] + heal_hp)
                            char["mp"] = min(char["max_mp"], char["mp"] + heal_mp)
                            log = f"🧪 Usou **{sel_item['name']}**!"
                        else:
                            log = "❌ Nenhum item selecionado."

                if monster_hp <= 0:
                    monster_hp = 0
                    xp_gain = int(
                        monsters_data.get(monster["id"], {}).get("xp_reward", 50)
                        * dungeon["xp_bonus"]
                    )
                    gold_gain = int(
                        random.randint(
                            *monsters_data.get(monster["id"], {}).get(
                                "gold_reward", [10, 30]
                            )
                        )
                        * dungeon["gold_bonus"]
                    )
                    total_xp += xp_gain
                    total_gold += gold_gain
                    floors_cleared += 1

                    await msg.edit(
                        content=(
                            f"🏆 Derrotou **{monster['name']}**! "
                            f"(+{xp_gain} XP, +{gold_gain}G)"
                        ),
                        embed=None,
                        view=None,
                    )
                    break

                m_dmg, _ = calculate_damage(
                    monster.get("attack", 10), total_stats["defense"]
                )
                char["hp"] -= m_dmg
                log += f"\n{monster['emoji']} **{monster['name']}** causou **{m_dmg}** de dano!"

                if char["hp"] <= 0:
                    char["hp"] = 0
                    self.active_dungeons.discard(interaction.user.id)
                    await db.update_character(interaction.user.id, hp=0, mp=char["mp"])
                    await msg.edit(
                        content=(
                            f"💀 Você foi derrotado no andar {floor}!\n"
                            f"⭐ XP ganho: {total_xp} | 💰 Ouro: {total_gold}G\n"
                            f"Use `/descansar` para recuperar."
                        ),
                        embed=None,
                        view=None,
                    )
                    await self._apply_dungeon_rewards(
                        interaction.user.id, char, total_xp, total_gold, 0, growth
                    )
                    return

                turn += 1
                embed = combat_embed(
                    char, monster, monster_hp, monster_max_hp, turn, log
                )
                view = CombatView(interaction.user.id, char_skills)
                await msg.edit(embed=embed, view=view)

        self.active_dungeons.discard(interaction.user.id)

        reward_items = dungeon.get("reward_items", [])
        drop_text = ""
        if reward_items:
            drop_id = random.choice(reward_items)
            if drop_id in items_data:
                await db.add_item(interaction.user.id, drop_id)
                drop_text = f"\n🎁 Recompensa: **{items_data[drop_id]['emoji']} {items_data[drop_id]['name']}**!"

        await self._apply_dungeon_rewards(
            interaction.user.id, char, total_xp, total_gold, 1, growth
        )

        embed = discord.Embed(
            title=f"🏆 Dungeon Completa: {dungeon['name']}!",
            description=(
                f"Todos os {dungeon['floors']} andares foram conquistados!\n\n"
                f"⭐ XP Total: +{total_xp}\n"
                f"💰 Ouro Total: +{total_gold}G\n"
                f"{drop_text}"
            ),
            color=discord.Color.gold(),
        )

        await interaction.followup.send(embed=embed)

    def _get_total_stats(self, char: dict, equipment: dict | None) -> dict:
        stats = {
            "hp": char["hp"],
            "max_hp": char["max_hp"],
            "mp": char["mp"],
            "max_mp": char["max_mp"],
            "attack": char["attack"],
            "defense": char["defense"],
            "magic": char["magic"],
            "speed": char["speed"],
            "luck": char["luck"],
        }
        if equipment:
            items_data = get_items_data()
            for slot in ["weapon", "armor", "shield", "accessory"]:
                item_id = equipment.get(slot)
                if item_id and item_id in items_data:
                    for stat, value in items_data[item_id].get("stats", {}).items():
                        if stat in stats:
                            stats[stat] += value
        return stats

    def _calc_skill_damage(
        self, skill: dict, total_stats: dict, monster: dict
    ) -> int:
        if "damage_multiplier" not in skill:
            return 0
        stat_key = skill.get("stat", "attack")
        attacker_stat = total_stats.get(stat_key, total_stats["attack"])
        hits = skill.get("hits", 1)
        total = 0
        for _ in range(hits):
            dmg, _ = calculate_damage(
                attacker_stat,
                monster.get("defense", 0),
                multiplier=skill["damage_multiplier"],
                element=skill.get("element", "none"),
                defender_element=monster.get("element", "none"),
                armor_pierce=skill.get("armor_pierce", 0),
                crit_bonus=skill.get("crit_bonus", 0),
                luck=total_stats["luck"],
            )
            total += dmg
        return total

    async def _apply_dungeon_rewards(
        self,
        user_id: int,
        char: dict,
        total_xp: int,
        total_gold: int,
        dungeons_cleared: int,
        growth: dict,
    ):
        new_xp = char.get("xp", 0) + total_xp
        new_gold = char.get("gold", 0) + total_gold
        new_level = char["level"]
        new_stat_points = char["stat_points"]
        level_ups = 0

        while new_xp >= xp_for_level(new_level):
            new_xp -= xp_for_level(new_level)
            new_level += 1
            new_stat_points += POINTS_PER_LEVEL
            level_ups += 1

        updates = {
            "xp": new_xp,
            "gold": new_gold,
            "level": new_level,
            "stat_points": new_stat_points,
            "hp": char["hp"],
            "mp": char["mp"],
            "dungeons_cleared": char["dungeons_cleared"] + dungeons_cleared,
        }

        if level_ups > 0:
            updates["max_hp"] = char["max_hp"] + growth.get("hp", 10) * level_ups
            updates["max_mp"] = char["max_mp"] + growth.get("mp", 5) * level_ups
            updates["attack"] = char["attack"] + growth.get("attack", 2) * level_ups
            updates["defense"] = char["defense"] + growth.get("defense", 2) * level_ups
            updates["magic"] = char["magic"] + growth.get("magic", 1) * level_ups
            updates["speed"] = char["speed"] + growth.get("speed", 1) * level_ups
            updates["luck"] = char["luck"] + growth.get("luck", 1) * level_ups
            updates["hp"] = updates["max_hp"]
            updates["mp"] = updates["max_mp"]

        await db.update_character(user_id, **updates)


async def setup(bot: commands.Bot):
    await bot.add_cog(Dungeon(bot))
