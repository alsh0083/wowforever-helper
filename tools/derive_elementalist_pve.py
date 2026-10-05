"""Re-derive the revised Offensive Elementalist (PvE) (#101) after a patch:

    .venv/Scripts/python tools/derive_elementalist_pve.py

It prints the scores, the talent changes and a TOML `order` to paste into
config/builds/elementalist-pve-v2.toml. #101: revised Offensive Elementalist (PvE). Levels 10-40 (31 points) stay the PvP route;
the 20 points from 41 to 60 are chosen by hill-climbing the PvE focus score."""

from collections import Counter

from wowforever.assumptions import Assumptions
from wowforever.builds import load_builds
from wowforever.classes import class_module
from wowforever.consensus import Consensus
from wowforever.effects import attach_effects
from wowforever.focus import pve_score_fn
from wowforever.optimizer import _legal_now
from wowforever.schema import Dataset
from wowforever.shortlist import improve
from wowforever.stats import StatTable

from pathlib import Path

m = class_module("mage")
ds = Dataset.load(Path("data/datasets/1.60.1.70205.json"))
cls, _ = attach_effects(ds.class_data("mage"), m.TALENT_EFFECTS, m.UNMODELED)
builds = {b.id: b for b in load_builds()}
A = Assumptions.load()
score = pve_score_fn(cls, StatTable.load("mage").at(60), A)
arch = Consensus.load().archetypes
name_of = {t.talent_id: t.name for t in cls.talents}

pvp_order = builds["elementalist-v4"].order_ids(cls)
shared = pvp_order[:31]                       # levels 10-40
lock = Counter(shared)


def locked_score(ranks):
    if any(ranks.get(t, 0) < r for t, r in lock.items()):
        return -1e9
    return score(ranks)


start = builds["elementalist-pve"].final_ids(cls)
print("original PvE", round(score(start), 4), " fire-frost-shatter",
      round(score(builds["fire-frost-shatter"].final_ids(cls)), 4))
best, best_score = improve(cls, start, locked_score, archetype="Fire/Frost", deep=arch["deep"],
                           hybrid=arch["hybrid"], recognized=tuple(arch["recognized"]), max_evals=4000)
print("revised PvE", round(best_score, 4))
changes = {name_of[t]: (start.get(t, 0), best.get(t, 0)) for t in set(start) | set(best)
           if start.get(t, 0) != best.get(t, 0)}
print("changes", changes)

# order the 20 points after 40: greedily by PvE score among legal points
by_id = {t.talent_id: t for t in cls.talents}
ranks = Counter(shared)
order = list(shared)
remaining = Counter(best) - Counter(shared)
while sum(remaining.values()):
    options = [t for t, n in remaining.items() if n > 0 and _legal_now(by_id[t], dict(ranks), by_id, cls.rules)]
    pick = max(options, key=lambda t: (score({**ranks, t: ranks[t] + 1}), -by_id[t].row, -t))
    ranks[pick] += 1
    remaining[pick] -= 1
    order.append(pick)
print("order 41-60:", [name_of[t] for t in order[31:]])
print("TOML:")
for i, t in enumerate(order):
    print(f'  "{name_of[t]}",  # {10 + i}')
