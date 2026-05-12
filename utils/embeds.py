import discord
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def load_json(filename: str) -> dict:
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def get_classes_data() -> dict:
    return load_json("classes.json")


def get_items_data() -> dict:
    return load_json("items.json")


def get_monsters_data() -> dict:
    return load_json("monsters.json")


def get_skills_data() -> dict:
    return load_json("skills.json")


def get_dungeons_data() -> dict:
    return load_json("dungeons.json")


def hp_bar(current: int, maximum: int, length: int = 10) -> str:
    ratio = max(0, min(1, current / maximum)) if maximum > 0 else 0
    filled = int(ratio * length)
    empty = length - filled
    return f"{'🟩' * filled}{'⬛' * empty} {current}/{maximum}"


def mp_bar(current: int, maximum: int, length: int = 10) -> str:
    ratio = max(0, min(1, current / maximum)) if maximum > 0 else 0
    filled = int(ratio * length)
    empty = length - filled
    return f"{'🟦' * filled}{'⬛' * empty} {current}/{maximum}"


def profile_embed(char: dict, equipment: dict | None = None) -> discord.Embed:
    classes = get_classes_data()
    cls = classes.get(char["char_class"], {})
    emoji = cls.get("emoji", "⚔️")

    embed = discord.Embed(
        title=f"{emoji} {char['name']}",
        description=f"**Classe:** {cls.get('name', char['char_class'])} | **Nível:** {char['level']}",
        color=discord.Color.gold(),
    )

    from utils.formulas import xp_for_level

    xp_needed = xp_for_level(char["level"])
    embed.add_field(
        name="❤️ HP",
        value=hp_bar(char["hp"], char["max_hp"]),
        inline=True,
    )
    embed.add_field(
        name="💙 MP",
        value=mp_bar(char["mp"], char["max_mp"]),
        inline=True,
    )
    embed.add_field(
        name="⭐ XP",
        value=f"{char['xp']}/{xp_needed}",
        inline=True,
    )
    embed.add_field(
        name="📊 Atributos",
        value=(
            f"⚔️ ATK: **{char['attack']}** | 🛡️ DEF: **{char['defense']}**\n"
            f"🔮 MAG: **{char['magic']}** | 💨 SPD: **{char['speed']}**\n"
            f"🍀 LCK: **{char['luck']}** | 📌 Pontos: **{char['stat_points']}**"
        ),
        inline=False,
    )
    embed.add_field(
        name="💰 Ouro",
        value=f"{char['gold']} G",
        inline=True,
    )
    embed.add_field(
        name="📈 Estatísticas",
        value=f"🗡️ Monstros: {char['monsters_killed']} | 🏰 Dungeons: {char['dungeons_cleared']}",
        inline=True,
    )

    if equipment:
        items = get_items_data()
        equip_lines = []
        for slot in ["weapon", "armor", "shield", "accessory"]:
            item_id = equipment.get(slot)
            if item_id and item_id in items:
                item = items[item_id]
                equip_lines.append(f"{item['emoji']} **{item['name']}**")
            else:
                slot_names = {
                    "weapon": "Arma",
                    "armor": "Armadura",
                    "shield": "Escudo",
                    "accessory": "Acessório",
                }
                equip_lines.append(f"⬜ *{slot_names[slot]}: Vazio*")
        embed.add_field(
            name="🎒 Equipamento",
            value="\n".join(equip_lines),
            inline=False,
        )

    return embed


def combat_embed(
    char: dict,
    monster: dict,
    monster_hp: int,
    monster_max_hp: int,
    turn: int,
    log: str = "",
) -> discord.Embed:
    classes = get_classes_data()
    cls = classes.get(char["char_class"], {})
    embed = discord.Embed(
        title=f"⚔️ Combate — Turno {turn}",
        color=discord.Color.red(),
    )
    embed.add_field(
        name=f"{cls.get('emoji', '⚔️')} {char['name']} (Lv.{char['level']})",
        value=(
            f"HP: {hp_bar(char['hp'], char['max_hp'])}\n"
            f"MP: {mp_bar(char['mp'], char['max_mp'])}"
        ),
        inline=True,
    )
    embed.add_field(
        name=f"{monster.get('emoji', '👾')} {monster['name']} (Lv.{monster.get('level', '?')})",
        value=f"HP: {hp_bar(monster_hp, monster_max_hp)}",
        inline=True,
    )
    if log:
        embed.add_field(name="📜 Log", value=log[-1024:], inline=False)
    return embed
