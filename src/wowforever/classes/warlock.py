"""Warlock-specific knowledge: where the Forever warlock talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #152): the trees and spells load and every talent is
classified; nothing is modeled yet. The warlock is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand, below_health

# Trait tree 1116 holds all three warlock trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="warlock",
    trait_tree_id=1116,
    trees=(
        TreeBand(tree_id=1, name="Affliction", min_x=1020),
        TreeBand(tree_id=2, name="Demonology", min_x=5020),
        TreeBand(tree_id=3, name="Destruction", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
    # Amplify Curse and Improved Life Tap sit 10 units off their grid row.
    snap=20,
)

# Numbers are read from the rank text (#163).
# client SkillLineAbility, skill line 593 (Destruction), its damaging spells; wago 1.60.1.70425, #377
DESTRUCTION_SPELLS = ("Conflagrate", "Hellfire", "Immolate", "Incinerate", "Rain of Fire", "Searing Pain", "Shadow Bolt", "Shadowburn", "Soul Fire")

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    "Suppression": (
        EffectRule("hit_chance", r"Improves your chance to hit by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Improved Corruption": (
        EffectRule("cast_time", r"casting time of your Corruption spell by (\d+(?:\.\d+)?) sec", ("Corruption",), sign=-1),
        EffectRule("damage_pct", r"increases the damage it deals by (\d+(?:\.\d+)?)%", ("Corruption",)),
    ),
    "Improved Bane of Agony": (
        EffectRule("damage_pct", r"damage done by your Bane of Agony by (\d+(?:\.\d+)?)%", ("Bane of Agony",)),
    ),
    "Pandemic": (
        EffectRule("crit_damage_pct", r"critical strike damage bonus of your Corruption, Bane of Agony, Bane of Doom, Drain Soul, Drain Life, Siphon Life, and Wrack spells by (\d+(?:\.\d+)?)%",
                   ("Corruption", "Bane of Agony", "Wrack")),
    ),
    "Malevolence": (
        EffectRule("crit_chance", r"critical effect chance of your Shadow spells by (\d+(?:\.\d+)?)%", ("shadow",)),
    ),
    "Nightfall": (
        EffectRule("instant_proc_pct", r"Wrack spells a (\d+(?:\.\d+)?)% chance to cause you to enter a Shadow Trance",
                   ("Corruption", "Drain Soul", "Drain Life", "Wrack", "@Shadow Bolt")),
    ),
    "Shadow Mastery": (
        EffectRule("damage_pct", r"damage dealt or life drained by your Shadow spells by (\d+(?:\.\d+)?)%", ("shadow",)),
    ),
    "Demonic Sacrifice": (
        EffectRule("damage_pct", r"Imp: Increases your Shadow damage by (\d+(?:\.\d+)?)%", ("shadow",)),
    ),
    "Bane": (
        EffectRule("cast_time", r"casting time of your Shadow Bolt, Immolate, and Incinerate spells by (\d+(?:\.\d+)?) sec",
                   ("Shadow Bolt", "Immolate", "Incinerate"), sign=-1),
    ),
    "Cataclysm": (
        EffectRule("mana_cost_pct", r"Mana cost of your Destruction spells by (\d+(?:\.\d+)?)%", DESTRUCTION_SPELLS, sign=-1),
    ),
    "Ruin": (
        EffectRule("crit_damage_pct", r"critical strike damage bonus of your Destruction spells by (\d+(?:\.\d+)?)%", DESTRUCTION_SPELLS),
    ),
    "Intensity": (
        EffectRule("pushback_pct", r"Gives you a (\d+(?:\.\d+)?)% chance to resist interruption", ("destruction",)),
    ),
    "Agonizing Flames": (
        EffectRule("damage_pct", r"damage done by all your Destruction spells by (\d+(?:\.\d+)?)%", DESTRUCTION_SPELLS),
    ),
    "Fire and Brimstone": (
        EffectRule("crit_chance", r"critical strike chance of your Conflagrate spell by (\d+(?:\.\d+)?)%", ("Conflagrate",)),
    ),
    "Shadow and Flame": (
        EffectRule("damage_pct", r"Conflagrate increases all Shadow damage you deal by (\d+(?:\.\d+)?)%", ("shadow",)),
        EffectRule("damage_pct", r"Shadowburn increases all Fire damage you deal by (\d+(?:\.\d+)?)%", ("fire",)),
        EffectRule("proc_chance", r"Conflagrate has a (\d+(?:\.\d+)?)% chance not to consume Immolate",
                   ("@keep_Immolate",)),
    ),
    "Fel Vitality": (
        EffectRule("stat_pct", r"increases your maximum Mana by (\d+(?:\.\d+)?)%", ("mana",)),
    ),
    "Improved Drains": (
        EffectRule("damage_pct", r"Drain Life, Drain Soul, and Wrack spells by (\d+(?:\.\d+)?)%",
                   ("Drain Life", "Drain Soul", "Wrack")),
    ),
    # the model's warlock keeps a demon out (#396)
    "Demonic Knowledge": (
        EffectRule("spell_power_from", r"by up to (\d+(?:\.\d+)?)% of your level", ("level",)),
    ),
    "Improved Life Tap": (
        EffectRule("life_tap_pct", r"Mana awarded by your Life Tap spell by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    # the Shadow Bolt and Searing Pain part; Soul Fire isn't in the rotation (#396)
    "Decimation": (
        EffectRule("damage_pct", r"enemy below (\d+(?:\.\d+)?)% health, they deal (\d+(?:\.\d+)?)% increased damage",
                   ("Shadow Bolt", "Searing Pain"), combine=below_health),
    ),
    "Improved Shadow Bolt": (
        EffectRule("crit_debuff_pct", r"Shadow damage taken by the target from your attacks by (\d+(?:\.\d+)?)%",
                   ("Shadow Bolt", "shadow")),
        EffectRule("crit_debuff_seconds", r"from your attacks by \d+(?:\.\d+)?% for (\d+(?:\.\d+)?) sec",
                   ("Shadow Bolt", "shadow")),
    ),
    # one rule per Affliction DoT, each counting while that DoT is up (#396)
    "Soul Siphon": tuple(
        EffectRule("damage_pct", r"Wrack spells by (\d+(?:\.\d+)?)% per each of your other Affliction effects",
                   ("Drain Life", "Drain Soul", "Wrack", f"@dot:{dot}"))
        for dot in ("Corruption", "Bane of Agony", "Siphon Life")),
}

# Every warlock talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Affliction
    "Soul Harvest": "resource: mana regeneration after Drain Soul kills",
    "Fel Concentration": "utility: drains resist pushback",
    "Amplify Curse": "control: stronger next curse",
    "Curse of Exhaustion": "grants_spell",
    "Siphon Life": "grants_spell",
    "Wrack": "grants_spell",
    "Grim Reach": "utility: range of Affliction spells (1.60.1.70425)",
    # Demonology
    "Improved Health Funnel": "pet: stronger Health Funnel",
    "Improved Imp": "pet: stronger Imp",
    "Demonic Embrace": "defensive: +15% Stamina",
    "Unholy Power": "pet: +10% pet damage",
    "Demonic Aegis": "defensive: stronger Demon Skin and Demon Armor",
    "Improved Voidwalker": "pet: stronger Voidwalker",
    "Demonic Energies": "pet: heal pet from spell damage",
    "Improved Sayaad": "pet: stronger Succubus and Incubus",
    "Master Summoner": "pet: faster pet summons",
    "Fel Domination": "grants_spell",
    "Demonic Brand": "pet: pet bonus vs branded targets",
    "Improved Felhunter": "pet: stronger Felhunter",
    "Soul Link": "grants_spell",
    "Master Demonologist": "pet: bonus per active demon",
    "Demonic Pact": "pet: Demonic Sacrifice persists",
    # Destruction
    "Destructive Reach": "utility: +20% spell range",
    "Molten Skin": "defensive: 10% less damage taken",
    "Aftermath": "control: Conflagrate dazes, stronger Immolate",
    "Shadowburn": "grants_spell",
    "Conflagrate": "grants_spell",
    "Pyroclasm": "control: Soul Fire and AoE can stun",
    "Bane of Havoc": "grants_spell",
    "Incinerate": "grants_spell",
}

# Warlock skill lines in SkillLineAbility: Affliction, Demonology, Destruction.
SKILL_LINES = (355, 354, 593)

# Scored by the caster spell engine (#163).
ENGINE = "spell"
ROTATION = {
    "dots": ("Corruption", "Bane of Agony", "Siphon Life", "Immolate"),
    "cooldowns": ("Conflagrate", "Shadowburn"),
    "fillers": ("Shadow Bolt", "Incinerate", "Searing Pain", "Wrack", "Drain Life"),
    "consumes": {"Conflagrate": "Immolate"},
}
CAVEAT = ("Caster model (#163, #165): Corruption, Bane of Agony, Siphon Life and Immolate kept up, Conflagrate "
          "and Shadowburn on cooldown, then the best of Shadow Bolt, Incinerate, Searing Pain, Wrack or Drain "
          "Life, with Life Tap as steady mana. Improved Shadow Bolt and Nightfall count as averages and Soul "
          "Siphon counts the DoTs kept up; pets aren't modeled; Demonic Sacrifice counts the Imp (+Shadow) and "
          "Demonic Knowledge assumes a demon is out. Base stats are estimates.")


# --- class engine (#311): this module is the warlock's ClassEngine ------------------------------------


def playstyle(cls, ranks) -> str:
    return "caster"


def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None, sustained=False):
    from wowforever.classes.engines import caster_output

    return caster_output("warlock", stats, spells, cls, ranks, target, drink_mana_per_second=drink_mana_per_second)


def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
    from wowforever.classes.engines import caster_aoe

    return caster_aoe("warlock", stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp)


def facts(stats, cls, ranks):
    from wowforever.classes.engines import caster_facts

    return caster_facts("warlock", ROTATION, stats, cls, ranks)


def sides(stats, spells, cls, ranks):
    from wowforever.classes.engines import one_side

    return one_side("warlock", stats, spells, cls, ranks)
