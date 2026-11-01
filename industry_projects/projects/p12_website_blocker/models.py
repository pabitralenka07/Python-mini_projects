"""Data models for Website Blocker."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BlockRule:
    """Represents a domain blocking rule redirected to localhost."""

    domain: str
    redirect_ip: str = "127.0.0.1"


@dataclass(frozen=True)
class BlockerResult:
    """Result summary of a website blocker operation."""

    action: str  # "BLOCK", "UNBLOCK", "CLEAR", "RESTORE"
    is_dry_run: bool
    modified: bool
    blocked_domains: list[str]
    backup_path: Path | None
    message: str
