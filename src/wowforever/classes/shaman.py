"""Shaman-specific knowledge: where the Forever shaman talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #152): the trees and spells load and every talent is
classified; nothing is modeled yet. The shaman is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1082 holds all three shaman trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="shaman",
    trait_tree_id=1082,
    trees=(
        TreeBand(tree_id=1, name="Elemental", min_x=1020),
        TreeBand(tree_id=2, name="Enhancement", min_x=5020),
        TreeBand(tree_id=3, name="Restoration", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)

# Numbers are read from the rank text (#163).
TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    "Convection": (
        EffectRule("mana_cost_pct", r"mana cost of your Shock, Lightning Bolt, Lava Burst, and Chain Lightning spells by (\d+(?:\.\d+)?)%",
                   ("Flame Shock", "Lightning Bolt", "Lava Burst", "Chain Lightning"), sign=-1),
    ),
    "Concussion": (
        EffectRule("damage_pct", r"damage done by your Lightning Bolt, Chain Lightning, and Earth Shock spells by (\d+(?:\.\d+)?)%",
                   ("Lightning Bolt", "Chain Lightning")),
    ),
    "Call of Flame": (
        EffectRule("damage_pct", r"Flame Shock, Fire Nova, and Lava Burst spells by (\d+(?:\.\d+)?)%", ("Flame Shock", "Lava Burst")),
    ),
    "Elemental Alacrity": (
        EffectRule("cast_time", r"cast time of your Lightning Bolt, Chain Lightning, and Lava Burst spells by (\d+(?:\.\d+)?) sec",
                   ("Lightning Bolt", "Chain Lightning", "Lava Burst"), sign=-1),
    ),
    "Call of Thunder": (
        EffectRule("crit_chance", r"critical strike chance of your Lightning Bolt and Chain Lightning spells by (\d+(?:\.\d+)?)%",
                   ("Lightning Bolt", "Chain Lightning")),
    ),
    "Elemental Fury": (
        EffectRule("crit_damage_pct", r"your Fire, Frost, and Nature spells by (\d+(?:\.\d+)?)%", ("fire", "frost", "nature")),
    ),
    "Lightning Overload": (
        EffectRule("damage_pct", r"(\d+)% chance to cast a second, similar spell on the same target at no additional cost that causes half damage",
                   ("Lightning Bolt", "Chain Lightning"), combine=lambda m: float(m.group(1)) / 2),
    ),
    "Thundering Strikes": (
        EffectRule("crit_chance", r"critical strike with all spells and attacks by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Tidal Focus": (
        EffectRule("hit_chance", r"improves your chance to hit by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Mindfulness": (
        EffectRule("regen_while_casting", r"Allows (\d+(?:\.\d+)?)% of your Mana regeneration", ("all",)),
    ),
    # melee hybrid (#175)
    "Flurry": (
        EffectRule("haste_pct", r"attack speed by (\d+(?:\.\d+)?)% for your next 3 swings", ("@flurry",)),
    ),
    "Elemental Weapons": (
        EffectRule("damage_pct", r"your Windfury Weapon effect by (\d+(?:\.\d+)?)%", ("Windfury Weapon",)),
    ),
    "Mental Dexterity": (
        EffectRule("ap_from_int_pct", r"Attack Power by an amount equal to (\d+(?:\.\d+)?)% of your Intellect", ("all",)),
    ),
}

# Every shaman talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Elemental
    "Elemental Warding": "defensive: 10% less Fire, Frost, Nature damage",
    "Reverberation": "damage: Shock cooldown -1 s",
    "Elemental Devastation": "proc: spell crits raise melee crit",
    "Elemental Focus": "proc: Clearcasting after damage spells",
    "Improved Fire Nova": "damage: Fire Nova damage and cooldown",
    "Eye of the Storm": "utility: less pushback on Lightning and Lava Burst",
    "Elemental Reach": "utility: longer spell range",
    "Earthbound": "control: Earthbind Totem roots 5 s",
    "Lava Burst": "grants_spell",
    # Enhancement
    "Earth's Grasp": "utility: Stoneclaw health, Earthbind radius",
    "Ancestral Knowledge": "buff: +10% Intellect",
    "Guardian Totems": "defensive: stronger Stoneskin and Windwall Totems",
    "Improved Ghost Wolf": "mobility: faster Ghost Wolf, usable indoors",
    "Improved Lightning Shield": "damage: +15% Lightning Shield",
    "Shamanistic Focus": "resource: cheaper Shocks and Lightning Shield",
    "Anticipation": "defensive: +6% dodge",
    "Toughness": "defensive: +10% Stamina",
    "Stormstrike": "grants_spell",
    "Spirit Weapons": "defensive: parry, less threat",
    "Mental Quickness": "damage: spell power from Intellect",
    "Improved Stormstrike": "resource: mana regeneration after Stormstrike",
    "Maelstrom Weapon": "proc: melee hits speed up the next spell",
    "Rage of the Farseer": "grants_spell",
    # Restoration
    "Improved Healing Wave": "healing: faster Healing Wave",
    "Totemic Focus": "resource: cheaper totems",
    "Natural Grace": "threat: 15% less spell threat",
    "Improved Reincarnation": "defensive: Reincarnation cooldown, +4% health",
    "Ancestral Healing": "healing: crit heals raise target armor",
    "Healing Focus": "utility: heals resist pushback",
    "Water Shield": "grants_spell",
    "Tidal Mastery": "healing: +5% heal crit",
    "Restorative Totems": "healing: stronger Mana Spring and Healing Stream",
    "Mana Tide Totem": "grants_spell",
    "Healing Way": "healing: +25% Healing Wave",
    "Nature's Swiftness": "grants_spell",
    "Purification": "healing: +10% healing",
    "Riptide": "grants_spell",
}

# Shaman skill lines in SkillLineAbility: Elemental, Enhancement, Restoration.
SKILL_LINES = (375, 373, 374)

# Scored by the caster spell engine (#163).
ENGINE = "spell"
ROTATION = {
    "dots": ("Flame Shock",),
    "cooldowns": ("Lava Burst", "Chain Lightning"),
    "fillers": ("Lightning Bolt",),
}
# Enhancement fights in melee on the melee engine (#175); Restoration stays unscored (Q3).
MELEE_TREES = ("Enhancement",)
UNSCORED_TREES = ("Restoration",)
CAVEAT = ("Elemental (#167): Flame Shock kept up, Lava Burst and Chain Lightning on cooldown, Lightning Bolt in "
          "between on the caster engine. Enhancement (#175): two-hander swings with Windfury (Classic chance and "
          "attack power) and Flurry, Stormstrike and Earth Shock on cooldown on the melee engine; Stormstrike's "
          "debuff, Maelstrom Weapon, totems and Enhancement's mana aren't modeled. Restoration stays unscored. "
          "Base stats are estimates.")
