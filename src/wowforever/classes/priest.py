"""Priest-specific knowledge: where the Forever priest talent trees live in the client's trait data.

Stage 1 (#152, #158): trees, spells and every talent classified. Stage 2 (#164): Shadow and
Discipline Smite on the caster spell engine.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1114 holds all three priest trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="priest",
    trait_tree_id=1114,
    trees=(
        TreeBand(tree_id=1, name="Discipline", min_x=1020),
        TreeBand(tree_id=2, name="Holy", min_x=5020),
        TreeBand(tree_id=3, name="Shadow", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
    # A second Holy Specialization node (105865) is parked at Y 21300, off the talent UI.
    hidden_nodes=frozenset({105865}),
)

# Numbers are read from the rank text (#164).
TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {
    "Darkness": (
        EffectRule("damage_pct", r"Shadow damage done by (\d+(?:\.\d+)?)%", ("shadow",)),
    ),
    "Shadowform": (
        EffectRule("damage_pct", r"increasing your Shadow damage by (\d+(?:\.\d+)?)%", ("shadow",)),
        EffectRule("mana_cost_pct", r"Mana cost of all Shadow spells by (\d+(?:\.\d+)?)%", ("shadow",), sign=-1),
        EffectRule("crit_damage_pct", r"critical strike damage bonus of your Shadow spells by (\d+(?:\.\d+)?)%", ("shadow",)),
    ),
    "Shadow Focus": (
        EffectRule("hit_chance", r"chance to hit with Shadow spells by (\d+(?:\.\d+)?)%", ("shadow",)),
    ),
    "Shadow Weaving": (
        EffectRule("damage_pct",
                   r"(\d+)% chance to increase the Shadow damage you deal by (\d+)% for \d+ sec, stacking up to (\d+) times",
                   ("shadow",), combine=lambda m: float(m.group(1)) / 100 * float(m.group(2)) * float(m.group(3))),
    ),
    "Improved Mind Flay": (
        EffectRule("damage_pct", r"Mind Flay now deals (\d+(?:\.\d+)?)% more damage", ("Mind Flay",)),
    ),
    "Improved Mind Blast": (
        EffectRule("cooldown", r"cooldown of your Mind Blast spell by (\d+(?:\.\d+)?) sec", ("Mind Blast",), sign=-1),
    ),
    "Holy Specialization": (
        EffectRule("crit_chance", r"critical effect chance of your Holy spells by (\d+(?:\.\d+)?)%", ("holy",)),
    ),
    "Holy Precision": (
        EffectRule("hit_chance", r"chance to hit with Holy spells by (\d+(?:\.\d+)?)%", ("holy",)),
    ),
    "Searing Light": (
        EffectRule("damage_pct", r"Holy damage done by (\d+(?:\.\d+)?)%", ("holy",)),
    ),
    "Divine Fury": (
        EffectRule("cast_time", r"casting time of your Smite, Holy Fire, Heal, and Greater Heal spells by (\d+(?:\.\d+)?) sec",
                   ("Smite", "Holy Fire"), sign=-1),
    ),
    "Mental Agility": (
        EffectRule("mana_cost_pct", r"mana cost of your Smite, Holy Fire, and instant cast spells by (\d+(?:\.\d+)?)%",
                   ("Smite", "Holy Fire"), sign=-1),
    ),
    "Meditation": (
        EffectRule("regen_while_casting", r"Allows (\d+(?:\.\d+)?)% of your Mana regeneration", ("all",)),
    ),
}

# Every priest talent, with why it isn't modeled.
UNMODELED: dict[str, str] = {
    # Discipline
    "Power in Light": "damage: Smite and Penance vs Holy Fire targets",
    "Wand Specialization": "damage: +25% wand damage",
    "Twin Disciplines": "damage: +5% instant spell damage and healing",
    "Silent Resolve": "defensive: shorter stuns, fears and silences, less threat",
    "Improved Power Word: Shield": "defensive: stronger Power Word: Shield",
    "Martyrdom": "defensive: pushback immunity after being crit",
    "Inner Focus": "grants_spell",
    "Improved Inner Fire": "defensive: stronger Inner Fire",
    "Mental Strength": "buff: +15% Intellect",
    "Soul Warding": "defensive: faster, cheaper Power Word: Shield",
    "Improved Mana Burn": "resource: faster Mana Burn",
    "Penance": "grants_spell",
    "Renewed Hope": "healing: heal crit",
    "Divine Aegis": "healing: crit heals leave a shield",
    "Power Infusion": "grants_spell",
    # Holy
    "Twilight Focus": "utility: 70% pushback avoidance",
    "Improved Renew": "healing: +15% Renew",
    "Spell Warding": "defensive: 10% less spell damage taken",
    "Holy Nova": "grants_spell",
    "Blessed Recovery": "defensive: heal after big hits",
    "Inspiration": "healing: crit heals raise target armor",
    "Holy Reach": "utility: Smite, Holy Fire and Holy Nova range",
    "Improved Healing": "resource: cheaper heals",
    "Binding Heal": "grants_spell",
    "Litany of Light": "resource: mana back when alternating heals",
    "Spirit of Redemption": "healing: keep healing after death",
    "Spiritual Guidance": "healing: spell power from Spirit",
    "Spiritual Healing": "healing: +10% healing",
    "Prayer of Mending": "grants_spell",
    # Shadow
    "Blackout": "control: Shadow spells can stun 3 s",
    "Spirit Tap": "resource: Spirit after kills",
    "Shadow Affinity": "threat: less Shadow threat",
    "Improved Shadow Word: Pain": "damage: longer Shadow Word: Pain",
    "Shadow Reach": "utility: +20% Shadow range",
    "Improved Psychic Scream": "control: Psychic Scream cooldown -4 s",
    "Mind Flay": "grants_spell",
    "Improved Fade": "defensive: Fade cooldown -6 s",
    "Vampiric Embrace": "grants_spell",
    "Silence": "grants_spell",
    "Devouring Contagion": "damage: cheaper, spreading Devouring Plague",
    "Early Demise": "damage: Shadow Word: Death crit below 20%",
}

# Priest skill lines in SkillLineAbility: Discipline, Holy, Shadow.
SKILL_LINES = (613, 56, 78)

# Scored by the caster spell engine (#163, #164).
ENGINE = "spell"
ROTATION = {
    "dots": ("Shadow Word: Pain", "Devouring Plague"),
    "cooldowns": ("Mind Blast", "Shadow Word: Death"),
    "fillers": ("Mind Flay", "Smite", "Holy Fire"),
}
# Healing stays unscored (planning round 2, Q3): the Holy tree and the Discipline healer build.
UNSCORED_TREES = ("Holy",)
UNSCORED_BUILDS = ("priest-discipline",)
CAVEAT = ("Caster model (#163): Shadow Word: Pain and Devouring Plague kept up, Mind Blast and Shadow Word: "
          "Death on cooldown, Mind Flay or Smite in between, with Classic hit, crit and mana rules. Shadow "
          "Weaving counts at full stacks; Vampiric Embrace's healing, Twin Disciplines and Improved Shadow "
          "Word: Pain's longer duration aren't modeled. Base stats are estimates; healer builds stay unscored.")
