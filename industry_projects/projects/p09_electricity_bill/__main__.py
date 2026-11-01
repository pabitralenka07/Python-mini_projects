"""Entry point for running Electricity Bill CLI via python -m."""

import sys

from projects.p09_electricity_bill.cli import run_cli
from projects.p09_electricity_bill.gui_app import run_gui

if __name__ == "__main__":
    if "--gui" in sys.argv:
        run_gui()
    else:
        run_cli()
