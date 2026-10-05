"""Warrior-specific knowledge: where the Forever warrior talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #149): the trees and spells load and every talent is
classified; nothing is modeled yet. The warrior is an opponent, not a dashboard class.
"""

from wowforever.classes import EffectRule, TraitLayout, TreeBand

# Trait tree 1117 holds all three warrior trees side by side, on the same grid as the mage's 1112.
LAYOUT = TraitLayout(
    class_name="warrior",
    trait_tree_id=1117,
    trees=(
        TreeBand(tree_id=1, name="Arms", min_x=1020),
        TreeBand(tree_id=2, name="Fury", min_x=5020),
        TreeBand(tree_id=3, name="Protection", min_x=9080),
    ),
    first_row_y=2130,
    grid=600,
)

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every warrior talent, with why it isn't modeled. TODO(#149): classify every talent.
UNMODELED: dict[str, str] = {}

# Warrior skill lines in SkillLineAbility: Arms, Fury, Protection.
SKILL_LINES = (26, 256, 257)
