#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrapers/scrape_cours_uqam_async.py   –  parallel, asyncio + aiohttp
-------------------------------------------------------------------

1. Reads every sigle (course code) listed in
       static/data/liste_cours.txt
2. Fetches the corresponding course page
       https://etudier.uqam.ca/cours?sigle=ABC1234
   concurrently (aiohttp, configurable pool size).
3. Parses the HTML, extracts every offered group (semester, day, hour …).
4. Appends the result to
       static/data/raw_data_uqam.csv
   – ONE row per group, *no duplicates*.

This is a drop-in replacement for the previous synchronous scraper but
faster and following the same “coding style” as the parallel
scrape_programmes_uqam.py we prepared earlier.
"""
from __future__ import annotations

import asyncio
import csv
import os
import re
import string
import sys
from pathlib import Path
from typing import List

import aiohttp
from bs4 import BeautifulSoup                 # pip install beautifulsoup4
try:
    from tqdm import tqdm                     # pip install tqdm  (optional)
except ImportError:                           # stub if tqdm not available
    def tqdm(it, **kw):                       # noqa: D401
        return it

# --------------------------------------------------------------------------- #
#  Configuration                                                              #
# --------------------------------------------------------------------------- #
SIGLES_FILE       = Path("static/data/liste_cours.txt")
OUTPUT_CSV        = Path("static/data/raw_data_uqam.csv")

FLUSH_EVERY_ROWS  = 500           # write to disk every N parsed rows
DEFAULT_WORKERS   = 256           # simultaneous HTTP requests
TIMEOUT_SECONDS   = 15

# Override concurrency with   UQAM_ASYNC_WORKERS=128  python …
CONCURRENCY       = int(os.getenv("UQAM_ASYNC_WORKERS", DEFAULT_WORKERS))

SEMESTERS = [("groupes_wrapper20253", "automne2025"),
             ("groupes_wrapper20252", "ete2025")]

HEADERS  = {"User-Agent": "Mozilla/5.0 (compatible; uqam-async-scraper/2.0)"}

ASCII    = string.ascii_uppercase
RE_TIME  = re.compile(r"De (?P<debut>.*?)\s+à\s+(?P<fin>.*)")

FIELDNAMES = ["Name", "Group Number", "Day", "Dates",
              "Start Time", "End Time", "Location", "Type", "Teacher"]

# --------------------------------------------------------------------------- #
#  Networking                                                                 #
# --------------------------------------------------------------------------- #
async def fetch(session: aiohttp.ClientSession, sigle: str) -> tuple[str, str]:
    """Return (sigle, html) or (sigle, "") on error."""
    url = f"https://etudier.uqam.ca/cours?sigle={sigle}"
    try:
        async with session.get(url, timeout=TIMEOUT_SECONDS) as resp:
            resp.raise_for_status()
            return sigle, await resp.text()
    except Exception as exc:
        print(f"[WARN] {sigle}: {exc}", file=sys.stderr)
        return sigle, ""


# --------------------------------------------------------------------------- #
#  Parsing                                                                    #
# --------------------------------------------------------------------------- #
def parse(html: str, sigle: str) -> List[dict]:
    """Return a list of CSV rows extracted from one course page."""
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []

    for div_id, semester in SEMESTERS:
        div = soup.find(id=div_id)
        if not div or "Ce cours n'est pas offert" in div.text:
            continue

        for idx, class_div in enumerate(div.find_all("div", class_="groupe")):
            grp_letter = ASCII[idx] if idx < len(ASCII) else str(idx)
            name = f"{sigle}-{semester}-{grp_letter}"

            # group number
            h3_grp = (class_div.find("h3", class_="no_groupe")
                      or class_div.find("h3", string=lambda t: t and "Groupe" in t))
            grp_no = h3_grp.text.split()[-1] if h3_grp else ""

            # teacher
            h3_teacher = class_div.find("h3", string="Enseignant")
            teacher = h3_teacher.find_next("li").text.strip() if h3_teacher else ""

            # schedule table
            h3_sched = class_div.find("h3", string="Horaire et lieu")
            table = h3_sched.find_next("table") if h3_sched else None
            if not table:
                continue

            for tr in table.select("tr")[1:]:       # skip header row
                tds = [td.get_text(strip=True).replace("\xa0", " ")
                       for td in tr.select("td")]
                if len(tds) < 5:
                    continue
                day, dates, time_range, location, _type = tds
                m = RE_TIME.search(time_range)
                start, end = (m["debut"], m["fin"]) if m else ("", "")

                rows.append(dict(
                    Name=name,
                    **{"Group Number": grp_no, "Day": day, "Dates": dates,
                       "Start Time": start, "End Time": end,
                       "Location": location, "Type": _type,
                       "Teacher": teacher}
                ))
    return rows


# --------------------------------------------------------------------------- #
#  CSV helpers                                                                #
# --------------------------------------------------------------------------- #
def open_writer(path: Path, resume: bool):
    """Return (file_handle, csv_writer, already_existing_row_count)."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if resume and path.exists():
        fh = path.open("r+", newline="", encoding="utf-8")
        existing = sum(1 for _ in fh) - 1          # minus header
        fh.seek(0, os.SEEK_END)
        writer = csv.DictWriter(fh, FIELDNAMES)
        return fh, writer, existing

    fh = path.open("w", newline="", encoding="utf-8")
    writer = csv.DictWriter(fh, FIELDNAMES)
    writer.writeheader()
    return fh, writer, 0


def flush_to_disk(fh):
    fh.flush()
    os.fsync(fh.fileno())


# --------------------------------------------------------------------------- #
#  Main driver                                                                #
# --------------------------------------------------------------------------- #
async def main(resume: bool = True) -> None:
    if not SIGLES_FILE.exists():
        sys.exit(f"Sigle file not found: {SIGLES_FILE}")

    sigles = [s.strip() for s in SIGLES_FILE.read_text().splitlines() if s.strip()]
    total_sigles = len(sigles)
    if total_sigles == 0:
        sys.exit("Sigle file is empty – nothing to do.")

    csv_file, writer, already_done = open_writer(OUTPUT_CSV, resume)
    processed_rows = already_done
    if already_done:
        print(f"[INFO] Resuming – {already_done} rows already present in "
              f"{OUTPUT_CSV.name}")

    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:

        async def worker(one_sigle: str):
            async with sem:                             # bound concurrency
                s, html = await fetch(session, one_sigle)
                return parse(html, s)

        tasks = [asyncio.create_task(worker(s)) for s in sigles]

        buffer: list[dict] = []
        for fut in tqdm(asyncio.as_completed(tasks),
                        total=total_sigles,
                        desc="Scraping courses",
                        ncols=80):
            try:
                rows = await fut
            except Exception as exc:
                print(f"[ERROR] task failed: {exc}", file=sys.stderr)
                continue

            buffer.extend(rows)
            processed_rows += len(rows)

            if len(buffer) >= FLUSH_EVERY_ROWS:
                writer.writerows(buffer)
                flush_to_disk(csv_file)
                buffer.clear()

        # final flush
        if buffer:
            writer.writerows(buffer)
            flush_to_disk(csv_file)

    csv_file.close()
    print(f"\nWrote {processed_rows} rows to {OUTPUT_CSV.resolve()}")


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)