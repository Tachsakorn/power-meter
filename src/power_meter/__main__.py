import argparse
import sys
from pathlib import Path

from . import config, console


def _attach_console() -> None:
    """PowerMeter.exe has no console; borrow the terminal it was started from, if any."""
    import ctypes

    if ctypes.windll.kernel32.AttachConsole(-1):  # ATTACH_PARENT_PROCESS
        sys.stdout = open("CONOUT$", "w", encoding="utf-8")  # noqa: SIM115


def main() -> None:
    if sys.stdout is None and sys.platform == "win32" and len(sys.argv) > 1:
        _attach_console()
    if sys.stderr is None:
        # Started with pythonw (no console): keep crashes somewhere we can read them.
        log_dir = config.default_data_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        sys.stderr = open(log_dir / "error.log", "a", encoding="utf-8")  # noqa: SIM115
    if sys.platform == "win32" and sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8")  # Thai text in cmd/PowerShell

    parser = argparse.ArgumentParser(
        prog="power-meter", description="Track how much electricity your PC uses, in baht."
    )
    parser.add_argument(
        "-c", "--config", type=Path, default=Path("config.toml"), help="path to config.toml"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("app", help="open the desktop app (default)")
    sub.add_parser("run", help="monitor in the console")
    rep = sub.add_parser("report", help="show daily usage")
    rep.add_argument("-d", "--days", type=int, default=7)
    sub.add_parser("check", help="show detected hardware and take a few readings")
    args = parser.parse_args()

    cfg = config.load(args.config)
    if args.command == "report":
        console.report(cfg, args.days)
    elif args.command == "run":
        console.run(cfg)
    elif args.command == "check":
        console.check(cfg)
    else:
        from . import gui

        gui.run(cfg)


if __name__ == "__main__":
    main()
