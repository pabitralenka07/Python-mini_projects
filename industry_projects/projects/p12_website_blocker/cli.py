"""CLI interface for Website Blocker."""

import os
from pathlib import Path

from common.input_helpers import (
    UserExitException,
    confirm_action,
    prompt_int,
    safe_input,
)
from common.tables import format_table
from projects.p12_website_blocker.service import (
    BlockerError,
    HostsAccessError,
    InvalidDomainError,
    WebsiteBlockerService,
)


def get_default_service() -> WebsiteBlockerService:
    # Uses system hosts file by default
    return WebsiteBlockerService()


def display_menu(service: WebsiteBlockerService) -> None:
    print("\n" + "=" * 54)
    print("            WEBSITE BLOCKER UTILITY                   ")
    print(f" Target Hosts: {service.hosts_path}")
    print("=" * 54)
    print(" 1. View Currently Blocked Domains")
    print(" 2. Block Websites (Dry-Run Preview -> Apply)")
    print(" 3. Unblock Specific Websites")
    print(" 4. Unblock All Websites (Clear Managed Block)")
    print(" 5. View Available Backups & Restore")
    print(" 0. Exit")
    print("=" * 54)


def view_blocked(service: WebsiteBlockerService) -> None:
    try:
        domains = service.get_blocked_domains()
        if not domains:
            print("\nNo websites are currently blocked in the managed block.")
            return

        headers = ["#", "Blocked Domain", "Redirect Destination"]
        rows = [[str(idx + 1), d, "127.0.0.1 (Localhost)"] for idx, d in enumerate(domains)]
        print("\n" + format_table(headers, rows))
    except HostsAccessError as e:
        print(f"[ERROR] {e}")


def block_websites(service: WebsiteBlockerService) -> None:
    try:
        prompt_msg = "Enter domain(s) to block (comma-separated, e.g. facebook.com, twitter.com): "
        raw_input = safe_input(prompt_msg)
        domains = [d.strip() for d in raw_input.split(",") if d.strip()]
        if not domains:
            print("No domains provided.")
            return

        # 1. Preview changes in Dry-Run mode
        preview = service.block_domains(domains, dry_run=True)
        print(f"\n{preview.message}")
        print("Candidate blocked list after this operation:")
        for d in preview.blocked_domains:
            print(f"  * 127.0.0.1 {d}")

        # 2. Confirm application
        if confirm_action("\nApply these changes to the hosts file?"):
            result = service.block_domains(domains, dry_run=False)
            print(f"[SUCCESS] {result.message}")
            if result.backup_path:
                print(f"[BACKUP] Created backup at: {result.backup_path}")
        else:
            print("Operation aborted. No changes made.")
    except (InvalidDomainError, HostsAccessError, BlockerError) as e:
        print(f"[ERROR] {e}")


def unblock_websites(service: WebsiteBlockerService) -> None:
    try:
        view_blocked(service)
        raw_input = safe_input("Enter domain(s) to unblock (comma-separated): ")
        domains = [d.strip() for d in raw_input.split(",") if d.strip()]
        if not domains:
            print("No domains provided.")
            return

        preview = service.unblock_domains(domains, dry_run=True)
        print(f"\n{preview.message}")

        if confirm_action("Confirm unblocking these domains?"):
            result = service.unblock_domains(domains, dry_run=False)
            print(f"[SUCCESS] {result.message}")
            if result.backup_path:
                print(f"[BACKUP] Created backup at: {result.backup_path}")
        else:
            print("Operation aborted.")
    except (InvalidDomainError, HostsAccessError, BlockerError) as e:
        print(f"[ERROR] {e}")


def unblock_all(service: WebsiteBlockerService) -> None:
    try:
        preview = service.unblock_all(dry_run=True)
        print(f"\n{preview.message}")

        warn_msg = "WARNING: This will unblock ALL websites in the managed block. Proceed?"
        if not confirm_action(warn_msg):
            print("Operation aborted.")
            return

        result = service.unblock_all(dry_run=False)
        print(f"[SUCCESS] {result.message}")
        if result.backup_path:
            print(f"[BACKUP] Created backup at: {result.backup_path}")
    except (HostsAccessError, BlockerError) as e:
        print(f"[ERROR] {e}")


def manage_backups(service: WebsiteBlockerService) -> None:
    try:
        if not service.backup_dir.exists():
            print("\nNo backup directory exists yet.")
            return

        backups = sorted(list(service.backup_dir.glob("*.bak")), reverse=True)
        if not backups:
            print("\nNo previous backups found.")
            return

        print("\nAvailable Hosts Backups:")
        for idx, b in enumerate(backups):
            size = b.stat().st_size
            print(f"  {idx + 1}. {b.name} ({size} bytes)")

        if confirm_action("\nWould you like to restore a backup?"):
            choice_idx = prompt_int("Enter backup number to restore (or 0 to cancel): ")
            if 1 <= choice_idx <= len(backups):
                target_backup = backups[choice_idx - 1]
                service.restore_backup(target_backup)
                print(f"[SUCCESS] Hosts file restored from '{target_backup.name}'.")
            else:
                print("Restore cancelled.")
    except Exception as e:
        print(f"[ERROR] {e}")


def run_cli(service: WebsiteBlockerService | None = None) -> None:
    svc = service if service is not None else get_default_service()

    # Inform user about root/admin requirements if targeting system hosts
    if svc.hosts_path == Path("/etc/hosts") and os.geteuid() != 0:
        print("\n[NOTE] You are running without root privileges.")
        print("Viewing blocked domains works, but modifying /etc/hosts requires 'sudo'.")
        print("Dry-run preview is fully functional.\n")

    while True:
        try:
            display_menu(svc)
            choice = safe_input("Enter choice (0-5): ").strip()
            if choice == "1":
                view_blocked(svc)
            elif choice == "2":
                block_websites(svc)
            elif choice == "3":
                unblock_websites(svc)
            elif choice == "4":
                unblock_all(svc)
            elif choice == "5":
                manage_backups(svc)
            elif choice == "0":
                print("Exiting Website Blocker. Stay focused!")
                break
            else:
                print("Invalid option. Please choose between 0 and 5.")
        except UserExitException:
            print("\nSession terminated. Goodbye!")
            break
        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break


if __name__ == "__main__":
    run_cli()
