"""Command-line entry point: `python -m wowforever <command>`."""

import argparse

from wowforever import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wowforever")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    rep = sub.add_parser("report", help="score every build on a saved dataset and write the dashboard payload")
    rep.add_argument("--dataset", required=True, help="dataset JSON written by `update`")
    rep.add_argument("--out", default="data/report.json")
    rep.add_argument("--class", dest="class_name", default="mage", help="class to report (see classes.CLASSES)")
    dash = sub.add_parser("dashboard", help="render the offline dashboard page from a report payload")
    dash.add_argument("--report", action="append",
                      help="report JSON written by `report`; repeat for several classes (default: "
                           "data/report.json plus data/report-<class>.json files)")
    dash.add_argument("--out", default="dashboard/index.html")
    il = sub.add_parser("import-logs", help="summarize foreverlogs.gg API responses from browser HAR exports (#69)")
    il.add_argument("har", nargs="+", help="HAR files saved from the browser (keep them in data/cache/logs/)")
    il.add_argument("--out", default="data/logs/foreverlogs.json")
    gsrc = sub.add_parser("gear-sources", help="build data/items/gear.json: where gear drops, quest rewards and crafted items come from (#188)")
    gsrc.add_argument("--refresh", action="store_true", help="fetch wowforevertalent.com's items, dungeons and quests pages first")
    gsrc.add_argument("--tables", default="data/cache/wago/1.60.1.70205", help="folder with the cached client tables")
    sub.add_parser("validate-logs", help="compare the model's dungeon scores with cached Forever Logs statistics (#172)")
    gs = sub.add_parser("gear-stats", help="rebuild config/stats/<class>.csv from real Forever gear")
    gs.add_argument("--tables", required=True, help="folder with ItemSparse/Item/RandPropPoints CSVs")
    gs.add_argument("--class", dest="class_name", default="mage", choices=("mage", "rogue", "hunter", "warrior", "paladin", "priest", "warlock", "druid", "shaman",
                                     "druid_melee", "shaman_melee"))
    upd = sub.add_parser("update", help="fetch both sources, diff against the last saved dataset, record the check")
    upd.add_argument("--data-dir", default="data")
    upd.add_argument("--delay", type=float, default=1.0, help="seconds between table downloads")
    args = parser.parse_args(argv)
    if args.command == "report":
        import json
        from pathlib import Path

        from wowforever.report import report_from_dataset

        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report_from_dataset(args.dataset, args.class_name), indent=1), encoding="utf-8", newline="\n")
        print(f"wrote {out}")
        return 0
    if args.command == "dashboard":
        import json
        from pathlib import Path

        from wowforever.dashboard import fetch_icons, render
        from wowforever.sources.http import http_get_bytes

        from wowforever.classes import CLASSES

        found = {p.stem.removeprefix("report-"): str(p) for p in Path("data").glob("report-*.json")}
        paths = args.report or ["data/report.json", *(found[c] for c in CLASSES if c in found)]
        reports = [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]
        icons = fetch_icons(
            [talent["icon"] for report in reports for talent in report["talents"].values()]
            # each class's official icon for the page crest
            + [f"class_{report.get('class', 'mage')}" for report in reports],
            http_get_bytes=http_get_bytes,
            cache_dir=Path("data/cache/icons"),
        )
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(reports, icons), encoding="utf-8", newline="\n")
        print(f"wrote {out}")
        return 0
    if args.command == "gear-sources":
        from pathlib import Path

        from wowforever import gear_sources as gs
        from wowforever.normalize import read_tables
        from wowforever.sources.http import http_get

        cache = Path("data/cache/wft-gear")
        if args.refresh:
            gs.fetch_pages(cache, http_get)
        dataset = gs.build(gs.load_pages(cache), read_tables(Path(args.tables)), checked_at=gs.now())
        gs.write(dataset, Path("data/items/gear.json"))
        print("wrote data/items/gear.json:", gs.summary(dataset))
        return 0
    if args.command == "validate-logs":
        import json
        from pathlib import Path

        from wowforever.validate import compare, log_averages, markdown

        reports = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path("data").glob("report*.json"))]
        print(markdown(compare(reports, log_averages())))
        return 0
    if args.command == "import-logs":
        from pathlib import Path

        from wowforever.sources.foreverlogs import import_hars

        merged = import_hars([Path(p) for p in args.har], Path(args.out))
        print(f"wrote {args.out}: {len(merged)} encounter sets, "
              f"{sum(len(s['players']) for s in merged)} player rows")
        return 0
    if args.command == "gear-stats":
        import csv
        from dataclasses import asdict
        from pathlib import Path

        from wowforever.gear import gear_stat_table, load_items
        from wowforever.normalize import read_tables
        from wowforever.stats import CONFIG_DIR

        tables = read_tables(Path(args.tables))
        levels = (10, 20, 30, 40, 50, 60)
        if args.class_name not in ("mage",) and not _is_caster(args.class_name):
            from wowforever.melee_stats import melee_stat_table, write_melee_csv
            from wowforever.weapons import load_weapons

            out = CONFIG_DIR / f"{args.class_name}.csv"
            write_melee_csv(melee_stat_table(args.class_name, load_items(tables), load_weapons(tables), levels), out)
            print(f"wrote {out}")
            return 0
        if args.class_name == "mage":
            rows = gear_stat_table(load_items(tables), levels=levels)
        else:
            from wowforever.gear import caster_stat_table

            rows = caster_stat_table(args.class_name, load_items(tables), levels)
        out = CONFIG_DIR / f"{args.class_name}.csv"
        with out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, list(asdict(rows[0])), lineterminator="\n")
            writer.writeheader()
            writer.writerows({k: round(v, 2) if isinstance(v, float) else v for k, v in asdict(r).items()}
                             for r in rows)
        print(f"wrote {out}")
        return 0
    if args.command == "update":
        from pathlib import Path

        from wowforever import update

        from wowforever.classes import CLASSES

        from wowforever.sources.wago import MissingTables

        now = update.datetime.now(update.timezone.utc).isoformat()
        for class_name in CLASSES:
            try:
                summary = update.check_for_updates(
                    update.default_http_get, data_dir=Path(args.data_dir), delay=args.delay, now=now,
                    class_name=class_name,
                )
            except MissingTables as missing:
                print(missing)
                return 2
            print(f"[{class_name}]")
            print(summary.text())
        return 0
    if args.command is None:
        parser.print_help()
    return 0


def _is_caster(class_name: str) -> bool:
    """Classes scored by the caster spell engine (#163)."""
    from wowforever.classes import CLASSES, class_module

    return class_name in CLASSES and getattr(class_module(class_name), "ENGINE", None) == "spell"


if __name__ == "__main__":
    raise SystemExit(main())
