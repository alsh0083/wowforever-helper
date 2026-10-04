# Default character stats

One CSV per class. Rows are anchor levels; the loader interpolates linearly between them, so add or edit rows freely. Values are **totals** (base + gear + enchants), assuming a mage in typical quest/dungeon gear.

| Column | Meaning |
|---|---|
| `spell_power` | bonus spell damage from gear |
| `crit_pct` | total spell crit chance %, before talents |
| `hit_pct` | spell hit from gear %, before talents (base miss chance comes from level difference, not this table) |
| `mana`, `health` | pools at full |

**Confidence: low.** These are rough estimates for the shape of the curve: near-zero spell power while leveling, then a jump at 60 from dungeon blues. They exist so crit- and spell-power-dependent talents aren't valued at zero. They are not real Forever numbers. Replace them with game base stats from wago.tools when parsed, and later with the owner's real character (#33). Rankings should be checked for sensitivity to this table before being trusted.
