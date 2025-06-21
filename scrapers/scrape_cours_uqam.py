#!/usr/bin/env python
# scrape_uqam_async.py
import asyncio, aiohttp, csv, os, re, string, sys
from pathlib import Path
from bs4 import BeautifulSoup

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
SIGLES_FILE       = Path("static/data/liste_cours.txt")
OUTPUT_CSV        = Path("static/data/raw_data_uqam.csv")
FLUSH_EVERY_ROWS  = 500               # write to disk every N parsed rows
CONCURRENCY       = 256                # simultaneous HTTP requests
TIMEOUT_SECONDS   = 15
SEMESTERS = [("groupes_wrapper20253", "automne2025"),
             ("groupes_wrapper20252", "ete2025")]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; async-scraper/1.0)"}
ASCII = string.ascii_uppercase

RE_HORAIRE_DEBUT_FIN = re.compile(r"De (?P<debut>.*?)\s+à\s+(?P<fin>.*)")

FIELDNAMES = ["Name", "Group Number", "Day", "Dates", "Start Time",
              "End Time", "Location", "Type", "Teacher"]

# --------------------------------------------------------------------------- #
# Networking
# --------------------------------------------------------------------------- #
async def fetch(session: aiohttp.ClientSession, sigle: str) -> tuple[str, str]:
    url = f"https://etudier.uqam.ca/cours?sigle={sigle}"
    try:
        async with session.get(url, timeout=TIMEOUT_SECONDS) as resp:
            resp.raise_for_status()
            return sigle, await resp.text()
    except Exception as exc:
        print(f"[WARN] {sigle}: {exc}", file=sys.stderr)
        return sigle, ""

# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def parse(html: str, sigle: str) -> list[dict]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []

    for div_id, semester in SEMESTERS:
        div = soup.find(id=div_id)
        if not div or "Ce cours n'est pas offert" in div.text:
            continue

        classes = div.find_all("div", class_="groupe")
        for idx, class_div in enumerate(classes):
            grp_letter = ASCII[idx] if idx < len(ASCII) else str(idx)
            name = f"{sigle}-{semester}-{grp_letter}"

            # Group number
            h3_grp = class_div.find("h3", class_="no_groupe") \
                     or class_div.find("h3", string=lambda t: "Groupe" in t)
            grp_no = h3_grp.text.split()[-1] if h3_grp else ""

            # Teacher
            h3_teacher = class_div.find("h3", string="Enseignant")
            teacher = h3_teacher.find_next("li").text.strip() if h3_teacher else ""

            # Schedule table
            h3_sched = class_div.find("h3", string="Horaire et lieu")
            table = h3_sched.find_next("table") if h3_sched else None
            if not table:
                continue

            for tr in table.select("tr")[1:]:
                tds = [td.get_text(strip=True).replace("\xa0", " ")
                       for td in tr.select("td")]
                if len(tds) < 5:
                    continue
                day, dates, time_range, location, _type = tds
                m = RE_HORAIRE_DEBUT_FIN.search(time_range)
                start, end = (m["debut"], m["fin"]) if m else ("", "")
                rows.append(
                    dict(Name=name, **{
                        "Group Number": grp_no, "Day": day, "Dates": dates,
                        "Start Time": start,   "End Time": end,
                        "Location": location,  "Type": _type,
                        "Teacher": teacher
                    })
                )
    return rows

# --------------------------------------------------------------------------- #
# CSV helpers
# --------------------------------------------------------------------------- #
def open_writer(path: Path, resume: bool):
    """Return (file_handle, csv_writer, already_written_rows)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if resume and path.exists():
        fh = path.open("r+", newline="", encoding="utf-8")
        existing = sum(1 for _ in fh) - 1  # header not counted
        fh.seek(0, os.SEEK_END)            # append mode
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
# Main driver
# --------------------------------------------------------------------------- #
async def main(resume: bool = True) -> None:
    sigles = [s.strip() for s in SIGLES_FILE.read_text().splitlines() if s.strip()]
    csv_file, writer, already_done = open_writer(OUTPUT_CSV, resume)
    processed = already_done
    if processed:
        print(f"[INFO] Resuming – {processed} rows already in {OUTPUT_CSV.name}")

    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:

        async def worker(sigle: str):
            async with sem:
                s, html = await fetch(session, sigle)
                return parse(html, s)

        tasks = [worker(s) for s in sigles]
        buffer: list[dict] = []

        for fut in asyncio.as_completed(tasks):
            try:
                rows = await fut
            except Exception as e:
                print(f"[ERROR] task failed: {e}", file=sys.stderr)
                continue
            buffer.extend(rows)
            processed += len(rows)
            print(f"\rProcessed rows: {processed}", end="")

            if len(buffer) >= FLUSH_EVERY_ROWS:
                writer.writerows(buffer)
                flush_to_disk(csv_file)
                buffer.clear()

        if buffer:
            writer.writerows(buffer)
            flush_to_disk(csv_file)

    csv_file.close()
    print(f"\nDone. CSV written to {OUTPUT_CSV.resolve()}")

if __name__ == "__main__":
    asyncio.run(main())
