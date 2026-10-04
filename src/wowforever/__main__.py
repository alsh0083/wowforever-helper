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
    if args.command is None:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
