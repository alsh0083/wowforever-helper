# Current Forever Mage mechanics — researched 25 September 2026

## What is verified, and what changed recently?

### Takeaway
Client data supports a real Frost/Fire interaction, but the level-40+ build remains theorycraft. The supplied calculator reference is stale on two Fire durations.

### Cited Findings
- Official beta announcement starts the cap at 20 and promises 30 later; September 24 notes do not announce a cap increase. Thus the available official evidence supports low-level testing, not normal player testing of level-40 Frostfire Bolt. [Beta announcement](https://worldofwarcraft.blizzard.com/en-us/news/24304160/the-world-of-warcraft-forever-beta-now-live), [September 24 notes](https://us.forums.blizzard.com/en/wow/t/wow-forever-beta-development-notes-%E2%80%93-updated-september-24/2360696)
- September 24: Wake of Fire proc duration increased 20→30 seconds, Hot Streak 15→20 seconds; Ignite no longer double dips percentage damage modifiers. Blizzard explicitly says Wake duration was extended because drinking between fights made it hard to exploit. [Official notes](https://us.forums.blizzard.com/en/wow/t/wow-forever-beta-development-notes-%E2%80%93-updated-september-24/2360696)
- Original calculator reference explicitly dates its export September 20 and disclaims Blizzard verification. It still shows old durations. Treat this as a talent-structure reference, not fully current tuning. [Reference](https://wowforevertalent.com/mage/reference/)
- Updated extraction site identifies build 1.60.1.70009 and Classic comparator 1.15.9.69722. Burning Soul is three points for 23/47/70% damage-pushback avoidance, unlocked after ten Fire points. This is damage pushback protection, not immunity to an opponent interrupting a cast. [Burning Soul extraction](https://wowforevertalents.com/mage/talents/burning-soul/)

### Inferences
- It is defensible to plan the order now, but not claim a tested consensus about high-level Forever Elementalist matchups.
- Wake is not merely a PvE kill-proc talent: its unconditional Fire Blast cooldown reduction deserves PvP consideration.

### Gaps
- No reliable controlled high-level Forever tests found. Many low-quality new Forever guide sites repeat data and errors; number of pages agreeing is not independent validation.

## Which talent prerequisites and interactions matter?

### Takeaway
The existing Frost defensive sequence is structurally legal. Several proposed Fire synergies have explicit client support, while proc edge cases remain unverified.

### Cited Findings
- Talent gates: Ice Block and Shatter require 15 earlier Frost points; Cold Snap and Fingers of Frost require 20. FoF additionally requires Ice Lance. Ice Barrier requires 30 Frost points plus Cold Snap. Impact requires five Fire points; Burning Soul and Pyroblast ten; Hot Streak fifteen plus Pyroblast. [Talent reference](https://wowforevertalent.com/mage/reference/)
- Wake cuts Fire Blast cooldown by 1/2 seconds. Incineration grants 2/4/6% crit to Fire Blast, Ice Lance, Scorch and Arcane Blast. Improved Fireball reduces Fireball AND Frostfire Bolt cast time by 0.1–0.5 seconds. Improved Frostbolt names Frostbolt alone. Shatter grants 17/33/50% crit against frozen targets to all spells. FoF has 15% proc chance at either rank; second rank increases affected casts from one to two. [Talent reference](https://wowforevertalent.com/mage/reference/)
- Impact ranks give 3/7/10% Fire stun chance, lasting two seconds. The database proc flag alone does not establish which periodic effects trigger it. [Impact client entry](https://www.wowhead.com/forever/spell=11103/impact)
- Elemental Precision is 1/2/3/4/5% via trait overrides. Wowhead headline misleadingly shows 6%, while the same page exposes the correct five override values. Do not transfer Classic two-point advice mechanically. [Elemental Precision client entry](https://www.wowhead.com/forever/spell=29438/elemental-precision)
- FFB begins at 40, with ranks at 50/60. Rank 1 costs 205 mana, has 35-yard range, 3-second cast, a 40% slow, and a nine-second periodic effect. Tooltip explicitly says it uses the lower Fire/Frost resistance and counts as both schools. Client lists direct spell-power coefficient 0.814 and periodic-can-crit flag. [Rank 1](https://www.wowhead.com/forever/spell=401502/frostfire-bolt), [Rank 2](https://www.wowhead.com/forever/spell=1237312/frostfire-bolt), [Rank 3](https://www.wowhead.com/forever/spell=1237313/frostfire-bolt)
- Flame Throwing lists actual Forever FFB IDs 401502, 1237312, 1237313 among affected spells; trait ranks grant 3/6 yards. This is stronger evidence than relying on the generic word Fire, but still not an in-game measurement. [Flame Throwing](https://www.wowhead.com/forever/spell=11100/flame-throwing)
- Ice Shards affected-spell list includes all three FFB ranks; Piercing Ice includes them for direct and periodic damage modifications. These are affirmative data-level synergy evidence, though affected lists also contain unused/NPC spell variants. [Ice Shards](https://www.wowhead.com/forever/spell=11207/ice-shards), [Piercing Ice](https://www.wowhead.com/forever/spell=11151/piercing-ice)

### Inferences
- Improved Fireball 5/5 should yield 2.5-second FFB. Flame Throwing should yield 38/41-yard FFB if displayed client associations function normally. Neither should be sold as a personally tested result.
- Frostfire being dual school plus slowing supports the proposed Shatter/FoF engine, but does not prove every damage tick procs Impact/FoF or how charges are consumed.
- For PvP, missing early Permafrost, Improved Frost Nova and Arctic Reach is a substantive opportunity cost of the baseline, not just a leveling-speed issue.
- Two Elemental Precision points mean 2%, not the old Classic 4%. If old equal-level 4% spell miss / 1% floor rules persist, three points would be a sensible target; do not present that as a verified Forever cap.

### Gaps
- No current controlled tests located for Impact off FFB hits versus DoT, FoF consumption/refresh timing, or Burning Soul specifically protecting FFB.
- No primary current documentation located proving Forever PvP spell miss floor or exact hit cap. Old Wowhead comments are imported and cannot establish this.

## What about defense and weakened AoE?

### Takeaway
Cold Snap is supported as an early defensive pickup, and the AoE-control reductions are real. Avoid assuming those reductions make all AoE or control talents worthless.

### Cited Findings
- Cold Snap is ten-minute cooldown, zero GCD, physical school, and resets other Frost cooldowns; actual effect is server scripted. [Cold Snap entry](https://www.wowhead.com/forever/spell=12472/cold-snap)
- Ice Block is Frost, five-minute cooldown, ten-second duration, prevents user actions, and lists remove-auras-on-immunity. Current entry shows no Hypothermia in tooltip or listed effects. This is absence of client evidence, not proof of server behavior. [Ice Block entry](https://www.wowhead.com/forever/spell=11958/ice-block)
- Improved Blizzard maximum slow is 40%; Permafrost changes duration to percentage rather than flat seconds, and adds up to ten percentage points of slow. [Reference](https://wowforevertalent.com/mage/reference/)
- Client comparison: Cone of Cold slow is 40% for six seconds versus Classic 50% for eight. Max-rank Blizzard base damage is 1168 versus 1192; therefore the cleanest documented issue is control, not evidence that all AoE damage has collapsed. [Spellbook comparison](https://foreverchanges.pro/spellbook/mage)

### Inferences
- Baseline Ice Block 25, Shatter 26–28, final Ice Shards 29, Cold Snap 30, FoF 31–32 is legal with one point per level starting 10.
- No basis to import modern Cold Snap healing or Wrath Hypothermia automatically.
- Stronger slows/range still help PvP even when enormous Blizzard grinding pulls are weaker. Do not dismiss Permafrost as only an AoE talent.

### Gaps
- No firm official source located confirming full Forever AoE target-cap or root/slow diminishing-return rules in this pass.
- Did not independently test any spell. Approximately 18 substantive source pages inspected/used (multiple rank pages share provenance); two official Blizzard sources, several distinct Wowhead client records, three fan extraction resources. Search-result filler and unrelated-era hits were excluded from evidence.
