"""Druid-specific knowledge: where the Forever druid talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #152): the trees and spells load and every talent is
classified; nothing is modeled yet. The druid is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1089 holds all three druid trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="druid",
    trait_tree_id=1089,
    trees=(
        TreeBand(tree_id=1, name="Balance", min_x=1020),
        TreeBand(tree_id=2, name="Feral Combat", min_x=5020),
        TreeBand(tree_id=3, name="Restoration", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)

# Numbers are read from the rank text (#163).
TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    "Improved Wrath": (
        EffectRule("cast_time", r"cast time of your Wrath spell by (\d+(?:\.\d+)?) sec", ("Wrath",), sign=-1),
        EffectRule("mana_cost_pct", r"its Mana cost by (\d+(?:\.\d+)?)%", ("Wrath",), sign=-1),
    ),
    "Genesis": (
        EffectRule("damage_pct", r"periodic damage and healing done by your spells and abilities by (\d+(?:\.\d+)?)%",
                   ("Moonfire", "Insect Swarm")),
        EffectRule("healing_pct", r"periodic damage and healing done by your spells and abilities by (\d+(?:\.\d+)?)%",
                   ("periodic",)),
    ),
    "Moonglow": (
        EffectRule("mana_cost_pct", r"Mana cost of your damaging spells by (\d+(?:\.\d+)?)%", ("arcane", "nature"), sign=-1),
    ),
    "Improved Moonfire": (
        EffectRule("damage_pct", r"damage and critical strike chance of your Moonfire spell by (\d+(?:\.\d+)?)%", ("Moonfire",)),
        EffectRule("crit_chance", r"damage and critical strike chance of your Moonfire spell by (\d+(?:\.\d+)?)%", ("Moonfire",)),
    ),
    "Nature's Majesty": (
        EffectRule("crit_chance", r"critical strike chance with spells and melee attacks by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Nature's Reach": (
        EffectRule("hit_chance", r"improves your chance to hit by (\d+(?:\.\d+)?)%", ("arcane", "nature")),
    ),
    "Vengeance": (
        EffectRule("crit_damage_pct", r"critical strike damage bonus of your Arcane and Nature spells by (\d+(?:\.\d+)?)%",
                   ("arcane", "nature")),
    ),
    "Improved Starfire": (
        EffectRule("cast_time", r"cast time of Starfire by (\d+(?:\.\d+)?) sec", ("Starfire",), sign=-1),
    ),
    "Eclipse": (
        EffectRule("cast_time", r"cast time of your next 2 Starfire spells by (\d+(?:\.\d+)?) sec",
                   ("Starfire", "@eclipse"), sign=-1),
    ),
    "Nature's Grace": (
        EffectRule("crit_haste_pct", r"reducing your global cooldown by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Moonfury": (
        EffectRule("damage_pct", r"damage done by your Arcane and Nature spells by (\d+(?:\.\d+)?)%", ("arcane", "nature")),
    ),
    "Moonkin Form": (
        EffectRule("crit_chance", r"Critical Strike chance increased by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Nature's Focus": (
        EffectRule("pushback_pct", r"Gives you a (\d+(?:\.\d+)?)% chance to avoid interruption", ("arcane", "nature")),
    ),
    "Naturalist": (
        EffectRule("cast_time", r"cast time of your Healing Touch spell by (\d+(?:\.\d+)?) sec", ("Healing Touch",), sign=-1),
        EffectRule("damage_pct", r"increases all damage you deal by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Reflection": (
        EffectRule("regen_while_casting", r"Allows (\d+(?:\.\d+)?)% of your Mana regeneration", ("all",)),
    ),
    # self-healing (#276)
    "Gift of Nature": (
        EffectRule("healing_pct", r"effect of all your healing spells by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Tranquil Spirit": (
        EffectRule("mana_cost_pct", r"mana cost of your Healing Touch and Tranquility spells by (\d+(?:\.\d+)?)%",
                   ("Healing Touch", "Tranquility"), sign=-1),
    ),
    "Improved Rejuvenation": (
        EffectRule("healing_pct", r"effect of your Rejuvenation spell by (\d+(?:\.\d+)?)%", ("Rejuvenation",)),
    ),
    # HoT durations only; longer Moonfire and Insect Swarm aren't modeled
    "Nature's Splendor": (
        EffectRule("duration", r"Moonfire and Rejuvenation spells by (\d+(?:\.\d+)?) sec", ("Rejuvenation",)),
        EffectRule("duration", r"your Regrowth spell by (\d+(?:\.\d+)?) sec", ("Regrowth",)),
    ),
    "Gift of the Earthmother": (
        EffectRule("gcd", r"global cooldown by (\d+(?:\.\d+)?) seconds", ("Rejuvenation", "Swiftmend", "Wild Growth"), sign=-1),
    ),
    "Improved Regrowth": (
        EffectRule("crit_chance", r"critical effect chance of your Regrowth spell by (\d+(?:\.\d+)?)%", ("Regrowth",)),
    ),
    "Improved Entangling Roots": (
        EffectRule("break_threshold_pct", r"can take up to (\d+)% more damage without interrupting", ("Entangling Roots",)),
    ),
    "Overgrowth": (
        EffectRule("targets", r"affected by Entangling Roots by (\d+)", ("Entangling Roots",)),
    ),
    # melee hybrid (#175)
    "Ferocity": (
        EffectRule("energy_cost", r"cost of your Maul, Primal Bite, Swipe, Claw, and Rake abilities by (\d+(?:\.\d+)?) Rage or Energy",
                   ("Claw", "Rake", "Maul", "Swipe", "Primal Bite"), sign=-1),
    ),
    "Shredding Attacks": (
        EffectRule("energy_cost", r"Energy cost of your Shred ability by (\d+(?:\.\d+)?)", ("Shred",), sign=-1),
    ),
    "Savage Fury": (
        EffectRule("damage_pct", r"damage caused by your Claw, Rake, Shred, Maul, and Swipe abilities by (\d+(?:\.\d+)?)%",
                   ("Claw", "Rake", "Shred", "Maul", "Swipe")),
    ),
    "Sharpened Claws": (
        EffectRule("crit_chance", r"critical strike chance while in Bear Form, Dire Bear Form, or Cat Form by (\d+(?:\.\d+)?)%", ("@feral",)),
    ),
    "Predatory Strikes": (
        EffectRule("ap_per_level_pct", r"Attack Power in Cat Form, Bear Form, and Dire Bear Form by (\d+(?:\.\d+)?)% of your level", ("all",)),
    ),
    "Leader of the Pack": (
        EffectRule("crit_chance", r"within 45 yards by (\d+(?:\.\d+)?)%", ("@feral",)),
    ),
    "Natural Instinct": (                    # "Predatory Instincts" before the Oct 8 patch
        EffectRule("crit_damage_pct", r"critical strike damage bonus of your melee abilities by (\d+(?:\.\d+)?)%", ("@ability",)),
    ),
    "Rend and Tear": (
        EffectRule("damage_pct", r"damage done by your melee abilities on Bleeding targets by (\d+(?:\.\d+)?)%", ("@bleeding",)),
    ),
    "Heart of the Wild": (
        EffectRule("stat_pct", r"Increases your Intellect by (\d+(?:\.\d+)?)%", ("intellect",)),
        EffectRule("stat_pct", r"Cat Form your Strength is increased by (\d+(?:\.\d+)?)%", ("strength",)),
    ),
    "Living Spirit": (
        EffectRule("stat_pct", r"Increases your Spirit by (\d+(?:\.\d+)?)%", ("spirit",)),
    ),
    "Blood Frenzy": (
        # the Cat Form part (#397); the Bear Form Rage part stays out (bear isn't scored)
        EffectRule("proc_chance", r"Combo Points have a (\d+(?:\.\d+)?)% chance to add an additional Combo Point",
                   ("@builder_crit",)),
    ),
}

# Every druid talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Balance
    "Insect Swarm": "grants_spell",
    # Feral Combat
    "Feral Swiftness": "mobility: Cat Form speed and dodge",
    "Feral Instinct": "damage: Swipe damage, stealthier Prowl",
    "Brutal Impact": "control: longer Bash and Pounce stuns",
    "Thick Hide": "defensive: more armor in forms",
    "Feral Charge": "grants_spell",
    "Shifting Power": "grants_spell",
    "Primal Bite": "grants_spell",
    "Improved Shifting Power": "resource: Shifting Power cooldown -8 s",
    "Natural Reaction": "defensive: +5% dodge, Rage on dodge",
    "Berserk": "damage: builder crit averaged in druid_rotation (#397); Primal Bite's cleave not modeled",
    # Restoration
    "Furor": "resource: Rage or Energy on shapeshift",
    "Subtlety": "threat: less threat from Nature and Arcane spells",
    "Natural Shapeshifter": "resource: cheaper shapeshifting",
    "Swiftmend": "grants_spell",
    "Nature's Swiftness": "grants_spell",
    "Improved Tranquility": "healing: Tranquility cooldown and threat",
    "Wild Growth": "grants_spell",
}

# Druid skill lines in SkillLineAbility: Balance, Feral Combat, Restoration.
SKILL_LINES = (574, 134, 573)

# Scored by the caster spell engine (#163).
ENGINE = "spell"
ROTATION = {
    "dots": ("Moonfire", "Insect Swarm"),
    "cooldowns": (),
    "fillers": ("Starfire", "Wrath"),
    # one Wrath, then two Starfires with Eclipse's cut (#397)
    "filler_mix": ("Wrath", "Starfire", 2, "eclipse"),
}
# Feral builds fight in cat form on the melee engine (#175); the bear tank and Restoration stay
# unscored (Q3).
MELEE_TREES = ("Feral Combat",)
UNSCORED_TREES = ("Restoration",)
UNSCORED_BUILDS = ("druid-feral-bear",)
CAVEAT = ("Balance (#166): Moonfire and Insect Swarm kept up, then Starfire or Wrath on the caster engine; "
          "Nature's Grace counts as an average haste from crits; Eclipse weighs a Wrath-then-two-Starfires "
          "filler; Omen of Clarity isn't modeled. Feral cat (#175): paw swings and a Shred or Claw to Ferocious "
          "Bite energy cycle on the melee engine, Classic paw damage; Rake and Rip bleeds, Tiger's Fury and "
          "powershifting aren't modeled. The bear tank and Restoration stay unscored. Base stats are estimates.")


# --- class engine (#311): this module is the druid's ClassEngine ------------------------------------


def playstyle(cls, ranks) -> str:
    from wowforever.classes.engines import melee_build

    return "melee" if melee_build(MELEE_TREES, cls, ranks) else "caster"


def _melee_output(stats, spells, cls, ranks, target, *, pack=1):
    # a cat stays single target (#262)
    from wowforever.classes.druid_rotation import cat_rotation
    from wowforever.melee_scenarios import Output

    r = cat_rotation(stats, spells, cls, ranks, target)
    return Output(r.dps, 0.0, r.dps)


def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None, sustained=False):
    from wowforever.classes.engines import hybrid_output

    return hybrid_output("druid", MELEE_TREES, _melee_output, stats, spells, cls, ranks, target, pack=pack,
                         drink_mana_per_second=drink_mana_per_second, melee=melee)


def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
    from wowforever.classes.engines import hybrid_aoe

    return hybrid_aoe("druid", MELEE_TREES, output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp,
                      armor=armor)


def _melee_facts(stats, cls, ranks):
    from wowforever.classes.druid_rotation import cat_rotation
    from wowforever.physical import Target

    r = cat_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
    return {"kind": "cat", "builder": r.builder,
            "split": {"auto-attacks": r.white_dps / r.dps, "abilities": r.yellow_dps / r.dps}}


def facts(stats, cls, ranks):
    from wowforever.classes.engines import hybrid_facts

    return hybrid_facts("druid", MELEE_TREES, _melee_facts, ROTATION, stats, cls, ranks)


def sides(stats, spells, cls, ranks):
    from wowforever.classes.engines import one_side

    return one_side("druid", stats, spells, cls, ranks)
