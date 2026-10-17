# Talent paths vs Icy Veins' level-30 builds

Checked 2026-10-07: each build's first 21 points against Icy Veins' level-30 guide build for the same main
tree (`wowforever icy-veins` prints this table; it's a background sanity check, not shown on the page, since
the guide builds stop at level 30 while talent paths run to 60).

| Agreement | Builds |
|---|---|
| 16-19 of 21 | Enhancement shaman, Retribution paladin, Marksmanship hunter, Balance druid, Fire/Frost and Offensive Elementalist mage |
| 9-15 of 21 | Arms warrior, Feral druid, Deep Frost/Deep Arcane mage, Affliction warlock, Discipline priest, Combat and Assassination rogue, Survival PvP hunter, Protection paladin |
| 0-8 of 21 | Shadow priest (1-3), Subtlety rogue (0-5), Restoration druid (0), Beast Mastery hunter (1-6), Demonology warlock (3-5), Elemental shaman (5), healers |

Most low scores are structural, not order bugs: a talent path only spends points on the talents of the
build's final level-60 setup, while Icy Veins' leveling builds take leveling talents and respec later (Shadow
priest: Wand Specialization, Spirit Tap, Twilight Focus; Restoration druid: a Feral/Balance leveling route).
Where both trees agree, the differences show order choices worth checking against the model (e.g. Icy
Veins takes Mind Flay at 25, the Shadowform path at 33).

Possible next step: a leveling variant per build that may use leveling-only talents and converges on the
final build by respec at a chosen level.

## Recheck 2026-10-17 (1.60.1.70425, #376)

18 of Icy Veins' guide builds were updated on Oct 16 for the patch (Malediction is gone; the warlock guides now
take Grim Reach). Agreement moved for 48 of 133 builds, mostly up:
- Builds that used to share no main tree now match: Fire/Frost Shatter 15, Elemental shaman 10-14, Affliction
  warlock 9-15, and the Deep Fire / Arcane Fire / Arcane PoM-Pyro mage builds 7-12. The one exception is
  Fire/Frost PvP, at 1.
- Clear gains: Deep Frost 12 -> 15 (leveling 7 -> 15), Frost PvE 8 -> 11, Offensive Elementalist 19 -> 21,
  Protection paladin 13 -> 17, Holy paladin leveling 17 -> 22, Discipline/Smite priest 5 -> 10.
- Shadow priest stays the lowest (0-5): Icy Veins still levels through Spirit Tap and Wand Specialization.

The wowforevertalent.com catalog plans behind priest-holy-pvp, priest-shadow-pve and warlock-affliction-pvp-guide
were rechecked the same day: the site marks all three "needs review" (not republished for the new tree), so
those builds keep their #369 `adjusted` ranks until the authors republish.
