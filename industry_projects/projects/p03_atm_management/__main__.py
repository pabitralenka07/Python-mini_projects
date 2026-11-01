"""Main entry point for Project 03: ATM Management System.

================================================================================
Concepts used:
1. Module Execution: Allows running as a package with `python -m projects.p03_atm_management`.
2. Cross-Module Reusability: Leverages underlying Bank management data and models.
================================================================================
"""

from projects.p03_atm_management.cli import run_cli

if __name__ == "__main__":
    run_cli()
