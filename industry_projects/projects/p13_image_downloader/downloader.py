"""Concurrent image downloader engine with streaming SHA-256 verification and size limits."""

import hashlib
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from projects.p13_image_downloader.models import (
    BatchSummary,
    DownloadResult,
    DownloadTask,
)

DEFAULT_MAX_SIZE_BYTES = 50 * 1024 * 1024
DEFAULT_CHUNK_SIZE = 65536
USER_AGENT = "Mozilla/5.0 (compatible; AntigravityImageDownloader/1.0)"


def sanitize_filename(url: str, custom_name: str | None = None) -> str:
    """Derives a secure filename, preventing directory traversal and path injections."""
    if custom_name and custom_name.strip():
        candidate = custom_name.strip()
    else:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        candidate = os.path.basename(path)

    clean = re.sub(r'[\/\\:\*\?"<>\|\0]', "_", candidate)
    clean = clean.replace("..", "_").strip(" ._")

    if not clean:
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        clean = f"image_{url_hash}.jpg"

    if "." not in clean:
        clean += ".jpg"

    return clean


def download_single_image(
    task: DownloadTask,
    destination_dir: Path,
    max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES,
    timeout_seconds: float = 15.0,
) -> DownloadResult:
    """Streams an individual image from URL, calculating SHA-256 and enforcing size caps."""
    start_time = time.perf_counter()
    destination_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(task.url, task.custom_filename)
    target_path = destination_dir / filename
    temp_path = destination_dir / f"{filename}.part"

    parsed = urllib.parse.urlparse(task.url)
    if parsed.scheme.lower() not in ("http", "https"):
        elapsed = time.perf_counter() - start_time
        return DownloadResult(
            url=task.url,
            filename=filename,
            success=False,
            bytes_downloaded=0,
            sha256_hash=None,
            error=f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.",
            duration_seconds=round(elapsed, 3),
        )

    req = urllib.request.Request(task.url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    length_val = int(content_length)
                    if length_val > max_size_bytes:
                        elapsed = time.perf_counter() - start_time
                        return DownloadResult(
                            url=task.url,
                            filename=filename,
                            success=False,
                            bytes_downloaded=0,
                            sha256_hash=None,
                            error=(
                                f"Remote file exceeds size cap "
                                f"({length_val} > {max_size_bytes} bytes)."
                            ),
                            duration_seconds=round(elapsed, 3),
                        )
                except ValueError:
                    pass

            hasher = hashlib.sha256()
            bytes_received = 0

            with open(temp_path, "wb") as f_out:
                while True:
                    chunk = response.read(DEFAULT_CHUNK_SIZE)
                    if not chunk:
                        break

                    bytes_received += len(chunk)
                    if bytes_received > max_size_bytes:
                        temp_path.unlink(missing_ok=True)
                        elapsed = time.perf_counter() - start_time
                        return DownloadResult(
                            url=task.url,
                            filename=filename,
                            success=False,
                            bytes_downloaded=bytes_received,
                            sha256_hash=None,
                            error=(
                                f"Download exceeded maximum safety cap of {max_size_bytes} bytes."
                            ),
                            duration_seconds=round(elapsed, 3),
                        )

                    hasher.update(chunk)
                    f_out.write(chunk)

            os.replace(temp_path, target_path)
            elapsed = time.perf_counter() - start_time

            return DownloadResult(
                url=task.url,
                filename=filename,
                success=True,
                bytes_downloaded=bytes_received,
                sha256_hash=hasher.hexdigest(),
                error=None,
                duration_seconds=round(elapsed, 3),
            )

    except urllib.error.HTTPError as e:
        temp_path.unlink(missing_ok=True)
        elapsed = time.perf_counter() - start_time
        return DownloadResult(
            url=task.url,
            filename=filename,
            success=False,
            bytes_downloaded=0,
            sha256_hash=None,
            error=f"HTTP Error {e.code}: {e.reason}",
            duration_seconds=round(elapsed, 3),
        )
    except urllib.error.URLError as e:
        temp_path.unlink(missing_ok=True)
        elapsed = time.perf_counter() - start_time
        return DownloadResult(
            url=task.url,
            filename=filename,
            success=False,
            bytes_downloaded=0,
            sha256_hash=None,
            error=f"Network URL Error: {e.reason}",
            duration_seconds=round(elapsed, 3),
        )
    except (OSError, TimeoutError) as e:
        temp_path.unlink(missing_ok=True)
        elapsed = time.perf_counter() - start_time
        return DownloadResult(
            url=task.url,
            filename=filename,
            success=False,
            bytes_downloaded=0,
            sha256_hash=None,
            error=f"I/O or Timeout Error: {e}",
            duration_seconds=round(elapsed, 3),
        )


def download_batch(
    tasks: list[DownloadTask],
    destination_dir: Path,
    max_workers: int = 4,
    max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES,
    timeout_seconds: float = 15.0,
) -> BatchSummary:
    """Executes multiple image download tasks in parallel using a thread pool."""
    start_time = time.perf_counter()
    results: list[DownloadResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                download_single_image,
                task,
                destination_dir,
                max_size_bytes,
                timeout_seconds,
            ): task
            for task in tasks
        }

        for future in as_completed(future_map):
            res = future.result()
            results.append(res)

    total_duration = time.perf_counter() - start_time
    success_count = sum(1 for r in results if r.success)
    failed_count = sum(1 for r in results if not r.success)
    total_bytes = sum(r.bytes_downloaded for r in results if r.success)

    return BatchSummary(
        total_tasks=len(tasks),
        successful_count=success_count,
        failed_count=failed_count,
        total_bytes=total_bytes,
        total_duration_seconds=round(total_duration, 3),
        results=results,
    )
