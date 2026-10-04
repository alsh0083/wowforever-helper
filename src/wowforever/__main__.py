"""Command-line entry point: `python -m wowforever <command>`."""

import argparse

from wowforever import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wowforever")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_subparsers(dest="command")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
