"""Tests for Project 12: Website Blocker."""

from pathlib import Path
from unittest.mock import patch

import pytest

from projects.p12_website_blocker.cli import run_cli
from projects.p12_website_blocker.service import (
    SECTION_END,
    SECTION_START,
    InvalidDomainError,
    WebsiteBlockerService,
    validate_domain,
)


@pytest.fixture
def mock_hosts_env(tmp_path: Path) -> tuple[WebsiteBlockerService, Path, Path]:
    hosts_file = tmp_path / "hosts"
    backup_dir = tmp_path / "backups"

    initial_content = (
        "##\n"
        "# Host Database\n"
        "# localhost is used to configure loopback interface\n"
        "127.0.0.1       localhost\n"
        "255.255.255.255 broadcasthost\n"
        "::1             localhost\n"
        "192.168.1.50    my-printer.local\n"
    )
    hosts_file.write_text(initial_content, encoding="utf-8")

    service = WebsiteBlockerService(hosts_path=hosts_file, backup_dir=backup_dir)
    return service, hosts_file, backup_dir


def test_domain_validation_rules() -> None:
    # Valid domains
    assert validate_domain("example.com") == "example.com"
    assert validate_domain("SUB.DOMAIN.CO.UK  ") == "sub.domain.co.uk"
    assert validate_domain("reddit.com") == "reddit.com"

    # Rejection of schemes
    with pytest.raises(InvalidDomainError, match="URL scheme"):
        validate_domain("https://example.com")

    with pytest.raises(InvalidDomainError, match="URL scheme"):
        validate_domain("http://reddit.com")

    # Rejection of paths
    with pytest.raises(InvalidDomainError, match="URL paths"):
        validate_domain("example.com/feed")

    # Rejection of ports
    with pytest.raises(InvalidDomainError, match="Port numbers"):
        validate_domain("example.com:8080")

    # Rejection of raw IP addresses
    with pytest.raises(InvalidDomainError, match="Raw IP addresses"):
        validate_domain("192.168.1.1")


def test_dry_run_leaves_file_untouched(
    mock_hosts_env: tuple[WebsiteBlockerService, Path, Path],
) -> None:
    service, hosts_file, _ = mock_hosts_env
    content_before = hosts_file.read_text(encoding="utf-8")

    # Perform dry run
    result = service.block_domains(["distraction.com"], dry_run=True)
    assert result.is_dry_run is True
    assert result.modified is False
    assert result.backup_path is None

    # Verify hosts file content is identical
    content_after = hosts_file.read_text(encoding="utf-8")
    assert content_before == content_after


def test_block_domains_creates_backup_and_bounded_section(
    mock_hosts_env: tuple[WebsiteBlockerService, Path, Path],
) -> None:
    service, hosts_file, backup_dir = mock_hosts_env

    # Apply block
    result = service.block_domains(["facebook.com"], dry_run=False)
    assert result.is_dry_run is False
    assert result.modified is True
    assert result.backup_path is not None
    assert result.backup_path.exists()
    assert len(list(backup_dir.glob("*.bak"))) == 1

    content = hosts_file.read_text(encoding="utf-8")

    # Verify original lines are preserved
    assert "192.168.1.50    my-printer.local" in content

    # Verify bounded section is created
    assert SECTION_START in content
    assert SECTION_END in content
    assert "127.0.0.1 facebook.com" in content
    assert "127.0.0.1 www.facebook.com" in content

    # Verify getter returns the blocked domains
    blocked = service.get_blocked_domains()
    assert "facebook.com" in blocked
    assert "www.facebook.com" in blocked


def test_unblock_domains_and_unblock_all(
    mock_hosts_env: tuple[WebsiteBlockerService, Path, Path],
) -> None:
    service, hosts_file, _ = mock_hosts_env

    # Block two sites
    service.block_domains(["facebook.com", "twitter.com"], dry_run=False)
    assert len(service.get_blocked_domains()) == 4  # Includes www variants

    # Unblock facebook
    service.unblock_domains(["facebook.com"], dry_run=False)
    remaining = service.get_blocked_domains()
    assert "facebook.com" not in remaining
    assert "www.facebook.com" not in remaining
    assert "twitter.com" in remaining
    assert "www.twitter.com" in remaining

    # Unblock all
    clear_result = service.unblock_all(dry_run=False)
    assert clear_result.modified is True
    assert len(service.get_blocked_domains()) == 0

    content = hosts_file.read_text(encoding="utf-8")
    # Section should be removed completely
    assert SECTION_START not in content
    assert SECTION_END not in content
    # Original lines preserved
    assert "my-printer.local" in content


def test_backup_restoration(
    mock_hosts_env: tuple[WebsiteBlockerService, Path, Path],
) -> None:
    service, hosts_file, _ = mock_hosts_env
    original_text = hosts_file.read_text(encoding="utf-8")

    # Block site (which creates backup of original)
    result = service.block_domains(["youtube.com"], dry_run=False)
    assert result.backup_path is not None
    assert "youtube.com" in hosts_file.read_text(encoding="utf-8")

    # Restore from backup
    service.restore_backup(result.backup_path)
    assert hosts_file.read_text(encoding="utf-8") == original_text
    assert len(service.get_blocked_domains()) == 0


def test_cli_handles_eof_gracefully(
    mock_hosts_env: tuple[WebsiteBlockerService, Path, Path],
) -> None:
    service, _, _ = mock_hosts_env
    with patch("builtins.input", side_effect=EOFError):
        run_cli(service)
