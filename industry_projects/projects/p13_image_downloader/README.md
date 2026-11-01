# Project 13: Parallel Image Downloader

A robust, concurrent HTTP/HTTPS image downloader demonstrating parallel threading with `concurrent.futures`, streaming chunked I/O with live SHA-256 checksum verification, directory traversal defense, and hard size limit enforcement.

---

## 1. Architecture & Design

The project uses a clean layered design separating data structures, networking/streaming logic, and interactive user presentation:

```
projects/p13_image_downloader/
├── __init__.py          # Package initialization
├── __main__.py          # Direct runner: python -m projects.p13_image_downloader
├── models.py            # Dataclasses: DownloadTask, DownloadResult, BatchSummary
├── downloader.py        # Core engine: sanitize_filename, download_single_image, download_batch
├── cli.py               # Interactive REPL: single, interactive paste, file-based batch
└── README.md            # Documentation and practice exercises
```

### Concurrency Model
The downloader utilizes Python's standard library `concurrent.futures.ThreadPoolExecutor`:
- Worker threads asynchronously stream distinct HTTP/HTTPS requests.
- As each download completes, `as_completed` collects the result immediately, keeping memory usage constant and providing timely status updates.
- Number of concurrent workers is configurable (defaults to 4).

---

## 2. Security & Reliability Highlights

1. **Path Traversal Protection (`sanitize_filename`)**:
   - URL basenames often contain dangerous characters (`../`, `:`, `?`, `*`, `\0`).
   - We strip all directory separators and control characters, replacing invalid tokens with underscores and guaranteeing safe output filenames inside destination directories.
2. **Hard File Size Limits (Zip/Image Bomb Defense)**:
   - Remote files are inspected via `Content-Length` headers before streaming begins.
   - During streaming, incoming chunk byte counters enforce `DEFAULT_MAX_SIZE_BYTES` (50 MB). If exceeded, streaming aborts instantly and partial files are unlinked.
3. **Atomic File Creation (`.part` Temporary Files)**:
   - Data streams into `<filename>.part`. Only upon complete, verified transfer is `os.replace` invoked, guaranteeing that corrupt or interrupted downloads never leave incomplete files in the target directory.
4. **Streaming SHA-256 Checksum Calculation**:
   - Rather than buffering entire multi-megabyte payloads in RAM, each 64 KB chunk updates a `hashlib.sha256()` hasher on the fly.
5. **Scheme Enforcement**:
   - Only `http` and `https` schemes are allowed, blocking unsafe schemes like `file://` or `ftp://`.

---

## 3. Common Pitfalls & How We Solved Them

| Pitfall | Consequence | Our Solution |
| :--- | :--- | :--- |
| **Buffering entire file in memory** | Memory exhaustion or crashes when downloading large images | Stream 64 KB chunks directly to disk (`DEFAULT_CHUNK_SIZE = 65536`) |
| **Incomplete files on network failure** | Partial/corrupted images saved with final filename | Write to `.part` file and atomically rename via `os.replace` only on success |
| **Path Traversal in URL / Filename** | Writing files outside target directory (`../../evil.sh`) | `sanitize_filename` cleans slashes, dots, and traversal sequences |
| **Zip/Image Bomb DoS** | Endless stream filling host disk | `max_size_bytes` check on both `Content-Length` and running chunk byte total |
| **Default User-Agent blocks** | CDNs and servers returning 403 Forbidden to Python urllib | Explicit `User-Agent` header configured in requests |

---

## 4. Sample CLI Usage

### Running the Application
```bash
python -m projects.p13_image_downloader
```

### Interactive Session Example
```text
=======================================================
 Welcome to Parallel Image Downloader
 Target Folder: downloads
=======================================================

Select an action:
1. Download single image
2. Download batch (interactive paste)
3. Download batch from text file
4. View downloaded files
5. Exit

Enter choice (1-5): 1
Enter image URL: https://example.com/logo.png
Custom filename (leave blank for auto-detect): brand_logo.png
Downloading 'https://example.com/logo.png'...

==================================================
 [SUCCESS] Download Completed
 URL:       https://example.com/logo.png
 Saved To:  brand_logo.png
 Size:      142.5 KB
 SHA-256:   e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
 Duration:  0.42s
==================================================
```

---

## 5. Unsolved Practice Exercises for Learners

### Exercise 1: Automatic MIME Type & Extension Detection
**Objective**: Enhance `downloader.py` so that if a URL lacks a file extension (e.g. `https://picsum.photos/400/300`), the downloader inspects the HTTP response header `Content-Type` (e.g., `image/jpeg`, `image/png`, `image/webp`) and automatically appends the correct extension instead of defaulting to `.jpg`.

### Exercise 2: Download Resumption (HTTP Range Requests)
**Objective**: Implement partial content resumption using HTTP `Range: bytes=start-end` headers. If a `.part` file exists and matches the remote file's `ETag` or `Last-Modified` timestamp, resume streaming from the existing byte offset rather than restarting from zero.
