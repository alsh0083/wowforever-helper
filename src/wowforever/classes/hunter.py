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

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every hunter talent, with why it isn't modeled. TODO (#107): fill from the rank text.
UNMODELED: dict[str, str] = {}

# Hunter skill lines in SkillLineAbility: Beast Mastery, Marksmanship, Survival.
SKILL_LINES = (50, 163, 51)
