"""The outnumbered (2v1) score in the reports (#287): a row at each checkpoint, next to the duel scenarios.

Mage (report.score_build): the best over the questing fillers of outnumbered_scores(mage_side(char,
filler), kits at that level)["score"], with that filler's name; unit "2v1 0-1". The other classes
(melee_report) use class_pvp.outnumbered_score; tests/test_melee_report.py checks their rows.
"""

import pytest

pytestmark = pytest.mark.slow   # score_build runs every scenario at five levels (~10 s)

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes.mage import TALENT_EFFECTS, UNMODELED
from wowforever.effects import attach_effects
from wowforever.pvp.duel import load_kits, mage_side, outnumbered_scores
from wowforever.report import CHECKPOINTS, ranks_at, score_build
from wowforever.scenarios import Character, default_params, usable_fillers
from wowforever.schema import Dataset, latest_dataset_path
from wowforever.stats import StatTable

CLS, _ = attach_effects(Dataset.load(latest_dataset_path()).class_data("mage"), TALENT_EFFECTS, UNMODELED)


def test_mage_rows_take_the_best_filler():
    build = next(b for b in load_builds(class_name="mage") if b.order)
    order = build.order_ids(CLS)
    stats, assumptions = StatTable.load("mage"), Assumptions.load()
    rows = score_build(order, CLS, CLS.spells, stats, assumptions)["outnumbered"]
    assert set(rows) == set(CHECKPOINTS)
    char = Character(60, stats.at(60), CLS.spells, CLS, ranks_at(order, 60, CLS))
    fillers = usable_fillers(char, default_params("questing", 60).fillers, 60, assumptions)
    best = max((outnumbered_scores(mage_side(char, f), load_kits(level=60))["score"], f.name) for f in fillers)
    assert rows[60] == {"score": pytest.approx(round(best[0], 3)), "unit": "2v1 0-1", "spell": best[1]}
