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
# Elemental Mastery's cooldown (180 s) comes from wago SpellCooldowns, spell 16166, not the rank text.
ELEMENTAL_MASTERY_COOLDOWN = 180.0

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
        EffectRule("dot_seconds", r"duration of your Flame Shock spell by (\d+(?:\.\d+)?) sec", ("Flame Shock",)),
    ),
    "Elemental Alacrity": (
        EffectRule("cast_time", r"cast time of your Lightning Bolt, Chain Lightning, and Lava Burst spells by (\d+(?:\.\d+)?) sec",
                   ("Lightning Bolt", "Chain Lightning", "Lava Burst"), sign=-1),
    ),
    "Eye of the Storm": (
        EffectRule("pushback_pct",
                   r"Reduces the pushback suffered from damaging attacks while casting Lightning Bolt, Chain Lightning, and Lava Burst by (\d+(?:\.\d+)?)%",
                   ("Lightning Bolt", "Chain Lightning", "Lava Burst")),
    ),
    "Elemental Fury": (
        EffectRule("crit_damage_pct", r"your Fire, Frost, and Nature spells by (\d+(?:\.\d+)?)%", ("fire", "frost", "nature")),
    ),
    "Lightning Overload": (
        EffectRule("damage_pct", r"(\d+)% chance to cast a second, similar spell on the same target at no additional cost that causes half damage",
                   ("Lightning Bolt", "Chain Lightning"), combine=lambda m: float(m.group(1)) / 2),
    ),
    # Uptime-weighted cast-time cut (15 s of the 180 s cooldown); Chain Lightning's cooldown removal isn't modeled.
    "Elemental Mastery": (
        EffectRule("cast_time", r"Lava Burst by (\d+(?:\.\d+)?) sec.*Lasts (\d+(?:\.\d+)?) sec",
                   ("Lightning Bolt", "Lava Burst"), sign=-1,
                   combine=lambda m: float(m.group(1)) * float(m.group(2)) / ELEMENTAL_MASTERY_COOLDOWN),
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
    "Ancestral Knowledge": (
        EffectRule("stat_pct", r"Increases your Intellect by (\d+(?:\.\d+)?)%", ("intellect",)),
    ),
    "Reverberation": (
        EffectRule("cooldown", r"cooldown of your Shock spells by (\d+(?:\.\d+)?) sec",
                   ("Earth Shock", "Flame Shock", "Frost Shock"), sign=-1),
    ),
    "Shamanistic Focus": (
        EffectRule("mana_cost_pct", r"Shock and Lightning Shield spells by (\d+(?:\.\d+)?)%",
                   ("Earth Shock", "Flame Shock", "Frost Shock", "Lightning Shield"), sign=-1),
    ),
    # best effort (#384): a 10% chance of a free next damage spell averages to 10% less mana
    "Elemental Focus": (
        EffectRule("mana_cost_pct", r"(\d+(?:\.\d+)?)% chance to enter a Clearcasting state",
                   ("fire", "frost", "nature"), sign=-1),
    ),
    "Mental Quickness": (
        EffectRule("spell_power_from", r"by up to (\d+(?:\.\d+)?)% of your Intellect", ("intellect",)),
    ),
}

# Every shaman talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Elemental
    "Elemental Warding": "defensive: 10% less Fire, Frost, Nature damage",
    "Elemental Devastation": "proc: spell crits raise melee crit",
    "Trial by Fire": "damage: Fire Nova damage and cooldown, longer Magma Totem",
    "Elemental Reach": "utility: longer spell range",
    "Earthbound": "control: Earthbind Totem roots 5 s",
    "Lava Burst": "grants_spell",
    # Enhancement
    "Earth's Grasp": "utility: Stoneclaw health, Earthbind radius",
    "Guardian Totems": "defensive: stronger Stoneskin and Windwall Totems",
    "Improved Ghost Wolf": "mobility: faster Ghost Wolf, usable indoors",
    "Improved Lightning Shield": "damage: +15% Lightning Shield",
    "Anticipation": "defensive: +6% dodge",
    "Toughness": "defensive: +10% Stamina",
    "Stormstrike": "grants_spell",
    "Spirit Weapons": "defensive: parry, less threat",
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
    # Lava Burst's own effect 1 (SpellEffect 408490, 1.60.1.70425): +20% damage with Flame Shock up (#384)
    "dot_bonus": {"Lava Burst": ("Flame Shock", 20.0)},
}
# Enhancement fights in melee on the melee engine (#175); Restoration stays unscored (Q3).
MELEE_TREES = ("Enhancement",)
UNSCORED_TREES = ("Restoration",)
CAVEAT = ("Elemental (#167): Flame Shock kept up, Lava Burst and Chain Lightning on cooldown, Lightning Bolt in "
          "between on the caster engine; Lava Burst gets its +20% while Flame Shock is up. Enhancement (#175): "
          "two-hander swings with Windfury (Classic chance and attack power) and Flurry, Stormstrike and Earth "
          "Shock on cooldown on the melee engine; Stormstrike's bonus counts on the share of Earth Shocks after "
          "one; Maelstrom Weapon, totems and Enhancement's mana aren't modeled. Restoration stays unscored. "
          "Base stats are estimates.")


# --- class engine (#311): this module is the shaman's ClassEngine ------------------------------------


def playstyle(cls, ranks) -> str:
    from wowforever.classes.engines import melee_build

    return "melee" if melee_build(MELEE_TREES, cls, ranks) else "caster"


def _melee_output(stats, spells, cls, ranks, target, *, pack=1):
    from wowforever.classes.shaman_rotation import enhancement_rotation
    from wowforever.melee_scenarios import Output

    r = enhancement_rotation(stats, spells, cls, ranks, target, pack=pack)
    return Output(r.dps, 0.0, r.dps, r.aoe)


def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None, sustained=False):
    from wowforever.classes.engines import hybrid_output

    return hybrid_output("shaman", MELEE_TREES, _melee_output, stats, spells, cls, ranks, target, pack=pack,
                         drink_mana_per_second=drink_mana_per_second, melee=melee)


def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
    from wowforever.classes.engines import hybrid_aoe

    return hybrid_aoe("shaman", MELEE_TREES, output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp,
                      armor=armor)


def _melee_facts(stats, cls, ranks):
    from wowforever.classes.shaman_rotation import enhancement_rotation
    from wowforever.physical import Target

    r = enhancement_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
    return {"kind": "enhancement", "split": {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps,
                                             "spells and procs": r.spell_dps / r.dps}}


def facts(stats, cls, ranks):
    from wowforever.classes.engines import hybrid_facts

    return hybrid_facts("shaman", MELEE_TREES, _melee_facts, ROTATION, stats, cls, ranks)


def sides(stats, spells, cls, ranks):
    from wowforever.classes.engines import one_side

    return one_side("shaman", stats, spells, cls, ranks)
