"""Disney Cruise data viewer.

Reads from Supabase when SUPABASE_URL + SUPABASE_ANON_KEY are set, otherwise from the bundled results.csv.
"""
import csv
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).parent
app = FastAPI(title="Disney Cruise Data")
templates = Jinja2Templates(directory=str(BASE / "templates"))

COLUMNS = ["cruise_name", "nights", "departure_port", "itinerary_note", "locations",
           "banner_tag", "offer", "price_from_inr", "num_dates"]
INT_COLS = ("page", "nights", "price_from_inr", "num_dates")


def auth(key):
    """New-style keys (sb_...) go in `apikey` only; legacy JWT keys (eyJ...) also need the Bearer header."""
    return {"apikey": key, **({"Authorization": f"Bearer {key}"} if key.startswith("eyJ") else {})}


def from_supabase():
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY")
    if not (url and key):
        return None
    rows, start = [], 0
    while True:  # PostgREST returns at most 1000 rows per request
        r = httpx.get(f"{url.rstrip('/')}/rest/v1/cruises?select=*&order=page.asc,id.asc",
                      headers={**auth(key), "Range": f"{start}-{start + 999}"},
                      timeout=30)
        r.raise_for_status()
        batch = r.json()
        rows += batch
        if len(batch) < 1000:
            return rows
        start += 1000


def from_csv():
    with open(BASE / "results.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for c in INT_COLS:
            r[c] = int(r[c])
    return rows


def load():
    try:
        rows = from_supabase()
        if rows is not None:
            return rows, "Supabase"
    except Exception as e:  # network / key problems must not take the page down
        print("Supabase read failed, falling back to CSV:", e)
    return from_csv(), "CSV file"


def stats(rows):
    return {
        "cruises": len(rows),
        "sailings": sum(r["num_dates"] for r in rows),
        "holiday": sum(r["banner_tag"] in ("Very Merrytime", "Halloween on the High Seas") for r in rows),
        "multi_date": sum(r["num_dates"] > 2 for r in rows),
        "pacific": sum("pacific" in (r["cruise_name"] + r["locations"]).lower() for r in rows),
        "ports": len({r["departure_port"] for r in rows}),
    }


@app.get("/")
def index(request: Request):
    rows, source = load()
    return templates.TemplateResponse(request, "index.html", {
        "rows": rows, "columns": COLUMNS, "source": source, "stats": stats(rows)})


@app.get("/api/cruises")
def api():
    rows, source = load()
    return JSONResponse({"source": source, "count": len(rows), "data": rows})


@app.get("/health")
def health():
    return {"ok": True}
