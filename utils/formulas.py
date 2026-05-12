import random
from config import XP_BASE, XP_GROWTH

ELEMENT_CHART = {
    "fogo": {"strong": "gelo", "weak": "agua"},
    "gelo": {"strong": "raio", "weak": "fogo"},
    "raio": {"strong": "agua", "weak": "terra"},
    "agua": {"strong": "fogo", "weak": "raio"},
    "terra": {"strong": "raio", "weak": "gelo"},
    "luz": {"strong": "trevas", "weak": "none"},
    "trevas": {"strong": "none", "weak": "luz"},
    "none": {"strong": "none", "weak": "none"},
}


def xp_for_level(level: int) -> int:
    return int(XP_BASE * (level ** XP_GROWTH))


def calculate_damage(
    attacker_stat: int,
    defender_defense: int,
    multiplier: float = 1.0,
    element: str = "none",
    defender_element: str = "none",
    armor_pierce: float = 0.0,
    crit_bonus: float = 0.0,
    luck: int = 0,
) -> tuple[int, bool]:
    effective_defense = int(defender_defense * (1 - armor_pierce))
    base_damage = max(1, int(attacker_stat * multiplier - effective_defense * 0.5))

    element_mult = get_element_multiplier(element, defender_element)
    base_damage = int(base_damage * element_mult)

    crit_chance = min(0.5, 0.05 + (luck / 200) + crit_bonus)
    is_crit = random.random() < crit_chance
    if is_crit:
        base_damage = int(base_damage * 1.5)

    variance = random.uniform(0.9, 1.1)
    final_damage = max(1, int(base_damage * variance))
    return final_damage, is_crit


def get_element_multiplier(attack_element: str, defender_element: str) -> float:
    if attack_element == "none" or defender_element == "none":
        return 1.0
    info = ELEMENT_CHART.get(attack_element, {"strong": "none", "weak": "none"})
    if info["strong"] == defender_element:
        return 1.5
    if info["weak"] == defender_element:
        return 0.7
    return 1.0


def get_element_text(attack_element: str, defender_element: str) -> str:
    if attack_element == "none" or defender_element == "none":
        return ""
    info = ELEMENT_CHART.get(attack_element, {"strong": "none", "weak": "none"})
    if info["strong"] == defender_element:
        return " 💥 **Super efetivo!**"
    if info["weak"] == defender_element:
        return " 🛡️ *Pouco efetivo...*"
    return ""


def scale_monster(base_stats: dict, player_level: int, level_range: list[int]) -> dict:
    min_lvl, max_lvl = level_range
    monster_level = min(max_lvl, max(min_lvl, player_level))
    scale = 1 + (monster_level - min_lvl) * 0.12
    scaled = {}
    for stat, value in base_stats.items():
        scaled[stat] = int(value * scale)
    scaled["level"] = monster_level
    return scaled
