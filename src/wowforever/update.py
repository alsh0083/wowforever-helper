"""On-demand update check (#13): fetch both sources, normalize one class, diff it against the
last saved dataset, and record the check. Each class is checked on its own and merged into the
build's dataset (#103), so a dataset holds every registered class.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from wowforever import builds as builds_module
from wowforever import crosscheck as crosscheck_module
from wowforever import effects as effects_module
from wowforever import normalize as normalize_module
from wowforever import normalize_spells as normalize_spells_module
from wowforever import revisions as revisions_module
from wowforever.assumptions import Assumptions
from wowforever.checklist import retest_names
from wowforever.classes import class_module
from wowforever.crosscheck import CrosscheckResult
from wowforever.revisions import Change
from wowforever.schema import ClassData, Dataset, Provenance
from wowforever.sources import wago, wowforevertalent
from wowforever.sources.http import http_get as default_http_get

WAGO_BUILDS_URL = "https://wago.tools/api/builds"
MAX_LISTED_CHANGES = 20


def _version_key(build: str) -> tuple[int, ...] | None:
    """Numeric sort key for a dotted build number, or None when not all parts are ints."""
    try:
        return tuple(int(part) for part in build.split("."))
    except ValueError:
        return None


def _previous_dataset(datasets_dir: Path, build: str) -> Path | None:
    """Saved dataset with the highest numeric build below `build`."""
    current = _version_key(build)
    best: tuple[tuple[int, ...], Path] | None = None
    for path in datasets_dir.glob("*.json"):
        key = _version_key(path.stem)
        if key is None or key >= current:
            continue
        if best is None or key > best[0]:
            best = (key, path)
    return best[1] if best is not None else None


@dataclass
class UpdateSummary:
    """Outcome of one update check."""

    build: str
    previous_build: str | None
    changed: bool
    changes: list[Change]
    affected_builds: list[str]
    crosscheck: CrosscheckResult
    effect_problems: list[str] = field(default_factory=list)
    popular_changed: bool = False                               # top community builds differ from last check
    popular_top: list[str] = field(default_factory=list)       # "points 0/29/22 (172 saves)" per top build
    retest: list[str] = field(default_factory=list)             # assumptions a patch change flags for retest

    def text(self) -> str:
        """Short chat-ready summary of the check."""
        if self.previous_build is None:
            first = self.changed and not self.changes
            lines = [f"Build {self.build}" + (" (first saved dataset)" if first else "")]
        else:
            lines = [f"Build {self.build} (previous {self.previous_build})"]
        if self.changed:
            lines += [f"- {change}" for change in self.changes[:MAX_LISTED_CHANGES]]
            if len(self.changes) > MAX_LISTED_CHANGES:
                lines.append(f"- and {len(self.changes) - MAX_LISTED_CHANGES} more")
        else:
            lines.append("No talent or spell changes.")
        if self.affected_builds:
            lines.append("Affected builds: " + ", ".join(self.affected_builds))
        lines.append(self.crosscheck.summary())
        if self.effect_problems:
            lines.append("Effect problems: " + "; ".join(self.effect_problems))
        if self.popular_top:
            state = "changed since last check" if self.popular_changed else "unchanged"
            lines.append(f"Popular community builds ({state}): " + "; ".join(self.popular_top))
        if self.retest:
            lines.append("Retest in game: " + ", ".join(self.retest))
        return "\n".join(lines)


def merge_class(dataset: Dataset, cls: ClassData, provenance: tuple[Provenance, ...]) -> Dataset:
    """`dataset` with `cls` added, or replacing the class of the same name, and `provenance`
    appended without duplicates."""
    classes = [c for c in dataset.classes if c.class_name != cls.class_name]
    index = next((i for i, c in enumerate(dataset.classes) if c.class_name == cls.class_name), len(classes))
    classes.insert(index, cls)
    merged = tuple(dict.fromkeys(dataset.provenance + tuple(provenance)))
    return dataclasses.replace(dataset, classes=tuple(classes), provenance=merged)


def check_for_updates(
    http_get: Callable[[str], str],
    *,
    data_dir: Path,
    delay: float = 1.0,
    now: str | None = None,
    class_name: str = "mage",
    table_http_get: Callable[[str], str] | None = None,
) -> UpdateSummary:
    """Fetch both sources, normalize `class_name`, and diff it against the last dataset.

    Saves a new dataset and changelog entry when anything changed, then records the
    check in `data_dir/builds.json`. `now` (ISO 8601, defaults to current UTC) is used
    for every timestamp.
    """
    if now is None:
        now = datetime.now(timezone.utc).isoformat()

    build = wago.latest_build(json.loads(http_get(WAGO_BUILDS_URL)))
    # table CSVs aren't in wago.tools' published API: they come from the cache, saved by hand
    # (wago.MissingTables says which); only tests pass a table_http_get
    manifest_path = wago.fetch_build(
        build,
        http_get=table_http_get,
        cache_dir=data_dir / "cache" / "wago",
        manifest_dir=data_dir / "raw" / "wago",
        delay=delay,
    )
    module = class_module(class_name)
    page_path, page = wowforevertalent.fetch(
        class_name, http_get=http_get, raw_dir=data_dir / "raw" / "wowforevertalent"
    )

    tables = normalize_module.read_tables(data_dir / "cache" / "wago" / build)
    cls, report = normalize_module.normalize_class(tables, module.LAYOUT, page, wago_build=build,
                                                   icon_overrides=getattr(module, "ICON_OVERRIDES", None))
    cls, effect_problems = effects_module.attach_effects(cls, module.TALENT_EFFECTS, module.UNMODELED)
    cls = dataclasses.replace(
        cls, spells=normalize_spells_module.class_spells(tables, skill_lines=module.SKILL_LINES)
    )

    wft_manifest = wowforevertalent.manifest_for(page_path)
    dataset = Dataset(
        version=build,
        game_build=build,
        classes=(cls,),
        provenance=(
            Provenance(
                source="wago.tools",
                game_build=build,
                data_version=build,
                fetched_at=now,
                snapshot_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            ),
            Provenance(
                source=wowforevertalent.SOURCE,
                game_build=page.game_build,
                data_version=page.page_data_version,
                fetched_at=now,
                snapshot_sha256=wft_manifest["sha256"],
            ),
        ),
    )
    dataset.validate()

    datasets_dir = data_dir / "datasets"
    current_path = datasets_dir / f"{build}.json"
    older_path = _previous_dataset(datasets_dir, build)
    previous_build = Dataset.load(older_path).version if older_path is not None else None
    # re-checking a build already saved compares against that dataset (a source may have
    # changed under the same game build); otherwise against the newest older build
    baseline_path = current_path if current_path.exists() else older_path
    baseline_ds = Dataset.load(baseline_path) if baseline_path is not None else None
    if baseline_ds is None:
        changes: list[Change] = []
    elif class_name not in {c.class_name for c in baseline_ds.classes}:
        changes = [Change(scope=class_name, talent="(class)", kind="added", text="class added")]
    else:
        baseline = baseline_ds.class_data(class_name)
        changes = (
            revisions_module.diff_class(baseline, cls)
            + revisions_module.diff_spells(baseline.spells, cls.spells)
        )
    changed = baseline_path is None or bool(changes)

    dataset_rel: str | None = f"datasets/{build}.json" if current_path.exists() else None
    if changed:
        dataset_rel = f"datasets/{build}.json"
        if baseline_ds is not None:
            # keep the other classes: those saved for this build, or carried over unchanged
            base = dataclasses.replace(baseline_ds, version=build, game_build=build)
            dataset = merge_class(base, cls, dataset.provenance)
            dataset.validate()
        dataset.save(current_path)
        revisions_module.append_changelog(data_dir / "CHANGELOG.md", build, changes, date=now[:10])

    affected = revisions_module.affected_builds(changes, builds_module.load_builds(class_name=class_name))
    result = crosscheck_module.crosscheck(cls, page, report, wago_build=build)

    # community popularity data rides along in the wowforevertalent.com snapshot
    popular = wowforevertalent.popular_builds(page)
    popular_path = data_dir / "popularity" / f"{page.class_id}.json"
    previous_popular = (json.loads(popular_path.read_text(encoding="utf-8"))["top"]
                        if popular_path.exists() else None)
    popular_changed = previous_popular is not None and [b["final"] for b in previous_popular] != [
        b["final"] for b in popular]
    if popular:
        popular_path.parent.mkdir(parents=True, exist_ok=True)
        meta = {k: page.popular.get(k) for k in ("sourceWindow", "sourceUpdatedAt", "counts", "spec")}
        popular_path.write_text(json.dumps({**meta, "top": popular}, indent=1, sort_keys=True),
                                encoding="utf-8", newline="\n")
    popular_top = [f"points {'/'.join(map(str, b['points']))} ({b['saved']} saves)" for b in popular]
    revisions_module.record_check(
        data_dir / "builds.json", build, changed=changed, dataset=dataset_rel, checked_at=now
    )
    return UpdateSummary(
        build=build,
        previous_build=previous_build,
        changed=changed,
        changes=changes,
        affected_builds=affected,
        crosscheck=result,
        effect_problems=effect_problems,
        popular_changed=popular_changed,
        popular_top=popular_top,
        retest=retest_names(Assumptions.load(), changes),
    )
