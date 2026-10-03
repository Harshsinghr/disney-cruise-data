"""Builds notebooks/disney_cruise_colab.ipynb from src/ + data/ so the notebook never drifts from the code."""
import base64
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
script = (ROOT / "src" / "disney_cruise_scraper.py").read_text(encoding="utf-8")
raw_b64 = base64.b64encode(gzip.compress((ROOT / "data" / "raw.json").read_bytes())).decode()
api_b64 = base64.b64encode(gzip.compress((ROOT / "data" / "raw_api.json").read_bytes())).decode()


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text}


def code(text):
    return {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None, "source": text}


cells = [
    md("# Disney Cruise Line scraper — Challenge 1\n"
       "Scrapes `disneycruise.disney.go.com/en-in`, cleans the data, writes `results.csv` and prints the 5 answers.\n\n"
       "**Run all cells top to bottom.** The site's bot protection (Akamai) blocks Colab's datacenter IPs, so the "
       "live scrape (cell 4) normally ends in *Access Denied* here. The notebook then falls back to the "
       "`raw.json` that the same script scraped from a home connection (35 pages, 171 cards), and runs the "
       "identical cleaning + answer code on it."),
    md("## 1. Install"),
    code("!pip -q install playwright pandas\n!playwright install chromium --with-deps > /dev/null 2>&1\nprint('ready')"),
    md("## 2. Scraper source (`disney_cruise_scraper.py`)\nSteps: navigate → View Dates → wait for cards → scroll 35 pages → clean → CSV → answers."),
    code("%%writefile disney_cruise_scraper.py\n" + script),
    md("## 3. Data scraped from a home connection (fallback)\nThe raw cards, exactly as the script's `scrape()` saved them."),
    code("import base64, gzip\n"
         f"RAW = '{raw_b64}'\n"
         f"API = '{api_b64}'\n"
         "open('raw.json', 'wb').write(gzip.decompress(base64.b64decode(RAW)))\n"
         "open('raw_api.json', 'wb').write(gzip.decompress(base64.b64decode(API)))\n"
         "print('raw.json and raw_api.json written')"),
    md("## 4. Try the live scrape (expected to be blocked in Colab)"),
    code("import subprocess, sys\n"
         "r = subprocess.run([sys.executable, 'disney_cruise_scraper.py'], capture_output=True, text=True)\n"
         "print((r.stdout + r.stderr)[-1500:])\n"
         "LIVE_OK = r.returncode == 0\n"
         "print('LIVE SCRAPE', 'OK' if LIVE_OK else 'BLOCKED -> using raw.json from section 3')"),
    md("## 5. Clean the data, write `results.csv`, print the answers"),
    code("!python disney_cruise_scraper.py --clean"),
    md("## 6. Preview and download"),
    code("import pandas as pd\n"
         "df = pd.read_csv('results.csv', encoding='utf-8-sig', keep_default_na=False)\n"
         "print(df.shape, '| empty cells:', int((df == '').sum().sum()), '| duplicate rows:', int(df.duplicated().sum()))\n"
         "df.drop(columns='link').head(10)"),
    code("from google.colab import files\nfiles.download('results.csv')"),
]

nb = {
    "cells": cells,
    "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                 "colab": {"name": "disney_cruise_colab.ipynb"}},
    "nbformat": 4,
    "nbformat_minor": 5,
}
out = ROOT / "notebooks" / "disney_cruise_colab.ipynb"
out.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print("wrote", out, f"({out.stat().st_size // 1024} KB)")
