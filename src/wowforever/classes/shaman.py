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

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every shaman talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Elemental
    "Convection": "resource: cheaper Shocks and Lightning",
    "Concussion": "damage: +5% Lightning Bolt, Chain Lightning, Earth Shock",
    "Elemental Warding": "defensive: 10% less Fire, Frost, Nature damage",
    "Reverberation": "damage: Shock cooldown -1 s",
    "Call of Flame": "damage: +15% fire totems, Flame Shock, Fire Nova, Lava Burst",
    "Elemental Devastation": "proc: spell crits raise melee crit",
    "Elemental Focus": "proc: Clearcasting after damage spells",
    "Elemental Alacrity": "damage: faster Lightning Bolt, Chain Lightning, Lava Burst",
    "Improved Fire Nova": "damage: Fire Nova damage and cooldown",
    "Eye of the Storm": "utility: less pushback on Lightning and Lava Burst",
    "Call of Thunder": "damage: +3% Lightning crit",
    "Elemental Reach": "utility: longer spell range",
    "Lightning Overload": "proc: Lightning spells can cast twice",
    "Earthbound": "control: Earthbind Totem roots 5 s",
    "Elemental Fury": "damage: spell and fire totem crit damage",
    "Lava Burst": "grants_spell",
    # Enhancement
    "Earth's Grasp": "utility: Stoneclaw health, Earthbind radius",
    "Thundering Strikes": "damage: +5% spell and melee crit",
    "Ancestral Knowledge": "buff: +10% Intellect",
    "Guardian Totems": "defensive: stronger Stoneskin and Windwall Totems",
    "Mental Dexterity": "damage: attack power from Intellect",
    "Improved Ghost Wolf": "mobility: faster Ghost Wolf, usable indoors",
    "Improved Lightning Shield": "damage: +15% Lightning Shield",
    "Elemental Weapons": "damage: stronger weapon imbues",
    "Shamanistic Focus": "resource: cheaper Shocks and Lightning Shield",
    "Anticipation": "defensive: +6% dodge",
    "Toughness": "defensive: +10% Stamina",
    "Flurry": "damage: attack speed after melee crits",
    "Stormstrike": "grants_spell",
    "Spirit Weapons": "defensive: parry, less threat",
    "Mental Quickness": "damage: spell power from Intellect",
    "Improved Stormstrike": "resource: mana regeneration after Stormstrike",
    "Maelstrom Weapon": "proc: melee hits speed up the next spell",
    "Rage of the Farseer": "grants_spell",
    # Restoration
    "Improved Healing Wave": "healing: faster Healing Wave",
    "Totemic Focus": "resource: cheaper totems",
    "Mindfulness": "resource: 50% mana regeneration while casting",
    "Natural Grace": "threat: 15% less spell threat",
    "Tidal Focus": "resource: cheaper heals, +5% hit",
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
