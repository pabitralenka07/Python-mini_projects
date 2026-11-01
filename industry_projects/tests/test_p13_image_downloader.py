"""Unit tests for Project 13: Parallel Image Downloader."""

import hashlib
import io
import urllib.error
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from projects.p13_image_downloader.cli import (
    format_bytes,
    handle_batch_file,
    handle_batch_interactive,
    handle_single_download,
    handle_view_downloads,
    run_cli,
)
from projects.p13_image_downloader.downloader import (
    download_batch,
    download_single_image,
    sanitize_filename,
)
from projects.p13_image_downloader.models import DownloadTask


class MockHTTPResponse:
    """Mock context manager for urllib.request.urlopen."""

    def __init__(
        self,
        data: bytes,
        headers: dict[str, str] | None = None,
        chunk_size: int = 65536,
    ) -> None:
        self.stream = io.BytesIO(data)
        self.headers = headers or {}
        self.chunk_size = chunk_size

    def read(self, amt: int = -1) -> bytes:
        return self.stream.read(amt)

    def __enter__(self) -> "MockHTTPResponse":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        pass


def test_sanitize_filename_standard() -> None:
    assert sanitize_filename("https://example.com/assets/banner.png") == "banner.png"
    assert sanitize_filename("https://example.com/photos/avatar.jpg?v=123") == "avatar.jpg"


def test_sanitize_filename_traversal() -> None:
    dirty = sanitize_filename("https://example.com/foo", custom_name="../../etc/passwd")
    assert ".." not in dirty
    assert "/" not in dirty
    assert "\\" not in dirty


def test_sanitize_filename_fallback() -> None:
    clean = sanitize_filename("https://example.com/")
    assert clean.startswith("image_")
    assert clean.endswith(".jpg")


def test_download_single_image_success(tmp_path: Path) -> None:
    test_data = b"Simulated image binary payload for testing"
    expected_hash = hashlib.sha256(test_data).hexdigest()

    mock_resp = MockHTTPResponse(test_data, headers={"Content-Length": str(len(test_data))})

    with patch("urllib.request.urlopen", return_value=mock_resp):
        task = DownloadTask(url="https://example.com/test.png", custom_filename="test.png")
        res = download_single_image(task, destination_dir=tmp_path)

        assert res.success is True
        assert res.bytes_downloaded == len(test_data)
        assert res.sha256_hash == expected_hash
        assert res.error is None
        assert (tmp_path / "test.png").is_file()
        assert (tmp_path / "test.png").read_bytes() == test_data
        assert not (tmp_path / "test.png.part").exists()


def test_download_single_image_unsupported_scheme(tmp_path: Path) -> None:
    task = DownloadTask(url="ftp://files.example.com/image.jpg")
    res = download_single_image(task, destination_dir=tmp_path)

    assert res.success is False
    assert "Unsupported URL scheme" in (res.error or "")
    assert res.bytes_downloaded == 0


def test_download_single_image_exceeds_content_length(tmp_path: Path) -> None:
    mock_resp = MockHTTPResponse(b"data", headers={"Content-Length": "100000000"})

    with patch("urllib.request.urlopen", return_value=mock_resp):
        task = DownloadTask(url="https://example.com/giant.jpg")
        res = download_single_image(task, destination_dir=tmp_path, max_size_bytes=1000)

        assert res.success is False
        assert "exceeds size cap" in (res.error or "")


def test_download_single_image_streaming_size_limit(tmp_path: Path) -> None:
    huge_data = b"X" * 2000
    mock_resp = MockHTTPResponse(huge_data, headers={})

    with patch("urllib.request.urlopen", return_value=mock_resp):
        task = DownloadTask(url="https://example.com/stream.jpg")
        res = download_single_image(task, destination_dir=tmp_path, max_size_bytes=500)

        assert res.success is False
        assert "exceeded maximum safety cap" in (res.error or "")
        assert not (tmp_path / "stream.jpg").exists()
        assert not (tmp_path / "stream.jpg.part").exists()


def test_download_single_image_http_error(tmp_path: Path) -> None:
    fake_hdrs = cast(Any, {})
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(
            url="https://example.com/404.jpg",
            code=404,
            msg="Not Found",
            hdrs=fake_hdrs,
            fp=None,
        ),
    ):
        task = DownloadTask(url="https://example.com/404.jpg")
        res = download_single_image(task, destination_dir=tmp_path)

        assert res.success is False
        assert "HTTP Error 404" in (res.error or "")


def test_download_batch(tmp_path: Path) -> None:
    test_data = b"Batch item content"

    tasks = [DownloadTask(url=f"https://example.com/pic_{i}.jpg") for i in range(3)]

    with patch(
        "urllib.request.urlopen",
        side_effect=lambda *a, **kw: MockHTTPResponse(test_data),
    ):
        summary = download_batch(tasks, destination_dir=tmp_path, max_workers=2)

        assert summary.total_tasks == 3
        assert summary.successful_count == 3
        assert summary.failed_count == 0
        assert summary.total_bytes == len(test_data) * 3
        assert len(summary.results) == 3


def test_cli_format_bytes() -> None:
    assert format_bytes(500) == "500 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(5 * 1024 * 1024) == "5.00 MB"


def test_cli_single_download(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_data = b"sample cli download data"
    mock_resp = MockHTTPResponse(test_data)

    inputs = iter(["https://example.com/cli_test.png", "my_cli_test.png"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    with patch("urllib.request.urlopen", return_value=mock_resp):
        handle_single_download(tmp_path)
        assert (tmp_path / "my_cli_test.png").is_file()


def test_cli_batch_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_data = b"sample batch file data"

    url_file = tmp_path / "urls.txt"
    url_file.write_text("https://example.com/1.png\nhttps://example.com/2.png\n")

    monkeypatch.setattr("builtins.input", lambda _: str(url_file))

    with patch(
        "urllib.request.urlopen",
        side_effect=lambda *a, **kw: MockHTTPResponse(test_data),
    ):
        handle_batch_file(tmp_path)
        assert (tmp_path / "1.png").is_file()
        assert (tmp_path / "2.png").is_file()


def test_cli_batch_interactive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_data = b"sample interactive batch data"
    inputs = iter(
        [
            "https://example.com/interactive1.png",
            "https://example.com/interactive2.png",
            "",  # empty line stops entry
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    with patch(
        "urllib.request.urlopen",
        side_effect=lambda *a, **kw: MockHTTPResponse(test_data),
    ):
        handle_batch_interactive(tmp_path)
        assert (tmp_path / "interactive1.png").is_file()
        assert (tmp_path / "interactive2.png").is_file()


def test_cli_view_downloads(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "image1.jpg").write_bytes(b"12345")
    handle_view_downloads(tmp_path)
    captured = capsys.readouterr()
    assert "image1.jpg" in captured.out
    assert "5 B" in captured.out


def test_cli_main_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    # Choice 5 exits
    monkeypatch.setattr("builtins.input", lambda _: "5")
    run_cli()
