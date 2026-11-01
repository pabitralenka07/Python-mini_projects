"""Service layer for Website Blocker with domain validation, atomic replacement, and dry-run."""

import os
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from projects.p12_website_blocker.models import BlockerResult

SECTION_START = "# --- BEGIN ANTIGRAVITY MANAGED BLOCK ---"
SECTION_END = "# --- END ANTIGRAVITY MANAGED BLOCK ---"
REDIRECT_IP = "127.0.0.1"


class BlockerError(Exception):
    """Base exception for website blocker errors."""

    pass


class InvalidDomainError(BlockerError):
    """Raised when domain name is invalid or contains forbidden URI components."""

    pass


class HostsAccessError(BlockerError):
    """Raised when hosts file cannot be accessed or written."""

    pass


def validate_domain(domain: str) -> str:
    """Validates and sanitizes a bare domain name.

    Rejects schemes, paths, ports, or raw IP addresses.
    """
    clean = domain.strip().lower()

    if not clean:
        raise InvalidDomainError("Domain name cannot be empty.")

    if "://" in clean:
        raise InvalidDomainError(
            f"Invalid domain '{clean}': URL scheme (http:// or https://) is not allowed."
        )

    if "/" in clean or "\\" in clean:
        raise InvalidDomainError(
            f"Invalid domain '{clean}': URL paths are not allowed; provide a bare domain."
        )

    if ":" in clean:
        raise InvalidDomainError(f"Invalid domain '{clean}': Port numbers are not allowed.")

    # Check if raw IPv4
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", clean):
        raise InvalidDomainError(
            f"Invalid domain '{clean}': Raw IP addresses cannot be blocked as domain names."
        )

    # Validate standard domain pattern (e.g. example.com or sub.example.co.uk)
    domain_regex = r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
    if not re.match(domain_regex, clean):
        raise InvalidDomainError(
            f"Invalid domain format: '{clean}'. Must be a valid hostname (e.g. 'facebook.com')."
        )

    return clean


class WebsiteBlockerService:
    """Manages hosts file modifications safely with backups, atomic replacement, and dry-run."""

    def __init__(self, hosts_path: Path | None = None, backup_dir: Path | None = None) -> None:
        if hosts_path is not None:
            self.hosts_path = hosts_path
        else:
            # Default platform hosts location
            if os.name == "nt":
                self.hosts_path = Path(r"C:\Windows\System32\drivers\etc\hosts")
            else:
                self.hosts_path = Path("/etc/hosts")

        if backup_dir is not None:
            self.backup_dir = backup_dir
        else:
            self.backup_dir = Path(__file__).resolve().parent / "data" / "backups"

    def _read_hosts(self) -> tuple[list[str], set[str], list[str]]:
        """Parses hosts file into (before_lines, managed_domains, after_lines)."""
        if not self.hosts_path.exists():
            return [], set(), []

        try:
            with open(self.hosts_path, encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            raise HostsAccessError(f"Cannot read hosts file at '{self.hosts_path}': {e}") from e

        before_lines: list[str] = []
        managed_domains: set[str] = set()
        after_lines: list[str] = []

        inside_managed = False
        found_section = False

        for line in lines:
            stripped = line.strip()
            if stripped == SECTION_START:
                inside_managed = True
                found_section = True
                continue
            elif stripped == SECTION_END:
                inside_managed = False
                continue

            if inside_managed:
                parts = stripped.split()
                if len(parts) >= 2 and parts[0] == REDIRECT_IP:
                    managed_domains.add(parts[1])
            elif not found_section:
                before_lines.append(line)
            else:
                after_lines.append(line)

        return before_lines, managed_domains, after_lines

    def get_blocked_domains(self) -> list[str]:
        """Returns sorted list of currently blocked domains inside the managed section."""
        _, managed, _ = self._read_hosts()
        return sorted(list(managed))

    def _create_backup(self) -> Path:
        """Creates a timestamped backup of the current hosts file."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"hosts_backup_{timestamp}.bak"

        if self.hosts_path.exists():
            try:
                shutil.copy2(self.hosts_path, backup_file)
            except OSError as e:
                raise HostsAccessError(f"Failed to create backup at '{backup_file}': {e}") from e
        else:
            backup_file.touch()

        return backup_file

    def _write_hosts(
        self, before_lines: list[str], domains: set[str], after_lines: list[str]
    ) -> None:
        """Atomically writes new hosts content using a temporary file in the same directory."""
        # Ensure parent directory exists
        self.hosts_path.parent.mkdir(parents=True, exist_ok=True)

        new_lines: list[str] = list(before_lines)

        # Ensure newline before section if needed
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"

        if domains:
            new_lines.append(f"{SECTION_START}\n")
            for d in sorted(list(domains)):
                new_lines.append(f"{REDIRECT_IP} {d}\n")
            new_lines.append(f"{SECTION_END}\n")

        new_lines.extend(after_lines)

        # Atomic write with tempfile in same directory
        temp_fd, temp_path_str = tempfile.mkstemp(dir=self.hosts_path.parent, prefix="hosts_tmp_")
        temp_path = Path(temp_path_str)

        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
                f.flush()
                os.fsync(f.fileno())

            # Atomic replace
            os.replace(temp_path, self.hosts_path)
        except OSError as e:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise HostsAccessError(f"Failed writing to hosts file '{self.hosts_path}': {e}") from e

    def block_domains(self, domains: list[str], dry_run: bool = True) -> BlockerResult:
        """Blocks specified domains by redirecting to 127.0.0.1."""
        valid_domains: set[str] = set()
        for d in domains:
            cleaned = validate_domain(d)
            valid_domains.add(cleaned)
            # Also add www subdomain if not already present
            if not cleaned.startswith("www.") and cleaned.count(".") == 1:
                valid_domains.add(f"www.{cleaned}")

        before_lines, existing_domains, after_lines = self._read_hosts()
        updated_domains = existing_domains.union(valid_domains)

        if updated_domains == existing_domains:
            return BlockerResult(
                action="BLOCK",
                is_dry_run=dry_run,
                modified=False,
                blocked_domains=sorted(list(existing_domains)),
                backup_path=None,
                message="All specified domains are already blocked.",
            )

        if dry_run:
            diff_count = len(updated_domains) - len(existing_domains)
            return BlockerResult(
                action="BLOCK",
                is_dry_run=True,
                modified=False,
                blocked_domains=sorted(list(updated_domains)),
                backup_path=None,
                message=f"[DRY-RUN] Would block {diff_count} new domain(s). No changes written.",
            )

        backup = self._create_backup()
        self._write_hosts(before_lines, updated_domains, after_lines)

        return BlockerResult(
            action="BLOCK",
            is_dry_run=False,
            modified=True,
            blocked_domains=sorted(list(updated_domains)),
            backup_path=backup,
            message=f"Successfully blocked {len(valid_domains)} domain entries. Backup created.",
        )

    def unblock_domains(self, domains: list[str], dry_run: bool = True) -> BlockerResult:
        """Unblocks specified domains."""
        to_remove: set[str] = set()
        for d in domains:
            cleaned = validate_domain(d)
            to_remove.add(cleaned)
            if not cleaned.startswith("www.") and cleaned.count(".") == 1:
                to_remove.add(f"www.{cleaned}")

        before_lines, existing_domains, after_lines = self._read_hosts()
        updated_domains = existing_domains.difference(to_remove)

        if updated_domains == existing_domains:
            return BlockerResult(
                action="UNBLOCK",
                is_dry_run=dry_run,
                modified=False,
                blocked_domains=sorted(list(existing_domains)),
                backup_path=None,
                message="None of the specified domains were found in the blocked list.",
            )

        if dry_run:
            diff_count = len(existing_domains) - len(updated_domains)
            return BlockerResult(
                action="UNBLOCK",
                is_dry_run=True,
                modified=False,
                blocked_domains=sorted(list(updated_domains)),
                backup_path=None,
                message=f"[DRY-RUN] Would unblock {diff_count} domain(s). No changes written.",
            )

        backup = self._create_backup()
        self._write_hosts(before_lines, updated_domains, after_lines)

        return BlockerResult(
            action="UNBLOCK",
            is_dry_run=False,
            modified=True,
            blocked_domains=sorted(list(updated_domains)),
            backup_path=backup,
            message="Specified domains unblocked successfully. Backup created.",
        )

    def unblock_all(self, dry_run: bool = True) -> BlockerResult:
        """Removes the entire managed block and clears all blocked domains."""
        before_lines, existing_domains, after_lines = self._read_hosts()
        if not existing_domains:
            return BlockerResult(
                action="CLEAR",
                is_dry_run=dry_run,
                modified=False,
                blocked_domains=[],
                backup_path=None,
                message="No blocked domains present to clear.",
            )

        if dry_run:
            return BlockerResult(
                action="CLEAR",
                is_dry_run=True,
                modified=False,
                blocked_domains=[],
                backup_path=None,
                message=(
                    f"[DRY-RUN] Would clear all {len(existing_domains)} "
                    "blocked domains. No changes written."
                ),
            )

        backup = self._create_backup()
        self._write_hosts(before_lines, set(), after_lines)

        return BlockerResult(
            action="CLEAR",
            is_dry_run=False,
            modified=True,
            blocked_domains=[],
            backup_path=backup,
            message=f"Cleared all {len(existing_domains)} blocked domains. Backup created.",
        )

    def restore_backup(self, backup_file: Path) -> None:
        """Restores hosts file from an existing backup file."""
        if not backup_file.exists():
            raise HostsAccessError(f"Backup file '{backup_file}' does not exist.")

        try:
            shutil.copy2(backup_file, self.hosts_path)
        except OSError as e:
            raise HostsAccessError(f"Failed to restore backup from '{backup_file}': {e}") from e
