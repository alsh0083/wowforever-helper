"""Heals over time and Swiftmend in self-healing (#279).

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

Spells at 60: Rejuvenation 776 over 12 s (coefficient 0.8, 360 mana, instant); Regrowth 1021 direct
(0.286) + 994 over 21 s (0.497), 2.0 s, 525 mana; Healing Touch 2332 (1.0), 3.5 s, 840 mana.
Heal mana share 0.5.

Restoration PvP 60 (312 spell power, 5030 mana; Gift of Nature 2, Improved Rejuvenation 3, Gift of
the Earthmother, Swiftmend, Naturalist 5, Tranquil Spirit 1):
  Rejuvenation (776 + 249.6) x 1.19 = 1220.464 in 1.0 s, 360 mana
  Regrowth (1021 + 89.232) x 1.04 = 1154.641 + (994 + 155.064) x 1.04 = 1195.027, 2.0 s, 525 mana
  Swiftmend 1220.464 in 1.0 s, no mana
  opening 4790.596 in 4.0 s for 885 of 2515 mana; Healing Touch 2749.76 per 3.0 s for 823.2 mana:
  1630 mana x 2749.76 / 823.2 = 5444.738 in 5.9403 s
  budget 10235.334, 10235.334 / 9.9403 = 1029.688/s
  Swiftmend consuming the HoT: opening 3570.132 in 3.0 s, budget 9014.870, 1008.348/s
Balance PvP 60 (Genesis 5, Nature's Splendor, Naturalist 5; no Swiftmend talent):
  Rejuvenation 1025.6 x 1.05 x 15/12 = 1346.100 in 1.5 s
  Regrowth 1110.232 + 1149.064 x 1.05 x 27/21 = 1551.236, 2.0 s
  opening 4007.568 in 3.5 s; Healing Touch 2644 per 3.0 s for 840: 1630 x 2644/840 = 5130.619
  budget 9138.187, 980.342/s
Feral 60 (no spell power, 2690 mana; Genesis 5): opening 814.8 + 1021 + 1043.7 = 2879.5 in 3.5 s;
  Healing Touch 2332 per 3.5 s: 460 x 2332/840 = 1277.048; budget 4156.548, 767.363/s
Restoration PvP 30 (93 spell power, 2330 mana; Naturalist 5, Gift of Nature 1): Rejuvenation r5
  (168 + 74.4) x 1.02 = 247.248; Regrowth r4 344.350 + 347.025; opening 938.623 in 3.5 s for 345 mana;
  Healing Touch r5 651.78 per 3.0 s for 280: 820 x 651.78/280 = 1908.785; budget 2847.408, 231.766/s
Mana-short (Restoration PvP 60 at heal mana share 0.05): 251.5 of 885 mana, so the opening scales
  by 0.284181: budget 1361.395 at the opening's 4790.596 / 4.0 = 1197.649/s
"""

import pytest

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes.druid import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.melee_scenarios import stat_table
from wowforever.pvp import class_pvp
from wowforever.pvp.class_pvp import heal_capacity, heal_modifiers
from wowforever.report import ranks_at
from wowforever.schema import Dataset, latest_dataset_path

CLS, PROBLEMS = attach_effects(Dataset.load(latest_dataset_path()).class_data("druid"), TALENT_EFFECTS, UNMODELED)
TABLE = stat_table("druid")
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
    assert hps == pytest.approx(1029.688, rel=1e-4) and budget == pytest.approx(10235.334, rel=1e-4)


def test_swiftmend_adds_nothing_when_it_consumes_the_hot():
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-restoration-pvp"),
                                assumptions=CONSUMES)
    assert hps == pytest.approx(1008.348, rel=1e-4) and budget == pytest.approx(9014.870, rel=1e-4)


def test_balance_gets_longer_hots_but_no_swiftmend():
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-balance-pvp"))
    assert hps == pytest.approx(980.342, rel=1e-4) and budget == pytest.approx(9138.187, rel=1e-4)


def test_feral_hots_without_spell_power():
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-feral"))
    assert hps == pytest.approx(767.363, rel=1e-4) and budget == pytest.approx(4156.548, rel=1e-4)


def test_restoration_at_the_beta_cap():
    ranks = ranks_at(BUILDS["druid-restoration-pvp-leveling"].order_ids(CLS), 30, CLS)
    hps, budget = heal_capacity("druid", TABLE.at(30), CLS.spells, CLS, ranks)
    assert hps == pytest.approx(231.766, rel=1e-4) and budget == pytest.approx(2847.408, rel=1e-4)


def test_opening_heals_scale_down_when_mana_is_short(monkeypatch):
    real = class_pvp.load_toml

    def short(path):
        cfg = real(path)
        return {**cfg, "druid": {**cfg["druid"], "heal_mana_share": 0.05}}

    monkeypatch.setattr(class_pvp, "load_toml", short)
    hps, budget = heal_capacity("druid", TABLE.at(60), CLS.spells, CLS, final("druid-restoration-pvp"))
    assert hps == pytest.approx(1197.649, rel=1e-4) and budget == pytest.approx(1361.395, rel=1e-4)
