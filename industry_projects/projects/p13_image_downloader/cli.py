"""Interactive Command-Line Interface for Concurrent Image Downloader."""

import datetime
import sys
from pathlib import Path

from common.input_helpers import UserExitException, prompt_int, safe_input
from common.tables import format_table
from projects.p13_image_downloader.downloader import (
    download_batch,
    download_single_image,
)
from projects.p13_image_downloader.models import (
    BatchSummary,
    DownloadResult,
    DownloadTask,
)

DEFAULT_DESTINATION = Path("downloads")


def format_bytes(size: int) -> str:
    """Formats raw byte counts into human-readable KB/MB strings."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"


def display_result(result: DownloadResult) -> None:
    """Prints a clear summary of an individual download result."""
    print("\n" + "=" * 50)
    if result.success:
        print(" [SUCCESS] Download Completed")
        print(f" URL:       {result.url}")
        print(f" Saved To:  {result.filename}")
        print(f" Size:      {format_bytes(result.bytes_downloaded)}")
        print(f" SHA-256:   {result.sha256_hash}")
        print(f" Duration:  {result.duration_seconds:.2f}s")
    else:
        print(" [FAILED] Download Error")
        print(f" URL:       {result.url}")
        print(f" Reason:    {result.error}")
        print(f" Duration:  {result.duration_seconds:.2f}s")
    print("=" * 50 + "\n")


def display_batch_summary(summary: BatchSummary) -> None:
    """Renders a clean tabular overview of a parallel download batch."""
    print("\n" + "=" * 65)
    print(" BATCH DOWNLOAD SUMMARY")
    print("=" * 65)
    print(f" Total Tasks:      {summary.total_tasks}")
    print(f" Successful:       {summary.successful_count}")
    print(f" Failed:           {summary.failed_count}")
    print(f" Total Downloaded: {format_bytes(summary.total_bytes)}")
    print(f" Total Duration:   {summary.total_duration_seconds:.2f}s")
    print("-" * 65)

    headers = ["Status", "Filename", "Size", "Duration", "Error / Hash (Prefix)"]
    rows = []
    for r in summary.results:
        status = "OK" if r.success else "FAIL"
        size_str = format_bytes(r.bytes_downloaded)
        duration_str = f"{r.duration_seconds:.2f}s"
        info = (
            r.sha256_hash[:16] + "..."
            if (r.sha256_hash and len(r.sha256_hash) > 16)
            else (r.error or "")
        )
        rows.append([status, r.filename, size_str, duration_str, info])

    print(format_table(headers, rows))
    print("=" * 65 + "\n")


def handle_single_download(destination: Path) -> None:
    """Prompts for a single URL and optional filename, then executes the download."""
    url = safe_input("Enter image URL: ").strip()
    if not url:
        print("No URL provided. Aborted.")
        return

    custom_name = safe_input(
        "Custom filename (leave blank for auto-detect): ", allow_empty=True
    ).strip()
    task = DownloadTask(url=url, custom_filename=custom_name or None)

    print(f"Downloading '{url}'...")
    res = download_single_image(task, destination)
    display_result(res)


def handle_batch_interactive(destination: Path) -> None:
    """Prompts for multiple URLs until an empty line is submitted, then downloads in parallel."""
    print("Enter URLs one per line (press Enter on empty line to begin download):")
    urls: list[str] = []
    while True:
        try:
            line = safe_input(f"URL [{len(urls) + 1}]: ", allow_empty=True).strip()
        except UserExitException:
            break
        if not line:
            break
        urls.append(line)

    if not urls:
        print("No URLs entered. Aborted.")
        return

    tasks = [DownloadTask(url=u) for u in urls]
    print(f"\nStarting parallel download of {len(tasks)} items...")
    summary = download_batch(tasks, destination)
    display_batch_summary(summary)


def handle_batch_file(destination: Path) -> None:
    """Reads a list of URLs from a local text file and downloads them concurrently."""
    path_str = safe_input("Enter path to text file containing URLs: ").strip()
    file_path = Path(path_str)
    if not file_path.is_file():
        print(f"Error: File '{file_path}' does not exist.")
        return

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Failed to read file: {e}")
        return

    urls = [line.strip() for line in content.splitlines() if line.strip()]
    if not urls:
        print("The file contains no URLs.")
        return

    tasks = [DownloadTask(url=u) for u in urls]
    print(f"\nStarting parallel download of {len(tasks)} URLs from '{file_path.name}'...")
    summary = download_batch(tasks, destination)
    display_batch_summary(summary)


def handle_view_downloads(destination: Path) -> None:
    """Lists existing downloaded files in the destination directory."""
    if not destination.exists():
        print(f"Destination folder '{destination}' does not exist yet.")
        return

    files = [f for f in destination.iterdir() if f.is_file()]
    if not files:
        print(f"Destination folder '{destination}' is empty.")
        return

    headers = ["Filename", "Size", "Modified"]
    rows = []
    for f in sorted(files, key=lambda x: x.name):
        stat = f.stat()
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.UTC).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        rows.append([f.name, format_bytes(stat.st_size), mtime])

    print(f"\nDownloads Directory: {destination.resolve()}")
    print(format_table(headers, rows))


def run_cli(destination_dir: Path | None = None) -> None:
    """Main REPL loop for Image Downloader."""
    dest = destination_dir or DEFAULT_DESTINATION
    print("\n=======================================================")
    print(" Welcome to Parallel Image Downloader")
    print(f" Target Folder: {dest}")
    print("=======================================================")

    menu_options = [
        "Download single image",
        "Download batch (interactive paste)",
        "Download batch from text file",
        "View downloaded files",
        "Exit",
    ]

    while True:
        print("\nActions:")
        for idx, opt in enumerate(menu_options, start=1):
            print(f"  {idx}. {opt}")

        try:
            choice = prompt_int("Select an action", min_val=1, max_val=len(menu_options))
        except (UserExitException, EOFError):
            print("\nExiting Image Downloader. Goodbye!")
            break

        if choice == 1:
            handle_single_download(dest)
        elif choice == 2:
            handle_batch_interactive(dest)
        elif choice == 3:
            handle_batch_file(dest)
        elif choice == 4:
            handle_view_downloads(dest)
        elif choice == 5:
            print("Goodbye!")
            break


def main() -> None:
    """Entry point when executed directly."""
    try:
        run_cli()
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")
        sys.exit(0)
