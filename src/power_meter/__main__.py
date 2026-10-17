import argparse
import sys
from pathlib import Path

from . import app, config


def main() -> None:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")  # Thai text in cmd/PowerShell

    parser = argparse.ArgumentParser(
        prog="power-meter", description="Track how much electricity your PC uses, in baht."
    )
    parser.add_argument(
        "-c", "--config", type=Path, default=Path("config.toml"), help="path to config.toml"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("run", help="start monitoring (default)")
    rep = sub.add_parser("report", help="show daily usage")
    rep.add_argument("-d", "--days", type=int, default=7)
    args = parser.parse_args()

    cfg = config.load(args.config)
    if args.command == "report":
        app.report(cfg, args.days)
    else:
        app.run(cfg)


if __name__ == "__main__":
    main()
