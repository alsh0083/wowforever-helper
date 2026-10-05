"""Priest-specific knowledge: where the Forever priest talent trees live in the client's trait data.

Stage 1 of class-specific opponents (#34, #152): the trees and spells load and every talent is
classified; nothing is modeled yet. The priest is an opponent, not a dashboard class.
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

TALENT_EFFECTS: dict[str, tuple[EffectRule, ...]] = {}

# Every priest talent, with why it isn't modeled. TODO(#152): classify every talent.
UNMODELED: dict[str, str] = {}

# Priest skill lines in SkillLineAbility: Discipline, Holy, Shadow.
SKILL_LINES = (613, 56, 78)
