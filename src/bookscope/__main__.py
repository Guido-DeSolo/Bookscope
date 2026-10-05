"""Launch Bookscope or generate a demo recording."""

import argparse
import sys
from importlib.resources import files
from pathlib import Path

from bookscope import __version__


def main():
    parser=argparse.ArgumentParser(prog="bookscope",description="Replay-first market microstructure workstation")
    sample=Path(__file__).resolve().parents[2]/"data/liquidity_shock.jsonl"
    if not sample.is_file(): sample=Path(str(files("bookscope").joinpath("data/liquidity_shock.jsonl")))
    parser.add_argument("recording",nargs="?",type=Path,default=sample)
    parser.add_argument("--version",action="version",version=f"Bookscope {__version__}")
    args=parser.parse_args()
    try:
        from PySide6.QtWidgets import QApplication

        from bookscope.ui.main_window import Workstation
    except ImportError as error:
        parser.exit(2,f"Bookscope desktop dependencies are missing: {error}\nInstall with: python -m pip install -e .\n")
    if not args.recording.is_file(): parser.error(f"recording not found: {args.recording}")
    app=QApplication(sys.argv[:1]); window=Workstation(args.recording); window.show()
    raise SystemExit(app.exec())


if __name__=="__main__": main()
