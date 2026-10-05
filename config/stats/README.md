# Default character stats

`mage.csv` is generated: `python -m wowforever gear-stats --tables <folder with ItemSparse, Item, RandPropPoints>` (#68). Rows are anchor levels; the loader interpolates between them.

Each row = base character stats (`mage_base.csv`, estimates) + the best gear set from **real Forever items** (client build 1.60.1.70205), chosen per slot by `config/gear.toml` weights:

- levels below 60: quest and dungeon quality (rare and below)
- level 60: pre-raid (epics up to item level 63; raid gear starts at 66)
- skipped: QA test items in the client, and level-scaling items whose listed item level is far above their required level

Derived stats follow Classic rules: 15 mana per Intellect, 10 health per Stamina, crit from Intellect, and ratings converted at 14 per 1% at 60 (from Robe of the Archmage; hit assumed the same).

**Confidence: low-medium.** Item stats are real; base stats, weights and rating scaling below 60 are estimates. Replaced by the owner's character at launch (#33).
