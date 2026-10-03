"""Upload results.csv to the Supabase `cruises` table (run schema.sql first).

Credentials are asked for at a hidden prompt (or read from SUPABASE_URL / SUPABASE_SERVICE_KEY),
so they never end up in a file or in shell history.
Use the *service_role* key here (Project Settings -> API); the web app itself only needs the anon key.
"""
import csv
import getpass
import os
import sys
from pathlib import Path

import httpx

CSV_PATH = Path(__file__).with_name("results.csv")
INT_COLS = ("page", "nights", "price_from_inr", "num_dates")


def main():
    url = (os.environ.get("SUPABASE_URL") or input("Supabase project URL (https://xxxx.supabase.co): ")).strip().rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or getpass.getpass("Supabase service_role key (hidden): ")

    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for c in INT_COLS:
            r[c] = int(r[c])
    print(f"read {len(rows)} rows from {CSV_PATH.name}")

    headers = {"apikey": key, **({"Authorization": f"Bearer {key}"} if key.startswith("eyJ") else {}),
               "Content-Type": "application/json",
               # re-running the upload updates rows instead of duplicating them
               "Prefer": "resolution=merge-duplicates,return=minimal"}
    endpoint = f"{url}/rest/v1/cruises?on_conflict=cruise_name,locations,price_from_inr,num_dates,banner_tag,page"
    for i in range(0, len(rows), 100):
        r = httpx.post(endpoint, headers=headers, json=rows[i:i + 100], timeout=60)
        if r.status_code >= 300:
            sys.exit(f"upload failed at batch {i // 100}: {r.status_code} {r.text[:300]}")
        print(f"  uploaded {min(i + 100, len(rows))}/{len(rows)}")

    check = httpx.get(f"{url}/rest/v1/cruises?select=id", headers={**headers, "Prefer": "count=exact", "Range": "0-0"}, timeout=60)
    print("rows now in table:", check.headers.get("content-range"))


if __name__ == "__main__":
    main()
