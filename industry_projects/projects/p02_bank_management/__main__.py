"""Main entry point for Project 02: Bank Management System.

================================================================================
Concepts used:
1. Module Execution: Allows running as a package with `python -m projects.p02_bank_management`.
2. Clean Delegation: Immediately hands off control to the CLI presentation layer.
================================================================================
"""

from projects.p02_bank_management.cli import run_cli

if __name__ == "__main__":
    run_cli()
