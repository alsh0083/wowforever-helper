# Data sources: what lives where

Checked 2026-10-04 against Forever beta build 1.60.1.70205.

## Talent trees come from the Trait tables, not `Talent`

- The client's legacy `Talent`/`TalentTab` tables are **stale**: they hold an earlier draft of the Forever mage trees (no Hot Streak, Heating Up or Fingers of Frost; Burning Soul at 2 ranks; Flame Throwing and Fire Power still present). wago.tools' hotfix option doesn't change them.
- The live trees are built on the modern **Trait** system: one trait tree per class holds all three trees side by side (mage = trait tree 1112, 54 nodes, matching wowforevertalent.com's 18/17/19).
  - Tree = PosX band (mage: Arcane from 1020, Fire from 5020, Frost from 9080); row/column = PosY/PosX steps of 600 from the first row (PosY 2130).
  - Ranks: `TraitNodeEntry.MaxRanks`; spell: `TraitDefinition.SpellID`; prerequisites: `TraitEdge` (left → right).
  - Per-class layout lives in `src/wowforever/classes/<class>.py`.
- Prerequisite rank is assumed to be the prerequisite's max rank (Classic rule; the legacy table agrees, e.g. Combustion needs Critical Mass 3/3). Not yet confirmed from `TraitCond`.

## Spell data

- Spell tables (`SpellEffect`, `SpellMisc`, `SpellTargetRestrictions`, ...) do carry Forever values: Cone of Cold's slow is 40%, and no AoE spell has a `MaxTargets` cap.

## Source lag

- wowforevertalent.com and wago.tools update independently (on 2026-10-04: 1.60.1.70170 vs 1.60.1.70205). The normalizer reports this; the cross-check (#12) compares contents.
