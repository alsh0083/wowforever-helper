"""Heals over time, Swiftmend and heal crits in self-healing (#279, #283).

A healing phase opens with each HoT in config `hots` once (direct part plus its full periodic
healing, counted as effective health: fights outlast the 12-21 s HoTs), then `hot_burst`
(Swiftmend: copies the biggest HoT's periodic healing; needs its talent; adds nothing when the
`swiftmend_consumes_hot` assumption is on). The rest of the healing mana goes to the best direct
heal per second, as before. If the opening heals cost more than the healing mana, they scale down
to fit and no direct heal follows.

Talents: healing % applies to both parts when it targets "all" or the spell by name, to the
periodic part only when it targets "periodic" (Genesis); healing % adds up. Nature's Splendor
lengthens a HoT, so its periodic healing grows by (duration + extra) / duration. Gift of the
Earthmother cuts Rejuvenation's and Swiftmend's global cooldown to 1.0 s.

Crits (#283): direct healing crits for 150% (the spell engine's base) at the caster row's crit plus
crit talents that target "all" or the heal by name (Nature's Majesty, Moonkin Form, Improved
Regrowth); periodic healing and Swiftmend don't crit. A melee row's crit is melee crit, so a Feral
build's heals crit only from talents. Factor = 1 + crit x 0.5.

Spells at 60: Rejuvenation 776 over 12 s (coefficient 0.8, 360 mana, instant); Regrowth 1021 direct
(0.286) + 994 over 21 s (0.497), 2.0 s, 525 mana; Healing Touch 2332 (1.0), 3.5 s, 840 mana.
Heal mana share 0.5.

Restoration PvP 60 (312 spell power, 5030 mana, 14.13% crit; Gift of Nature 2, Improved Rejuvenation 3,
Gift of the Earthmother, Swiftmend, Naturalist 5, Tranquil Spirit 1, Improved Regrowth 5):
  Rejuvenation (776 + 249.6) x 1.19 = 1220.464 in 1.0 s, 360 mana
  Regrowth (1021 + 89.232) x 1.04 x (1 + 0.6413 x 0.5) = 1524.877 + (994 + 155.064) x 1.04 = 1195.027,
    2.0 s, 525 mana
  Swiftmend 1220.464 in 1.0 s, no mana
  opening 5160.832 in 4.0 s for 885 of 2515 mana; Healing Touch 2749.76 x 1.07065 = 2944.031 per 3.0 s
  for 823.2 mana: 1630 x 2944.031 / 823.2 = 5829.409 in 5.9403 s
  budget 10990.241, 1105.632/s
  Swiftmend consuming the HoT: opening 3940.368 in 3.0 s, budget 9769.777, 1092.788/s
Balance PvP 60 (21.13% crit with Nature's Majesty 2 and Moonkin Form; Genesis 5, Nature's Splendor,
Naturalist 5; no Swiftmend talent):
  Rejuvenation 1025.6 x 1.05 x 15/12 = 1346.100 in 1.5 s
  Regrowth 1110.232 x 1.10565 = 1227.528 + 1149.064 x 1.05 x 27/21 = 1551.236, 2.0 s
  opening 4124.864 in 3.5 s; Healing Touch 2644 x 1.10565 = 2923.339 per 3.0 s for 840 mana
  budget 9797.533, 1051.076/s
Feral 60 (no spell power, 2690 mana, 4% crit from Nature's Majesty; Genesis 5): opening
  814.8 + 1021 x 1.02 + 1043.7 = 2899.92 in 3.5 s; Healing Touch 2332 x 1.02 = 2378.64 per 3.5 s;
  budget 4202.509, 775.848/s
Restoration PvP 30 (93 spell power, 2330 mana, 7.83% crit; Naturalist 5, Gift of Nature 1): Rejuvenation
  r5 247.248; Regrowth r4 344.350 x 1.03915 = 357.831 + 347.025; opening 952.105 in 3.5 s for 345 mana;
  Healing Touch r5 651.78 x 1.03915 = 677.297 per 3.0 s for 280; budget 2935.618, 238.946/s
Mana-short (Restoration PvP 60 at heal mana share 0.05): 251.5 of 885 mana, so the opening scales
  by 0.284181: budget 1466.609 at the opening's 5160.832 / 4.0 = 1290.208/s
"""

from pathlib import Path

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes.druid import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import HybridTable, MeleeStatTable
from wowforever.pvp import class_pvp
from wowforever.pvp.class_pvp import heal_capacity, heal_modifiers
from wowforever.report import ranks_at
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import StatTable

CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("druid"), TALENT_EFFECTS, UNMODELED)
# the stat rows the hand-worked values below use, frozen (1.60.1.70205 gear; #416 moved the live tables)
FROZEN = Path(__file__).parent / "fixtures" / "stats-70205"
TABLE = HybridTable(StatTable.load("druid", FROZEN), MeleeStatTable.load("druid_melee", config_dir=FROZEN))
BUILDS = {b.id: b for b in load_builds(class_name="druid")}
CONSUMES = Assumptions.load().with_values(swiftmend_consumes_hot=True)


def final(build_id):
    return BUILDS[build_id].final_ids(CLS)


def spell(name, level=60):
    return max((s for s in CLS.spells if s.name == name and s.level <= level), key=lambda s: s.rank)


def effects(name):
    return [(e.kind, e.values, e.applies_to) for e in next(t for t in CLS.talents if t.name == name).effects]


def test_hot_talents_parse_from_their_rank_texts():
    assert PROBLEMS == []
    assert ("healing_pct", (1.0, 2.0, 3.0, 4.0, 5.0), ("periodic",)) in effects("Genesis")
    assert effects("Improved Rejuvenation") == [("healing_pct", (5.0, 10.0, 15.0), ("Rejuvenation",))]
    assert effects("Nature's Splendor") == [("duration", (3.0,), ("Rejuvenation",)), ("duration", (6.0,), ("Regrowth",))]
    assert effects("Gift of the Earthmother") == [("gcd", (-0.5,), ("Rejuvenation", "Swiftmend", "Wild Growth"))]


def test_heal_modifiers_split_direct_and_periodic_healing():
    resto = heal_modifiers(spell("Rejuvenation"), CLS, final("druid-restoration-pvp"))
    assert (resto.direct_pct, resto.periodic_pct, resto.gcd) == (pytest.approx(19.0), pytest.approx(19.0), pytest.approx(-0.5))
    balance = heal_modifiers(spell("Regrowth"), CLS, final("druid-balance-pvp"))
    assert (balance.direct_pct, balance.periodic_pct, balance.duration) == (0.0, pytest.approx(5.0), pytest.approx(6.0))
    # Moonglow cuts damaging spells only; Naturalist names Healing Touch
    touch = heal_modifiers(spell("Healing Touch"), CLS, final("druid-balance-pvp"))
    assert (touch.cast, touch.cost) == (pytest.approx(-0.5), 0.0)


def test_restoration_opens_with_hots_and_swiftmend():
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-restoration-pvp"))
    assert hps == pytest.approx(1105.632, rel=1e-4) and budget == pytest.approx(10990.241, rel=1e-4)


def test_swiftmend_adds_nothing_when_it_consumes_the_hot():
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-restoration-pvp"),
                                assumptions=CONSUMES)
    assert hps == pytest.approx(1092.788, rel=1e-4) and budget == pytest.approx(9769.777, rel=1e-4)


def test_balance_gets_longer_hots_but_no_swiftmend():
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-balance-pvp"))
    assert hps == pytest.approx(1051.076, rel=1e-4) and budget == pytest.approx(9797.533, rel=1e-4)


def test_feral_hots_without_spell_power():
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-feral"))
    assert hps == pytest.approx(775.848, rel=1e-4) and budget == pytest.approx(4202.509, rel=1e-4)


def test_restoration_at_the_beta_cap():
    ranks = ranks_at(BUILDS["druid-restoration-pvp-leveling"].order_ids(CLS), 30, CLS)
    hps, budget = heal_capacity("druid", TABLE.at(30), CLS.spells, CLS, ranks)
    assert hps == pytest.approx(238.946, rel=1e-4) and budget == pytest.approx(2935.618, rel=1e-4)


def test_opening_heals_scale_down_when_mana_is_short(monkeypatch):
    real = class_pvp.load_toml

    def short(path):
        cfg = real(path)
        return {**cfg, "druid": {**cfg["druid"], "heal_mana_share": 0.05}}

    monkeypatch.setattr(class_pvp, "load_toml", short)
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-restoration-pvp"))
    assert hps == pytest.approx(1290.208, rel=1e-4) and budget == pytest.approx(1466.609, rel=1e-4)


def test_crit_talents_reach_heals_by_name_or_all():
    assert ("crit_chance", (10.0, 20.0, 30.0, 40.0, 50.0), ("Regrowth",)) in effects("Improved Regrowth")
    assert heal_modifiers(spell("Regrowth"), CLS, final("druid-restoration-pvp")).crit == pytest.approx(50.0)
    # Nature's Majesty and Moonkin Form target "all"; Improved Moonfire names Moonfire
    assert heal_modifiers(spell("Healing Touch"), CLS, final("druid-balance-pvp")).crit == pytest.approx(7.0)
    # Sharpened Claws and Leader of the Pack need cat or bear form
    assert heal_modifiers(spell("Healing Touch"), CLS, final("druid-feral")).crit == pytest.approx(4.0)
