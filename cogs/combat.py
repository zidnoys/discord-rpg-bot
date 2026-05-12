import discord
import random
from discord import app_commands
from discord.ext import commands

import database as db
from config import POINTS_PER_LEVEL
from utils.embeds import (
    combat_embed,
    get_items_data,
    get_monsters_data,
    get_skills_data,
    hp_bar,
)
from utils.formulas import (
    calculate_damage,
    get_element_text,
    scale_monster,
    xp_for_level,
)
from utils.views import CombatView, ItemSelectView


class Combat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_combats: set[int] = set()

    @app_commands.command(
        name="caçar", description="Saia para caçar monstros e ganhar XP e ouro!"
    )
    async def cacar(self, interaction: discord.Interaction):
        char = await db.get_character(interaction.user.id)
        if not char:
            await interaction.response.send_message(
                "❌ Você não tem um personagem! Use `/criar` para começar.",
                ephemeral=True,
            )
            return

        if interaction.user.id in self.active_combats:
            await interaction.response.send_message(
                "❌ Você já está em combate!", ephemeral=True
            )
            return

        if char["hp"] <= 0:
            await interaction.response.send_message(
                "💀 Seu HP está em 0! Use `/descansar` para recuperar.",
                ephemeral=True,
            )
            return

        monsters_data = get_monsters_data()
        available = {
            mid: m
            for mid, m in monsters_data.items()
            if m["level_range"][0] <= char["level"] + 3
        }
        if not available:
            available = monsters_data

        monster_id = random.choice(list(available.keys()))
        monster_template = available[monster_id]

        scaled_stats = scale_monster(
            monster_template["base_stats"],
            char["level"],
            monster_template["level_range"],
        )

        monster = {
            "id": monster_id,
            "name": monster_template["name"],
            "emoji": monster_template["emoji"],
            "element": monster_template["element"],
            "level": scaled_stats["level"],
            "xp_reward": monster_template["xp_reward"],
            "gold_reward": monster_template["gold_reward"],
            "drops": monster_template.get("drops", []),
            "drop_chance": monster_template.get("drop_chance", 0),
            **scaled_stats,
        }

        monster_hp = monster["hp"]
        monster_max_hp = monster["hp"]

        self.active_combats.add(interaction.user.id)

        skills_data = get_skills_data()
        char_skills = [
            s
            for s in skills_data.get(char["char_class"], [])
            if s["level_required"] <= char["level"]
        ]

        equipment = await db.get_equipment(interaction.user.id)
        total_stats = self._get_total_stats(char, equipment)

        turn = 1
        log = f"🐾 Um **{monster['emoji']} {monster['name']}** (Lv.{monster['level']}) apareceu!"

        embed = combat_embed(char, monster, monster_hp, monster_max_hp, turn, log)
        view = CombatView(interaction.user.id, char_skills)
        await interaction.response.send_message(embed=embed, view=view)

        while True:
            await view.wait()

            if view.action is None:
                self.active_combats.discard(interaction.user.id)
                await interaction.edit_original_response(
                    content="⏰ Combate encerrado por inatividade.",
                    embed=None,
                    view=None,
                )
                return

            action = view.action

            if action == "flee":
                flee_chance = 0.4 + (total_stats["speed"] - monster.get("speed", 10)) * 0.02
                if random.random() < min(0.9, max(0.1, flee_chance)):
                    self.active_combats.discard(interaction.user.id)
                    await db.update_character(interaction.user.id, hp=char["hp"])
                    await interaction.edit_original_response(
                        content="🏃 Você fugiu do combate com sucesso!",
                        embed=None,
                        view=None,
                    )
                    return
                else:
                    log = "🏃 Você tentou fugir mas falhou!"

            elif action == "attack":
                damage, is_crit = calculate_damage(
                    total_stats["attack"],
                    monster.get("defense", 0),
                    luck=total_stats["luck"],
                )
                monster_hp -= damage
                crit_text = " **CRÍTICO!**" if is_crit else ""
                log = f"⚔️ Você atacou e causou **{damage}** de dano!{crit_text}"

            elif action == "skill" and view.skill_index is not None:
                skill = char_skills[view.skill_index]
                if char["mp"] < skill["mp_cost"]:
                    log = f"❌ MP insuficiente para **{skill['name']}**! (Precisa: {skill['mp_cost']})"
                else:
                    char["mp"] -= skill["mp_cost"]
                    log = await self._use_skill(
                        skill, char, total_stats, monster, monster_hp
                    )
                    result = log
                    if isinstance(result, tuple):
                        log, monster_hp = result
                    else:
                        damage_dealt = self._extract_skill_damage(
                            skill, total_stats, monster
                        )
                        monster_hp -= damage_dealt
                        log = result

            elif action == "item":
                inventory = await db.get_inventory(interaction.user.id)
                items_data = get_items_data()
                consumables = []
                for inv_item in inventory:
                    item_id = inv_item["item_id"]
                    if item_id in items_data and items_data[item_id]["type"] == "consumable":
                        consumables.append(
                            {
                                **items_data[item_id],
                                "item_id": item_id,
                                "quantity": inv_item["quantity"],
                            }
                        )

                if not consumables:
                    log = "❌ Você não tem itens consumíveis!"
                else:
                    item_view = ItemSelectView(interaction.user.id, consumables)
                    msg = await interaction.followup.send(
                        "🧪 Escolha um item:", view=item_view, ephemeral=True
                    )
                    await item_view.wait()

                    if item_view.selected_item:
                        item = items_data[item_view.selected_item]
                        await db.remove_item(interaction.user.id, item_view.selected_item)
                        effect = item.get("effect", {})
                        heal_hp = effect.get("heal_hp", 0)
                        heal_mp = effect.get("heal_mp", 0)
                        char["hp"] = min(char["max_hp"], char["hp"] + heal_hp)
                        char["mp"] = min(char["max_mp"], char["mp"] + heal_mp)
                        parts = []
                        if heal_hp:
                            parts.append(f"+{heal_hp} HP")
                        if heal_mp:
                            parts.append(f"+{heal_mp} MP")
                        log = f"🧪 Usou **{item['name']}**! ({', '.join(parts)})"
                    else:
                        log = "❌ Nenhum item selecionado."

            if monster_hp <= 0:
                monster_hp = 0
                self.active_combats.discard(interaction.user.id)
                await self._victory(interaction, char, monster)
                return

            monster_damage, _ = calculate_damage(
                monster.get("attack", 10),
                total_stats["defense"],
            )
            char["hp"] -= monster_damage
            log += f"\n{monster['emoji']} **{monster['name']}** atacou e causou **{monster_damage}** de dano!"

            if char["hp"] <= 0:
                char["hp"] = 0
                self.active_combats.discard(interaction.user.id)
                await db.update_character(interaction.user.id, hp=0, mp=char["mp"])
                embed = combat_embed(
                    char, monster, monster_hp, monster_max_hp, turn, log
                )
                embed.add_field(
                    name="💀 Derrota!",
                    value="Você foi derrotado... Use `/descansar` para recuperar.",
                    inline=False,
                )
                await interaction.edit_original_response(embed=embed, view=None)
                return

            turn += 1
            embed = combat_embed(char, monster, monster_hp, monster_max_hp, turn, log)
            view = CombatView(interaction.user.id, char_skills)
            await interaction.edit_original_response(embed=embed, view=view)

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
                    item = items_data[item_id]
                    for stat, value in item.get("stats", {}).items():
                        if stat in stats:
                            stats[stat] += value

        return stats

    def _extract_skill_damage(
        self, skill: dict, total_stats: dict, monster: dict
    ) -> int:
        if "damage_multiplier" not in skill:
            return 0

        stat_key = skill.get("stat", "attack")
        attacker_stat = total_stats.get(stat_key, total_stats["attack"])
        hits = skill.get("hits", 1)
        total_damage = 0

        for _ in range(hits):
            damage, _ = calculate_damage(
                attacker_stat,
                monster.get("defense", 0),
                multiplier=skill["damage_multiplier"],
                element=skill.get("element", "none"),
                defender_element=monster.get("element", "none"),
                armor_pierce=skill.get("armor_pierce", 0),
                crit_bonus=skill.get("crit_bonus", 0),
                luck=total_stats["luck"],
            )
            total_damage += damage

        return total_damage

    async def _use_skill(
        self,
        skill: dict,
        char: dict,
        total_stats: dict,
        monster: dict,
        monster_hp: int,
    ) -> str:
        parts = [f"🎯 Usou **{skill['name']}**!"]

        if "damage_multiplier" in skill:
            stat_key = skill.get("stat", "attack")
            attacker_stat = total_stats.get(stat_key, total_stats["attack"])
            hits = skill.get("hits", 1)
            total_damage = 0

            for i in range(hits):
                damage, is_crit = calculate_damage(
                    attacker_stat,
                    monster.get("defense", 0),
                    multiplier=skill["damage_multiplier"],
                    element=skill.get("element", "none"),
                    defender_element=monster.get("element", "none"),
                    armor_pierce=skill.get("armor_pierce", 0),
                    crit_bonus=skill.get("crit_bonus", 0),
                    luck=total_stats["luck"],
                )
                total_damage += damage

            element_text = get_element_text(
                skill.get("element", "none"), monster.get("element", "none")
            )
            if hits > 1:
                parts.append(f"({hits} hits) Dano total: **{total_damage}**!{element_text}")
            else:
                parts.append(f"Causou **{total_damage}** de dano!{element_text}")

        effect = skill.get("effect", {})
        if "self_buff" in effect:
            buff_parts = []
            for stat, val in effect["self_buff"].items():
                if stat in total_stats:
                    total_stats[stat] += val
                    buff_parts.append(f"{stat.upper()} +{val}")
            if buff_parts:
                parts.append(f"Buff: {', '.join(buff_parts)} ({effect.get('duration', 1)} turnos)")

        if "heal_hp_multiplier" in effect:
            heal_amount = int(total_stats.get("magic", 10) * effect["heal_hp_multiplier"])
            char["hp"] = min(char["max_hp"], char["hp"] + heal_amount)
            parts.append(f"Curou **{heal_amount}** HP!")

        if "enemy_debuff" in effect:
            debuff_parts = []
            for stat, val in effect["enemy_debuff"].items():
                if stat in monster:
                    monster[stat] = max(0, monster[stat] + val)
                    debuff_parts.append(f"{stat.upper()} {val}")
            if debuff_parts:
                parts.append(f"Debuff no inimigo: {', '.join(debuff_parts)}")

        return " ".join(parts)

    async def _victory(
        self, interaction: discord.Interaction, char: dict, monster: dict
    ):
        xp_gain = monster["xp_reward"]
        gold_gain = random.randint(*monster["gold_reward"])

        new_xp = char["xp"] + xp_gain
        new_gold = char["gold"] + gold_gain
        new_level = char["level"]
        new_stat_points = char["stat_points"]
        level_ups = 0

        classes_data = get_classes_data()
        growth = classes_data.get(char["char_class"], {}).get("growth", {})

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
            "monsters_killed": char["monsters_killed"] + 1,
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

        drop_text = ""
        if monster["drops"] and random.random() < monster["drop_chance"]:
            drop_id = random.choice(monster["drops"])
            items_data = get_items_data()
            if drop_id in items_data:
                await db.add_item(interaction.user.id, drop_id)
                drop_item = items_data[drop_id]
                drop_text = f"\n🎁 Drop: **{drop_item['emoji']} {drop_item['name']}**!"

        await db.update_character(interaction.user.id, **updates)

        embed = discord.Embed(
            title="🏆 Vitória!",
            description=(
                f"Você derrotou **{monster['emoji']} {monster['name']}**!\n\n"
                f"⭐ XP: +{xp_gain}\n"
                f"💰 Ouro: +{gold_gain}G\n"
                f"{drop_text}"
            ),
            color=discord.Color.green(),
        )

        if level_ups > 0:
            embed.add_field(
                name="🎉 LEVEL UP!",
                value=(
                    f"Nível {char['level']} → **{new_level}**\n"
                    f"📌 +{level_ups * POINTS_PER_LEVEL} pontos de atributo disponíveis!\n"
                    f"Use `/atributos` para distribuí-los."
                ),
                inline=False,
            )

        await interaction.edit_original_response(embed=embed, view=None)


async def setup(bot: commands.Bot):
    await bot.add_cog(Combat(bot))
