"""Warlock-specific knowledge: where the Forever warlock talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #152): the trees and spells load and every talent is
classified; nothing is modeled yet. The warlock is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

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

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every warlock talent, with why it isn't modeled. TODO(#152): classify every talent.
UNMODELED: dict[str, str] = {}

# Warlock skill lines in SkillLineAbility: Affliction, Demonology, Destruction.
SKILL_LINES = (355, 354, 593)
