"""Rogue-specific knowledge: where the Forever rogue talent trees live in the client's trait data.

Stage 2 of the alts (#131 part 2): the damage talents carry effect rules read from the rank
text; the rest stay classified but unmodeled until the alts-engine milestone (#111).
"""

from dataclasses import replace
from pathlib import Path

from wowforever.classes import EffectRule, TraitLayout, TreeBand, below_health

# Trait tree 1111 holds all three rogue trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="rogue",
    trait_tree_id=1111,
    trees=(
        TreeBand(tree_id=1, name="Assassination", min_x=1020),
        TreeBand(tree_id=2, name="Combat", min_x=5020),
        TreeBand(tree_id=3, name="Subtlety", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)

# Numbers are taken from the rank text with each rule's pattern, never hard-coded;
# `sign` flips reductions. UNMODELED explains every talent not in TALENT_EFFECTS.
TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    # Assassination
    "Malice": (
        EffectRule("crit_chance",
                   r"critical strike chance with all attacks and Poisons by (\d+(?:\.\d+)?)%",
                   ("all",)),
    ),
    "Ruthlessness": (
        EffectRule("proc_chance", r"a (\d+(?:\.\d+)?)% chance to add a Combo Point",
                   ("@finisher",)),
    ),
    "Murder": (
        EffectRule("damage_pct", r"damage dealt by (\d+(?:\.\d+)?)%", ("@humanoid",)),
    ),
    "Improved Slice and Dice": (
        EffectRule("duration",
                   r"duration of your Slice and Dice ability by (\d+(?:\.\d+)?)%",
                   ("Slice and Dice",)),
    ),
    "Relentless Strikes": (
        EffectRule("resource", r"have a (\d+(?:\.\d+)?)% chance per Combo Point", ("@finisher",)),
    ),
    "Lethality": (
        EffectRule("crit_damage_pct",
                   r"critical strike damage bonus of your .* by (\d+(?:\.\d+)?)%",
                   ("Sinister Strike", "Gouge", "Backstab", "Mutilate", "Ghostly Strike",
                    "Hemorrhage")),
    ),
    "Vile Poisons": (
        EffectRule("damage_pct", r"damage dealt by your poisons by (\d+(?:\.\d+)?)%",
                   ("@poison",)),
    ),
    "Improved Poisons": (
        EffectRule("proc_chance", r"chance to apply Poisons to your target by (\d+(?:\.\d+)?)%",
                   ("@poison",)),
    ),
    "Seal Fate": (
        EffectRule("proc_chance",
                   r"a (\d+(?:\.\d+)?)% chance to add an additional Combo Point",
                   ("@builder_crit",)),
    ),
    # Combat
    "Improved Eviscerate": (
        EffectRule("damage_pct", r"Eviscerate ability by (\d+(?:\.\d+)?)%", ("Eviscerate",)),
    ),
    "Flawless Execution": (
        EffectRule("energy_cost", r"Energy cost of your Eviscerate ability by (\d+(?:\.\d+)?)",
                   ("Eviscerate",), sign=-1),
    ),
    "Improved Sinister Strike": (
        EffectRule("energy_cost",
                   r"Energy cost of your Sinister Strike ability by (\d+(?:\.\d+)?)",
                   ("Sinister Strike",), sign=-1),
    ),
    "Puncturing Wounds": (
        EffectRule("crit_chance",
                   r"critical strike chance of your Backstab by (\d+(?:\.\d+)?)%",
                   ("Backstab",)),
        EffectRule("crit_chance", r"Mutilate by (\d+(?:\.\d+)?)%", ("Mutilate",)),
        EffectRule("proc_chance", r"gives Backstab a (\d+(?:\.\d+)?)% chance",
                   ("@backstab_combo",)),
    ),
    "Precision": (
        EffectRule("hit_chance", r"chance to hit by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Dual Wield Specialization": (
        EffectRule("damage_pct", r"off-hand weapon by (\d+(?:\.\d+)?)%", ("@off_hand",)),
    ),
    "Weapon Expertise": (
        EffectRule("dodge_reduction", r"Dodged or Parried by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Aggression": (
        EffectRule("damage_pct", r"damage of your .* abilities by (\d+(?:\.\d+)?)%",
                   ("Sinister Strike", "Backstab", "Eviscerate")),
    ),
    # Subtlety
    "Opportunity": (
        EffectRule("damage_pct", r"damage dealt by your .* abilities by (\d+(?:\.\d+)?)%",
                   ("Backstab", "Garrote", "Ambush", "Mutilate")),
    ),
    "Improved Ambush": (
        EffectRule("crit_chance", r"Ambush ability by (\d+(?:\.\d+)?)%", ("Ambush",)),
    ),
    "Serrated Blades": (
        EffectRule("armor_pen", r"ignore (\d+(?:\.\d+)?)% of your target's Armor", ("all",)),
    ),
    "Quietus": (
        EffectRule("damage_pct",
                   r"abilities cause (\d+(?:\.\d+)?)% more damage against targets below (\d+(?:\.\d+)?)% health",
                   ("Sinister Strike", "Ghostly Strike", "Hemorrhage"), combine=below_health),
    ),
}

# Every rogue talent, with why it is not modeled yet. "grants_spell" marks talents that teach an
# activated ability; the rest get "<category>: <what it does>".
UNMODELED: dict[str, str] = {
    # Assassination
    "Improved Gouge": "control: longer Gouge duration",
    "Remorseless Attacks": "melee damage: post-kill crit buff on core abilities (#111)",
    "Improved Expose Armor": "resource: cheaper Expose Armor, refunds Combo Points",
    "Cold Blood": "grants_spell",
    "Vigor": "resource: +10 maximum Energy; no effect on a steady-state Energy cycle (#392)",
    "Mutilate": "grants_spell",
    "Improved Kidney Shot": "control: more damage to Kidney Shot stuns",
    "Venom": "grants_spell",
    # Combat
    "Lightning Reflexes": "defensive: +5% Dodge chance",
    "Deflection": "defensive: +6% Parry chance",
    "Endurance": "utility: shorter Sprint and Evasion cooldowns",
    "Riposte": "grants_spell",
    "Improved Sprint": "mobility: Sprint cleanses movement impairments",
    "Improved Kick": "control: Kick silences the target",
    "Blade Flurry": "grants_spell",
    "Hack and Slash": "proc: weapon-type bonus, best branch per scenario (weapon_talents.py, #386)",
    "Adrenaline Rush": "grants_spell",
    # Subtlety
    "Camouflage": "stealth: faster Stealth, shorter cooldown",
    "Master of Deception": "stealth: harder to detect while Stealthed",
    "Setup": "resource: Combo Point after dodges or resisted spells",
    "Elusiveness": "utility: shorter Vanish and Blind cooldowns",
    "Dirty Tricks": "resource: cheaper Sap and Blind",
    "Initiative": "resource: extra Combo Point from Ambush/Garrote/Cheap Shot",
    "Ghostly Strike": "grants_spell",
    "Improved Distract": "utility: larger Distract radius, less detection of distracted enemies",
    "Heightened Senses": "stealth: better Stealth detection, less hit by spells and ranged",
    "Premeditation": "grants_spell",
    "Dirty Deeds": "stealth: cheaper openers, Garrote works from the front",
    "Preparation": "grants_spell",
    "Hemorrhage": "grants_spell",
    "Cutthroat": "stealth: Backstab can enable Ambush without Stealth",
    "Thousand Cuts": "resource: Rupture ticks cut Hemorrhage/Backstab cost; Rupture loses to Eviscerate, so 0 (#392)",
}

# Two-tree builds the community actually plays (#104): Subtlety Preparation is 16/12/23.
HYBRIDS = ("Assassination/Subtlety",)

# Scored by the melee/ranged engine (#111): report_from_dataset builds a melee_report.
ENGINE = "melee"

# Rogue skill lines in SkillLineAbility: Assassination, Combat, Subtlety, Poisons.
SKILL_LINES = (253, 38, 39, 40)

# Poison damage spells (#387), not on a skill line: each rank's proc spell, by learn level.
EXTRA_SPELLS = {
    8680: "Instant Poison", 8685: "Instant Poison", 8689: "Instant Poison", 11335: "Instant Poison",
    11336: "Instant Poison", 11337: "Instant Poison",
    2818: "Deadly Poison", 2819: "Deadly Poison", 11353: "Deadly Poison", 11354: "Deadly Poison",
    25349: "Deadly Poison",
}


CONFIG = Path(__file__).resolve().parents[3] / "config" / "rogue.toml"


def dagger(stats):
    """`stats` with a dagger in the main hand (#392): the same weapon DPS at config/rogue.toml's `dagger_speed`."""
    from wowforever.toml_cache import load_toml

    mn, mx, speed = stats.main_hand
    f = load_toml(CONFIG)["dagger_speed"] / speed
    return replace(stats, main_hand=(mn * f, mx * f, speed * f))


# --- class engine (#309): this module is the rogue's ClassEngine ------------------------------------


def playstyle(cls, ranks) -> str:
    return "melee"


def output(stats, spells, cls, ranks, target, *, pack=1, drink_mana_per_second=None, melee=None, sustained=False):
    from wowforever.classes.rogue_rotation import rogue_rotation
    from wowforever.melee_scenarios import Output
    from wowforever.scenarios import best_rank
    from wowforever.weapon_talents import best_weapon

    # the usual weapon, or a dagger and Backstab: whichever scores higher (#386, #392)
    r, _ = best_weapon(lambda s, t: rogue_rotation(s, spells, cls, ranks, t, pack=pack),
                       stats, target, cls, ranks)
    if stats.main_hand is not None and best_rank(spells, "Backstab", stats.level) is not None:
        stab, _ = best_weapon(lambda s, t: rogue_rotation(s, spells, cls, ranks, t, pack=pack, backstab=True),
                              dagger(stats), target, cls, ranks, only="dagger")
        r = max(r, stab, key=lambda x: x.dps)
    return Output(r.dps, 0.0, r.dps, r.aoe)


def aoe(stats, spells, cls, ranks, *, pack, mob_hp, armor):
    from wowforever.classes.engines import pack_aoe

    return pack_aoe(output, stats, spells, cls, ranks, pack=pack, mob_hp=mob_hp, armor=armor)


def facts(stats, cls, ranks):
    from wowforever.classes.rogue_rotation import rogue_rotation
    from wowforever.physical import Target

    r = rogue_rotation(stats, cls.spells, cls, ranks, Target(0, 0))
    return {"kind": "rogue", "builder": r.builder,
            "split": {"auto-attacks": r.white_dps / r.dps, "abilities and poisons": r.yellow_dps / r.dps}}


def sides(stats, spells, cls, ranks):
    from wowforever.classes.engines import one_side

    return one_side("rogue", stats, spells, cls, ranks)
