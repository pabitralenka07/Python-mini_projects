# Project 12: Website Blocker

A productivity and security utility that demonstrates safe operating system file manipulation, parameter-driven path injection, dry-run safety previews, automatic backups, atomic file replacement, and bounded section parsing.

---

## 1. How It Works: DNS Redirection via Hosts

Operating systems consult the local `hosts` file (`/etc/hosts` on Unix/macOS, `C:\Windows\System32\drivers\etc\hosts` on Windows) before querying external DNS servers.

When a domain like `facebook.com` is mapped to `127.0.0.1` (loopback/localhost), your web browser attempts to connect to your own computer rather than Facebook's servers. Since no web server is running on that port, the connection fails immediately, blocking access and eliminating distractions.

---

## 2. Safety Architecture & Safeguards

Modifying system files can be dangerous if done naively. This utility implements **six defensive layers**:

1. **Parameter-Driven Path**: The `hosts_path` is injectable. Unit tests use temporary files in user space without requiring root or modifying the host machine.
2. **Dry-Run by Default**: All blocking and unblocking operations calculate changes in dry-run mode first, providing a clear preview before asking for confirmation.
3. **Bounded Section Delimiters**:
   ```text
   # --- BEGIN ANTIGRAVITY MANAGED BLOCK ---
   127.0.0.1 facebook.com
   127.0.0.1 www.facebook.com
   # --- END ANTIGRAVITY MANAGED BLOCK ---
   ```
   All edits occur strictly between these markers. Any existing custom host mappings outside this block are preserved verbatim.
4. **Automatic Timestamped Backups**: A copy of the hosts file is saved before every write in `data/backups/hosts_backup_<timestamp>.bak`.
5. **Atomic File Replacement**: Files are written to a temporary sibling file in the same directory, flushed with `os.fsync()`, and swapped into place with `os.replace()`, guaranteeing no corrupted half-written files if interrupted.
6. **Strict Domain Validation**: Rejects URL schemes (`http://`, `https://`), trailing paths (`/home`), ports (`:8080`), and raw IP addresses (`127.0.0.1`).

---

## 3. Platform DNS Cache Flushing

After modifying the hosts file, operating systems may continue serving cached DNS lookups for a few minutes. To clear your DNS cache immediately:

- **macOS**:
  ```bash
  sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
  ```
- **Windows (Command Prompt as Administrator)**:
  ```cmd
  ipconfig /flushdns
  ```
- **Linux (systemd)**:
  ```bash
  sudo systemd-resolve --flush-caches
  # or
  sudo resolvectl flush-caches
  ```

---

## 4. Sample CLI Session

```text
======================================================
            WEBSITE BLOCKER UTILITY                   
 Target Hosts: /etc/hosts
======================================================
 1. View Currently Blocked Domains
 2. Block Websites (Dry-Run Preview -> Apply)
 3. Unblock Specific Websites
 4. Unblock All Websites (Clear Managed Block)
 5. View Available Backups & Restore
 0. Exit
======================================================
Enter choice (0-5): 2
Enter domain(s) to block: twitter.com, reddit.com

[DRY-RUN] Would block 4 new domain(s). No changes written.
Candidate blocked list after this operation:
  * 127.0.0.1 reddit.com
  * 127.0.0.1 twitter.com
  * 127.0.0.1 www.reddit.com
  * 127.0.0.1 www.twitter.com

Apply these changes to the hosts file? (y/n): y
[SUCCESS] Successfully blocked 4 domain entries. Backup created.
[BACKUP] Created backup at: .../data/backups/hosts_backup_20261031_150000.bak
```

---

## 5. Unsolved Practice Exercises

1. **Exercise 1: Time-Scheduled Website Blocker (Focus Hours)**
   - Add a scheduler mode that automatically blocks distracting websites between 09:00 and 17:00 on weekdays, and unblocks them during evenings and weekends.
2. **Exercise 2: Category Blocklists Import**
   - Implement importing pre-defined blocklist files (e.g. `social_media.txt`, `gaming.txt`) and blocking all domains in batch.
