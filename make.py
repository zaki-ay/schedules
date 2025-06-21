import sys, os
import subprocess
from pathlib import Path
from shutil import which
import requests, re
from datetime import datetime

# --------------------------------------------------------------------------- #
#  Configuration – portable (works on Windows, macOS, Linux)
# --------------------------------------------------------------------------- #
PYTHON = sys.executable                          # use the current interpreter

# base folders
BASE_DIR     = Path("static", "data")
SCRAPERS_DIR = Path("scrapers")
SCRIPTS_DIR  = Path("scripts")

# individual files / scripts
SCRIPT_SCRAPE_PROGRAMMES = SCRAPERS_DIR / "scrape_programmes_uqam.py"
SCRIPT_SCRAPE_COURS      = SCRAPERS_DIR / "scrape_cours_uqam.py"
SCRIPT_CSV_TO_SQL        = SCRIPTS_DIR  / "convert_csv_to_sql.py"
SCRIPT_SIGLES_TO_JSON    = SCRIPTS_DIR  / "sigles_to_json.py"

RAW_COURS   = BASE_DIR / "raw_liste_cours.txt"
CLEAN_COURS = BASE_DIR / "liste_cours.txt"
RAW_DATA    = BASE_DIR / "raw_data_uqam.csv"
CLEAN_DATA  = BASE_DIR / "data_uqam.csv"
VAR_CONTENT = BASE_DIR / "contenu_variable.html"
DB_FILE     = BASE_DIR / "database.db"

APP = "app.py"

# --------------------------------------------------------------------------- #
#  Helper: choose powershell / pwsh
# --------------------------------------------------------------------------- #
def _detect_powershell() -> str:
    """Return the full path to powershell.exe or pwsh.exe, preferring pwsh."""
    for exe in ("pwsh", "powershell"):
        path = which(exe)
        if path:
            return path
    sys.exit("ERROR: neither 'pwsh' nor 'powershell' executable was found.")

POWERSHELL = _detect_powershell()

# --------------------------------------------------------------------------- #
#  Helper: run a command and stream its output live
# --------------------------------------------------------------------------- #
def run_cmd(cmd):
    """
    Run *cmd* (list/tuple or str).  Live-stream stdout/stderr and abort on error.
    • Path objects are accepted.
    • If *cmd* is a str we invoke the shell so redirections like “> file” work.
    """
    use_shell = isinstance(cmd, str)

    if not use_shell:                       
        cmd = [str(c) for c in cmd]
        printable = " ".join(cmd)
    else:
        printable = cmd

    print(f"Running: {printable}")

    proc = subprocess.Popen(
        cmd,
        shell=use_shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )

    for line in proc.stdout:
        print(line, end="")

    proc.wait()
    if proc.returncode:
        print(f"\nCommand failed with exit-code {proc.returncode}", file=sys.stderr)
        sys.exit(proc.returncode)

# --------------------------------------------------------------------------- #
#  PowerShell one-liners
# --------------------------------------------------------------------------- #

def ps_command(script: str):
    """
    Wrap a PowerShell script string so it can be passed to run_cmd().
    The -NoProfile switch keeps execution quick and deterministic.
    """
    return [POWERSHELL, "-NoProfile", "-Command", script]

# ──────────────────────────────────────────────────────────────────────────── #
#  Tasks
# ──────────────────────────────────────────────────────────────────────────── #

def scrape_programmes():
    print("\n=== Scraping programme list ===")
    run_cmd([PYTHON, SCRIPT_SCRAPE_PROGRAMMES])

    # ------------------------------------------------------------------ #
    #  Build a unique course-sigle list  (grep | sort | uniq)
    #  PowerShell:  Get-Content -> Select-String -> Sort-Object -Unique
    # ------------------------------------------------------------------ #
    if os.path.exists(CLEAN_COURS):
        os.remove(CLEAN_COURS)

    # ------------------------------------------------------------------ #
    #  Build a unique course-code list  (regex → sort-unique)
    # ------------------------------------------------------------------ #
    ps_extract = f"""
        Get-Content '{RAW_COURS}' |
        Select-String -Pattern '[A-Z]{{3}}[0-9]{{4}}' -AllMatches |
        ForEach-Object {{ $_.Matches.Value }} |
        Sort-Object -Unique |
        Set-Content '{CLEAN_COURS}'          # ← no -NoNewline here
    """
    run_cmd(ps_command(ps_extract))

    # ------------------------------------------------------------------ #
    #  contenu-variable  (this part already used pure Python = unchanged)
    # ------------------------------------------------------------------ #
    print("Scraping contenu variable…")

    url = "https://etudier.uqam.ca/cours-contenu-variable"
    r = requests.get(url)
    r.raise_for_status()

    with open(VAR_CONTENT, "w", encoding="utf-8") as f:
        f.write(r.text)

    ids = re.findall(r"id='([A-Z]{3}[0-9]{3}[A-Z]?)'", r.text)
    with open(CLEAN_COURS, "a", encoding="utf-8") as f:
        for id_ in sorted(set(ids)):
            f.write(id_ + "\n")

    # final dedup / sort
    ps_sort_unique = f"""
        Get-Content '{CLEAN_COURS}' |
        Sort-Object -Unique |
        Set-Content '{CLEAN_COURS}'          #  ← no -NoNewline here
    """
    run_cmd(ps_command(ps_sort_unique))

    print("Programme data scraping completed.\n")

def scrape_cours():
    print("\n=== Scraping course details ===")
    run_cmd([PYTHON, SCRIPT_SCRAPE_COURS])

    # ------------------------------------------------------------------ #
    #  sort & uniq raw CSV   (sort | uniq)
    # ------------------------------------------------------------------ #
    if os.path.exists(CLEAN_DATA):
        os.remove(CLEAN_DATA)

    ps_csv_dedup = f"""
        Get-Content '{RAW_DATA}' |
        Sort-Object -Unique |
        Set-Content '{CLEAN_DATA}'
    """
    run_cmd(ps_command(ps_csv_dedup))

    # ------------------------------------------------------------------ #
    #  rebuild database & JSON – unchanged
    # ------------------------------------------------------------------ #
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    run_cmd([PYTHON, SCRIPT_CSV_TO_SQL])
    run_cmd([PYTHON, SCRIPT_SIGLES_TO_JSON])

    print("Course details scraping completed.\n")

def run_app():
    print("\n=== Starting the application ===\n")
    run_cmd([PYTHON, APP])
    print("Application exited.\n")

def clean():
    print("Cleaning up raw data files…")
    for f in (RAW_COURS, RAW_DATA, VAR_CONTENT):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
    print("Cleanup completed.\n")

def update_last_update_date():
    """
    Update the <span id="last_update_date"> in templates/index.html with today's date (yyyy-MM-dd).
    """
    index_file = Path("templates", "index.html")
    if not index_file.exists():
        print(f"File not found: {index_file}")
        return

    date_str = datetime.now().strftime("%Y-%m-%d")
    pattern = r'(<span\s+id=["\']last_update_date["\'][^>]*>)(.*?)(</span>)'

    with open(index_file, "r", encoding="utf-8") as f:
        content = f.read()

    new_content, count = re.subn(pattern, r'\1' + date_str + r'\3', content, flags=re.IGNORECASE)
    if count == 0:
        print("No <span id=\"last_update_date\"> found in index.html.")
        return

    with open(index_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated last_update_date to {date_str} in {index_file}")
# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def main():
    scrape_programmes()
    scrape_cours()
    update_last_update_date()
    run_app()
    # clean()     

if __name__ == "__main__":
    main()
