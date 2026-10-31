# Hotfix cache fixtures (#456)

- `DBCache-sample.bin`: the header and six entries cut, byte for byte, from the owner's client hotfix cache
  (`data/raw/hotfixes/1.60.1.70707-20261031/DBCache.bin`, build 1.60.1.70707, captured 2026-10-31 at character select).
  The entries, in file order:

  | table (hash) | record | push | status | data |
  |---|---|---|---|---|
  | 0xAE1CA308 | 580844 | 112618 | 3 (invalid) | none |
  | SpellName (0x46C66698) | 1326589 | 112635 | 4 (not public) | none |
  | TraitNode (0xE1432D63) | 105773 | 112753 | 2 (record removed) | none |
  | SpellName | 2118 | 112758 | 2 (record removed) | none |
  | SpellName | 468843 | 112758 | 1 (valid) | `Lacerate\0` |
  | TraitNode | 104951 | 113283 | 1 (valid) | 25 bytes: Lacerate's node in the druid tree |

- `SpellName.dbd`, `TraitNode.dbd`: WoWDBDefs definitions (github.com/wowdev/WoWDBDefs), as saved with build 1.60.1.70707.
  Their 70707 layouts are `782EE721` (SpellName) and `A01A518A` (TraitNode).
