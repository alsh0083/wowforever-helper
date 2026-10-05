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
    dash = sub.add_parser("dashboard", help="render the offline dashboard page from a report payload")
    dash.add_argument("--report", default="data/report.json", help="report JSON written by `report`")
    dash.add_argument("--out", default="dashboard/index.html")
    gs = sub.add_parser("gear-stats", help="rebuild config/stats/mage.csv from real Forever gear")
    gs.add_argument("--tables", required=True, help="folder with ItemSparse/Item/RandPropPoints CSVs")
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
        out.write_text(json.dumps(report_from_dataset(args.dataset), indent=1), encoding="utf-8", newline="\n")
        print(f"wrote {out}")
        return 0
    if args.command == "dashboard":
        import json
        from pathlib import Path

        from wowforever.dashboard import fetch_icons, render
        from wowforever.sources.http import http_get_bytes

        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        icons = fetch_icons(
            [talent["icon"] for talent in report["talents"].values()],
            http_get_bytes=http_get_bytes,
            cache_dir=Path("data/cache/icons"),
        )
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(report, icons), encoding="utf-8", newline="\n")
        print(f"wrote {out}")
        return 0
    if args.command == "gear-stats":
        import csv
        from dataclasses import asdict
        from pathlib import Path

        from wowforever.gear import gear_stat_table, load_items
        from wowforever.normalize import read_tables
        from wowforever.stats import CONFIG_DIR

        rows = gear_stat_table(load_items(read_tables(Path(args.tables))), levels=(10, 20, 30, 40, 50, 60))
        out = CONFIG_DIR / "mage.csv"
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

        summary = update.check_for_updates(
            update.default_http_get, data_dir=Path(args.data_dir), delay=args.delay
        )
        print(summary.text())
        return 0
    if args.command is None:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
