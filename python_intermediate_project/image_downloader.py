"""13. Image Downloader - uses official image APIs (Openverse: no key; Pexels: free key), not Google scraping.
Saves CREDITS.txt with creator + licence for every image. Requires: pip install requests"""
import os
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

from common import AppError, guarded, launch, parse_number

UA = {"User-Agent": "ImageDownloader/1.0 (educational project)"}


def _requests():
    try:
        import requests
        return requests
    except ImportError:
        raise AppError("The 'requests' package is missing. Run: pip install requests")


def search_openverse(query, count):
    rq, found, page = _requests(), [], 1
    while len(found) < count:
        r = rq.get("https://api.openverse.org/v1/images/", headers=UA, timeout=20,
                   params={"q": query, "page": page, "page_size": min(20, count)})
        r.raise_for_status()
        items = r.json().get("results", [])
        if not items:
            break
        for it in items:
            found.append({"url": it["url"], "creator": it.get("creator") or "unknown",
                          "license": f"{it.get('license', '')} {it.get('license_version', '')}".strip(),
                          "page": it.get("foreign_landing_url", "")})
        page += 1
    return found[:count]


def search_pexels(query, count, key):
    if not key:
        raise AppError("Pexels needs an API key (free at pexels.com/api)")
    rq, found, page = _requests(), [], 1
    while len(found) < count:
        r = rq.get("https://api.pexels.com/v1/search", headers={**UA, "Authorization": key}, timeout=20,
                   params={"query": query, "page": page, "per_page": min(40, count)})
        if r.status_code == 401:
            raise AppError("Pexels rejected the API key")
        r.raise_for_status()
        items = r.json().get("photos", [])
        if not items:
            break
        found += [{"url": p["src"]["large"], "creator": p.get("photographer", "unknown"),
                   "license": "Pexels License", "page": p.get("url", "")} for p in items]
        page += 1
    return found[:count]


def download_all(items, folder, query, progress):
    rq = _requests()
    os.makedirs(folder, exist_ok=True)
    slug = re.sub(r"\W+", "_", query.lower()).strip("_") or "image"
    credits, ok = [], 0
    for i, it in enumerate(items, 1):
        ext = os.path.splitext(urlparse(it["url"]).path)[1].lower()
        ext = ext if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp") else ".jpg"
        name = f"{slug}_{i:03d}{ext}"
        try:
            r = rq.get(it["url"], headers=UA, timeout=30, stream=True)
            r.raise_for_status()
            if not r.headers.get("Content-Type", "").startswith("image"):
                raise ValueError("not an image")
            with open(os.path.join(folder, name), "wb") as fh:
                for chunk in r.iter_content(8192):
                    fh.write(chunk)
            credits.append(f"{name} | by {it['creator']} | {it['license']} | {it['page']}")
            ok += 1
            progress(i, len(items), f"saved {name}")
        except Exception as e:
            progress(i, len(items), f"skipped #{i}: {e}")
    with open(os.path.join(folder, "CREDITS.txt"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(credits) + "\n")
    return ok


class App:
    def __init__(self, root):
        self.root, self.q = root, queue.Queue()
        f = ttk.Frame(root, padding=10)
        f.pack(fill="both", expand=True)
        self.query = ttk.Entry(f, width=30)
        self.count = ttk.Spinbox(f, from_=1, to=100, width=6)
        self.count.set(10)
        self.source = ttk.Combobox(f, values=["Openverse (no key)", "Pexels (API key)"], state="readonly", width=20)
        self.source.current(0)
        self.key = ttk.Entry(f, width=30, show="*")
        self.folder = ttk.Entry(f, width=30)
        self.folder.insert(0, os.path.join(os.path.expanduser("~"), "Downloads", "images"))
        rows = (("Search for", self.query), ("How many", self.count), ("Source", self.source),
                ("Pexels key", self.key), ("Save to", self.folder))
        for i, (lab, w) in enumerate(rows):
            ttk.Label(f, text=lab).grid(row=i, column=0, sticky="e", padx=4, pady=3)
            w.grid(row=i, column=1, sticky="w", padx=4)
        ttk.Button(f, text="Browse", command=self.browse).grid(row=4, column=2)
        self.btn = ttk.Button(f, text="Download", command=self.start)
        self.btn.grid(row=5, column=1, sticky="w", pady=6)
        self.bar = ttk.Progressbar(f, length=420)
        self.bar.grid(row=6, column=0, columnspan=3, pady=4)
        self.log = tk.Text(f, height=12, width=70, state="disabled")
        self.log.grid(row=7, column=0, columnspan=3)

    def browse(self):
        d = filedialog.askdirectory()
        if d:
            self.folder.delete(0, "end")
            self.folder.insert(0, d)

    def write(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    @guarded
    def start(self):
        query = self.query.get().strip()
        if not query:
            raise AppError("Enter something to search for")
        n = parse_number(self.count.get(), "How many", int, 1)
        args = (query, n, self.source.get().startswith("Pexels"), self.key.get().strip(), self.folder.get().strip())
        self.btn.config(state="disabled")
        self.write(f"Searching for '{query}'...")
        threading.Thread(target=self.work, args=args, daemon=True).start()
        self.root.after(100, self.poll)

    def work(self, query, n, pexels, key, folder):  # runs in a worker thread: only touch self.q here
        try:
            items = search_pexels(query, n, key) if pexels else search_openverse(query, n)
            if not items:
                self.q.put(("done", "No images found."))
                return
            self.q.put(("log", f"Found {len(items)} images, downloading..."))
            ok = download_all(items, folder, query, lambda i, t, m: self.q.put(("progress", (i, t, m))))
            self.q.put(("done", f"Finished: {ok}/{len(items)} saved to {folder}"))
        except AppError as e:
            self.q.put(("done", f"Error: {e}"))
        except Exception as e:
            self.q.put(("done", f"Network/API error: {e}"))

    def poll(self):
        finished = False
        while not self.q.empty():
            kind, payload = self.q.get()
            if kind == "log":
                self.write(payload)
            elif kind == "progress":
                i, t, msg = payload
                self.bar.config(maximum=t, value=i)
                self.write(msg)
            else:
                self.write(payload)
                finished = True
        if finished:
            self.btn.config(state="normal")
        else:
            self.root.after(100, self.poll)


if __name__ == "__main__":
    launch(App, "Image Downloader", "640x560")
