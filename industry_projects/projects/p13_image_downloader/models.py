"""Data models for Parallel Image Downloader."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DownloadTask:
    """Represents an individual image URL to be retrieved."""

    url: str
    custom_filename: str | None = None


@dataclass(frozen=True)
class DownloadResult:
    """Detailed outcome of a single image download attempt."""

    url: str
    filename: str
    success: bool
    bytes_downloaded: int
    sha256_hash: str | None
    error: str | None
    duration_seconds: float


@dataclass(frozen=True)
class BatchSummary:
    """Aggregate statistics for a concurrent download batch."""

    total_tasks: int
    successful_count: int
    failed_count: int
    total_bytes: int
    total_duration_seconds: float
    results: list[DownloadResult] = field(default_factory=list)
