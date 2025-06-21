#!/usr/bin/env python
# scrape_programmes_async.py
#
# Reads programme-page URLs from liste_programmes.txt, extracts every
# data-sigle attribute, and appends them to raw_liste_cours.txt.
# Data are flushed to disk every BATCH_SIZE URLs so a crash only loses ≤ N URLs.
# The script is resumable: already-scraped URLs are skipped.

import asyncio, aiohttp, os, re, sys
from pathlib import Path
from typing import Dict, List
from bs4 import BeautifulSoup

# ─────────────────────────────────────────  configuration ────────────────── #
URLS_FILE        = Path("static/data/liste_programmes.txt")
OUTPUT_FILE      = Path("static/data/raw_liste_cours.txt")
BATCH_SIZE       = 256                # flush/commit every N URLs
CONCURRENCY      = 256                # simultaneous HTTP requests
TIMEOUT_SECONDS  = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; async-programme-scraper/1.0)"}

# ────────────────────────────────────  helpers / resume logic ────────────── #
def parsed_output() -> Dict[str, List[str]]:
    """
    Return dict {url: [sigle, …]} by reading the existing OUTPUT_FILE,
    or an empty dict if the file doesn't exist.
    """
    if not OUTPUT_FILE.exists():
        return {}
    data: Dict[str, List[str]] = {}
    with OUTPUT_FILE.open(encoding="utf-8") as f:
        for line in f:
            try:
                url, sigles_txt = line.rstrip("\n").split(":", 1)
                data[url.strip()] = eval(sigles_txt.strip())  # stored as Python list
            except ValueError:
                continue   # skip malformed lines
    return data

def flush(fh):
    fh.flush()
    os.fsync(fh.fileno())

# ──────────────────────────────────────────  network ─────────────────────── #
async def fetch(session: aiohttp.ClientSession, url: str) -> tuple[str, str]:
    try:
        async with session.get(url, timeout=TIMEOUT_SECONDS) as resp:
            resp.raise_for_status()
            return url, await resp.text()
    except Exception as e:
        print(f"[WARN] {url}: {e}", file=sys.stderr)
        return url, ""                     # empty html → no sigles

# ─────────────────────────────────────────  parser ───────────────────────── #
SIGLE_RE = re.compile(r"^[A-Z]{3}[0-9]{4}$")

def extract_sigles(html: str) -> List[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    sigles = [tag["data-sigle"] for tag in soup.find_all(attrs={"data-sigle": True})
              if SIGLE_RE.fullmatch(tag["data-sigle"])]
    return sorted(set(sigles))            # unique & deterministic order

# ─────────────────────────────────────────  main ─────────────────────────── #
async def main() -> None:
    already_done = parsed_output()        # {url: [sigle, …]}
    done_urls = set(already_done)
    print(f"[INFO] Resuming – {len(done_urls)} URL(s) already scraped")

    urls = [u.strip() for u in URLS_FILE.read_text().splitlines() if u.strip()]
    pending_urls = [u for u in urls if u not in done_urls]
    if not pending_urls:
        print("Everything already scraped.")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    # open in append-binary+utf8 so we can fsync on Windows too
    fh = open(OUTPUT_FILE, "a", encoding="utf-8")

    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:

        async def worker(u: str):
            async with sem:
                url, html = await fetch(session, u)
                return url, extract_sigles(html)

        tasks = [worker(u) for u in pending_urls]
        buffer: Dict[str, List[str]] = {}
        processed = 0

        for fut in asyncio.as_completed(tasks):
            url, sigles = await fut
            buffer[url] = sigles
            processed += 1
            print(f"\rProcessed URLs: {processed}/{len(pending_urls)}", end="")

            if len(buffer) >= BATCH_SIZE:
                for k, v in buffer.items():
                    fh.write(f"{k}: {v}\n")
                flush(fh)
                buffer.clear()

        # leftovers
        for k, v in buffer.items():
            fh.write(f"{k}: {v}\n")
        flush(fh)
        fh.close()

    print(f"\nDone. Data written to {OUTPUT_FILE.resolve()}")

# ─────────────────────────────────────────────────────────────────────────── #
if __name__ == "__main__":
    asyncio.run(main())
