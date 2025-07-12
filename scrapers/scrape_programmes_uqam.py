#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrapers/scrape_programmes_uqam.py   – parallel edition
-------------------------------------------------------

1. Collects every “programme” URL listed on
       https://etudier.uqam.ca/programmes
2. Downloads those pages in parallel (thread pool).
3. Extracts every course sigle ABC1234 it can find.
4. Writes exactly ONE line per sigle to
       static/data/raw_liste_cours.txt

       https://etudier.uqam.ca/programme/1234  =>  ABC1234

The format is the one expected by the rest of your pipeline – no more
Python lists on the right-hand side.
"""
from __future__ import annotations

import concurrent.futures as cf
import os
import re
import sys
import time
from pathlib import Path
from typing import Iterable, Set, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup                # pip install beautifulsoup4
try:
    from tqdm import tqdm                    # pip install tqdm (optional)
except ImportError:                          # tiny stub if tqdm is absent
    def tqdm(it, **kw):                      # noqa: D401
        return it

# --------------------------------------------------------------------------- #
#  Configuration                                                              #
# --------------------------------------------------------------------------- #
BASE_DIR       = Path("static", "data")
RAW_COURS_FILE = BASE_DIR / "raw_liste_cours.txt"

ROOT_URL   = "https://etudier.uqam.ca"
INDEX_URL  = urljoin(ROOT_URL, "/programmes")

HEADERS    = {"User-Agent": "Mozilla/5.0 (compatible; uqam-scraper/2.0)"}
TIMEOUT    = 30                    # seconds
COURSE_RE  = re.compile(r"[A-Z]{3}[0-9]{4}")

# parallelism --------------------------------------------------------------- #
MAX_WORKERS = int(os.getenv("UQAM_SCRAPER_WORKERS", "8"))   # tweak as desired
SLEEP_BETWEEN = 0.1     # seconds – stay polite, even when in parallel
# --------------------------------------------------------------------------- #

# requests session shared by all threads
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# --------------------------------------------------------------------------- #
#  Helper functions                                                           #
# --------------------------------------------------------------------------- #
def get_html(url: str) -> str:
    """Download *url* and return its HTML text, raising for HTTP errors."""
    rsp = SESSION.get(url, timeout=TIMEOUT)
    rsp.raise_for_status()
    return rsp.text


def find_programme_urls() -> Set[str]:
    """
    Scrape the main “all programmes” page and return the set
    of absolute URLs to individual programme pages.
    """
    html = get_html(INDEX_URL)
    soup = BeautifulSoup(html, "html.parser")
    urls: set[str] = set()

    for a in soup.select("a[href*='/programme']"):
        href = a.get("href")
        if not href:
            continue
        urls.add(urljoin(ROOT_URL, href))

    print(f"Found {len(urls)} programme URLs on {INDEX_URL}")
    return urls


def extract_sigles(html: str) -> Set[str]:
    """Return every course code ABC1234 that appears in *html*."""
    return set(COURSE_RE.findall(html))


def scrape_single_programme(url: str) -> Tuple[str, Set[str]] | None:
    """
    Download *url*, extract sigles and return (url, sigle_set).
    Returns None on any exception (already logged).
    """
    try:
        html = get_html(url)
    except Exception as exc:
        print(f"[WARN] {url} … {exc}", file=sys.stderr)
        return None

    sigles = extract_sigles(html)
    if not sigles:
        print(f"[INFO] No course code found on {url}", file=sys.stderr)
    return (url, sigles)


# --------------------------------------------------------------------------- #
#  Main logic                                                                 #
# --------------------------------------------------------------------------- #
def main() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_COURS_FILE.exists():
        RAW_COURS_FILE.unlink()           # fresh start

    programme_urls = find_programme_urls()

    written = 0
    with RAW_COURS_FILE.open("w", encoding="utf-8") as fh:
        with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
            futures = [exe.submit(scrape_single_programme, url)
                       for url in programme_urls]

            for fut in tqdm(cf.as_completed(futures),
                            total=len(futures),
                            desc="Scraping programmes",
                            ncols=80):
                res = fut.result()
                if not res:
                    continue
                url, sigles = res
                for sigle in sorted(sigles):
                    fh.write(f"{url}  =>  {sigle}\n")
                    written += 1
                # even though we are parallel, throttle a tiny bit
                time.sleep(SLEEP_BETWEEN)

    print(f"\nWrote {written} lines to {RAW_COURS_FILE}")


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)