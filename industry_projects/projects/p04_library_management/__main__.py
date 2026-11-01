"""Main entry point for Project 04: Library Management System.

================================================================================
Concepts used:
1. Module Execution: Allows running as a package with `python -m projects.p04_library_management`.
2. Clean Delegation: Immediately hands off control to the CLI presentation layer.
================================================================================
"""

from projects.p04_library_management.cli import run_cli

if __name__ == "__main__":
    run_cli()
