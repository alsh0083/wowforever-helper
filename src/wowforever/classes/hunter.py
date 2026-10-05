"""Hunter-specific knowledge: where the Forever hunter talent trees live in the client's trait data.

Stage 1 of the alts (#107): the trees and spells load, and every talent is classified. Ranged,
melee and pet damage are not modeled until the alts-engine milestone (#111). Pet abilities
(skill line 261) stay out of the spell list until then.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1091 holds all three hunter trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="hunter",
    trait_tree_id=1091,
    trees=(
        TreeBand(tree_id=1, name="Beast Mastery", min_x=1020),
        TreeBand(tree_id=2, name="Marksmanship", min_x=5020),
        TreeBand(tree_id=3, name="Survival", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
    # Classic nodes Forever parked off the grid (build 1.60.1.70205, #107): Lightning Reflexes
    # 104982 at (102800, 5740), replaced by node 110859 at Survival row 5, column 2; Improved
    # Serpent Sting 105003 at (6820, 39300), not on wowforevertalent.com (Improved Stings took over).
    hidden_nodes=frozenset({104982, 105003}),
)

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    "Lethal Attacks": (
        EffectRule("crit_chance", r"critical strike chance with all attacks by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Careful Aim": (
        EffectRule("ap_from_int_pct", r"Attack Power by (\d+(?:\.\d+)?)% of your Intellect", ("all",)),
    ),
    "Mortal Shots": (
        EffectRule("crit_damage_pct", r"critical strike damage bonus on all ranged abilities by (\d+(?:\.\d+)?)%", ("@ranged",)),
    ),
    "Ranged Weapon Specialization": (
        EffectRule("damage_pct", r"damage you deal with ranged weapons by (\d+(?:\.\d+)?)%", ("@ranged",)),
    ),
    "Barrage": (
        EffectRule("damage_pct", r"Multi-Shot, Aimed Shot, and Volley abilities by (\d+(?:\.\d+)?)%", ("Multi-Shot", "Aimed Shot", "Volley")),
    ),
    "Improved Arcane Shot": (
        EffectRule("cooldown", r"cooldown of your Arcane Shot by (\d+(?:\.\d+)?) sec", ("Arcane Shot",), sign=-1),
    ),
    "Efficiency": (
        EffectRule("mana_cost_pct", r"Mana cost of your Shots, Stings, and melee abilities by (\d+(?:\.\d+)?)%", ("@shot", "@sting", "@melee"), sign=-1),
    ),
    "Lone Wolf": (
        EffectRule("damage_pct", r"(\d+(?:\.\d+)?)% increased damage with all attacks", ("@no_pet",)),
    ),
    "Savage Strikes": (
        EffectRule("crit_chance", r"critical strike chance of all your melee abilities by (\d+(?:\.\d+)?)%", ("@melee",)),
    ),
    "Lacerating Strikes": (
        EffectRule("dot_pct", r"Bleed for damage equal to (\d+(?:\.\d+)?)% of the damage", ("Mongoose Bite",)),
    ),
    "Improved Stings": (
        EffectRule("damage_pct", r"damage of your Serpent Sting ability by (\d+(?:\.\d+)?)%", ("Serpent Sting",)),
    ),
    "Lightning Reflexes": (
        EffectRule("stat_pct", r"Agility by (\d+(?:\.\d+)?)%", ("agility",)),
    ),
    "Surefooted": (
        EffectRule("hit_chance", r"hit chance by (\d+(?:\.\d+)?)%", ("all",)),
    ),
    "Improved Tracking": (
        EffectRule("damage_pct", r"tracked creature type is increased by (\d+(?:\.\d+)?)%", ("@tracked",)),
    ),
    "Focused Fire": (
        EffectRule("damage_pct", r"damage you and your pet deal by (\d+(?:\.\d+)?)%", ("@with_pet",)),
    ),
    "Unleashed Fury": (
        EffectRule("damage_pct", r"damage done by your pets and hawks by (\d+(?:\.\d+)?)%", ("@pet",)),
    ),
    "Ferocity": (
        EffectRule("crit_chance", r"critical strike chance of your pets and hawks by (\d+(?:\.\d+)?)%", ("@pet",)),
    ),
    "Predator's Edge": (
        EffectRule("crit_damage_pct", r"melee critical strike damage by (\d+(?:\.\d+)?)%", ("@melee",)),
        EffectRule("damage_pct", r"Off Hand weapon damage by (\d+(?:\.\d+)?)%", ("@off_hand",)),
    ),
}

# Every hunter talent without an effect rule, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Beast Mastery
    "Deadly Aspects": "proc: attack speed proc while Aspects of Hawk or Beast are active",
    "Endurance Training": "pet: +15% pet health and armor (#111)",
    "Improved Aspect of the Monkey": "defensive: bigger dodge from Aspect of the Monkey",
    "Pathfinding": "mobility: faster Aspect of the Cheetah and Aspect of the Pack",
    "Improved Revive Pet": "pet: faster, cheaper Revive Pet with more pet health (#111)",
    "Bestial Swiftness": "pet: +30% pet movement speed (#111)",
    "Improved Mend Pet": "pet: Mend Pet cleanse chance and lower mana cost (#111)",
    "Summon Hawk": "grants_spell",
    "Spirit Bond": "pet: health regen for you and your pet while it is active (#111)",
    "Intimidation": "grants_spell",
    "Bestial Discipline": "resource: pet focus regen + 50% mana regen while casting",
    "Frenzy": "pet: pet attack speed proc after crits (#111)",
    "Bestial Wrath": "grants_spell",
    # Marksmanship
    "Hawk Eye": "utility: +6 yds ranged weapon range",
    "Improved Concussive Shot": "control: 20% chance to stun with Concussive Shot",
    "Rapid Killing": "ranged damage: Rapid Fire cooldown + shot damage after kills (#111)",
    "Trueshot Aura": "grants_spell",
    "Rapid Recuperation": "resource: mana regen while casting after Serpent Sting hits",
    "Scatter Shot": "grants_spell",
    "Sniper Shot": "grants_spell",
    # Survival
    "Deflection": "defensive: +5% parry chance",
    "Entrapment": "trap: triggered traps root affected targets",
    "Survivalist": "defensive: +10% total health",
    "Improved Wing Clip": "control: 20% chance to immobilize with Wing Clip",
    "Clever Traps": "trap: longer freeze/frost and stronger immolation/explosive traps",
    "Deterrence": "grants_spell",
    "Survival Tactics": "trap: +10% hit with traps and Feign Death",
    "Counterattack": "grants_spell",
    "Resourcefulness": "trap: -60% trap and melee mana cost, crit mana regen",
    "Expose Prey": "melee damage: chance to extend Mongoose Bite on marked prey (#111)",
    "Survivalist's Discipline": "trap: -40% trap and Deterrence cooldowns",
    "Strider Kick": "grants_spell",
}

# Hunter skill lines in SkillLineAbility: Beast Mastery, Marksmanship, Survival.
SKILL_LINES = (50, 163, 51)
