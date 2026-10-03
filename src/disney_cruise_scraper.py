"""
Disney Cruise Line scraper  (https://disneycruise.disney.go.com/en-in/)

Steps (mirrors the challenge brief):
  1. Open the homepage and accept the consent banner.
  2. Click "View Dates" to open the results list ("Find a Cruise").
  3. Wait for the cards to load.
  4. Scroll to the end, 5 cards per "page", until all 35 pages are loaded.
  5. Clean the data (no empties, no duplicates, locations present).
  6. Write results.csv and print the answers to the 5 questions.

NOTE: the site sits behind Akamai and returns "Access Denied" to datacenter IPs
(e.g. Google Colab). Run this from a normal home/office connection.

Usage:  python disney_cruise_scraper.py            # scrape + clean + answers
        python disney_cruise_scraper.py --clean    # skip scraping, reuse data/raw.json
"""
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

URL = "https://disneycruise.disney.go.com/en-in/"
CARD = "dcl-product-card"
CARDS_PER_PAGE = 5
MIN_PAGES = 35
# Local layout: src/ (this file) + data/ (outputs). In Colab everything sits in the cwd.
_DATA = Path(__file__).resolve().parent.parent / "data"
DATA_DIR = _DATA if _DATA.is_dir() else Path(".")
RAW_JSON = DATA_DIR / "raw.json"
API_JSON = DATA_DIR / "raw_api.json"
OUT_CSV = DATA_DIR / "results.csv"

# Runs inside the page: turns every card into a plain dict of raw text.
EXTRACT_JS = """
cards => cards.map(c => {
  const t = s => { const e = c.querySelector(s); return e ? e.innerText.trim() : ''; };
  const all = s => [...c.querySelectorAll(s)].map(e => e.innerText.trim()).filter(Boolean);
  const btn = c.querySelector('a.product-card-footer-wrapper__btn');
  return {
    title: t('h2.product-card-content__name'),
    banner: t('.product-card__banner'),
    locations: all('ul.ul-port-list li'),
    prices: all('.wrapper-price__pricing'),
    price_text: t('.product-card-pricing-wrapper'),
    dates_button: btn ? btn.innerText.trim() : '',
    link: btn ? btn.href : '',
    full_text: c.innerText
  };
})
"""


# --------------------------------------------------------------------------
# Scraping
# --------------------------------------------------------------------------
def scrape():
    from playwright.sync_api import sync_playwright

    api_products = {}

    with sync_playwright() as p:
        # A real Edge window is far less likely to be flagged than headless Chromium.
        if "google.colab" in sys.modules:   # Colab: headless Chromium (usually blocked by the site)
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        else:
            browser = p.chromium.launch(channel="msedge", headless=False)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="en-IN")
        page = ctx.new_page()

        # Keep the JSON the site itself fetches for each page (used to cross-check).
        total_info = {}

        def on_response(r):
            if "available-products" in r.url and "json" in (r.headers.get("content-type") or ""):
                try:
                    j = r.json()
                except Exception:
                    return
                total_info.update({k: j.get(k) for k in ("totalPages", "totalAvailableCruises")})
                for prod in j.get("products", []):
                    api_products[prod["productId"]] = {
                        "productId": prod["productId"],
                        "name": prod.get("productDisplayName"),
                        "sailings": sum(i.get("numberOfSailings", 0) for i in prod.get("itineraries", [])),
                    }

        page.on("response", on_response)

        # Step 1: navigate and agree
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)
        if "denied" in page.title().lower():
            raise RuntimeError("Access Denied by the site's bot protection (datacenter IP?). "
                               "Run from a home/office connection or use --clean with data/raw.json.")
        for label in ("Accept All Cookies", "Accept All", "Agree", "I Agree", "Accept"):
            try:
                page.get_by_role("button", name=label).first.click(timeout=1500)
                break
            except Exception:
                pass

        # Step 2: View Dates (no filters = the full catalogue)
        page.locator(".view-cruises-button").first.click()

        # Step 3: wait for the first cards
        page.wait_for_selector(CARD, timeout=60000)
        page.wait_for_timeout(3000)

        # Step 4: scroll until every page is loaded
        total = total_info.get("totalAvailableCruises") or MIN_PAGES * CARDS_PER_PAGE
        count, stalled = page.locator(CARD).count(), 0
        while count < total and stalled < 8:
            page.mouse.wheel(0, 8000)
            page.keyboard.press("End")
            page.wait_for_timeout(1500)
            new = page.locator(CARD).count()
            stalled = stalled + 1 if new == count else 0
            count = new
            print(f"  loaded {count}/{total} cards (page {count // CARDS_PER_PAGE})", end="\r")
        print()

        rows = page.eval_on_selector_all(CARD, EXTRACT_JS)
        browser.close()

    for i, r in enumerate(rows):
        r["page"] = i // CARDS_PER_PAGE + 1

    with open(RAW_JSON, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    with open(API_JSON, "w", encoding="utf-8") as f:
        json.dump({"info": total_info, "products": list(api_products.values())}, f, indent=1)
    print(f"scraped {len(rows)} cards; site reports {total_info}")
    return rows


# --------------------------------------------------------------------------
# Cleaning
# --------------------------------------------------------------------------
def money(s):
    """'₹1,09,674 INR' / '$1,142 USD' -> int"""
    m = re.search(r"[\d,]+", s or "")
    return int(m.group().replace(",", "")) if m else None


def split_port(text):
    """'San Diego ending in Galveston' -> ('San Diego', 'ending in Galveston')"""
    m = re.match(r"(.+?)\s+((?:ending|with)\s.*)$", text.strip(), flags=re.I)
    return (m.group(1).strip(), m.group(2).strip()) if m else (text.strip(), "No Note")


def clean(rows):
    recs = []
    for r in rows:
        title = re.sub(r"\s+", " ", r["title"]).strip()
        nights = re.match(r"(\d+)-Night", title)
        port = re.search(r"\bfrom (.+)$", title)
        locs = [re.sub(r"\s+", " ", l).strip() for l in r["locations"] if l.strip()]
        prices = r["prices"]
        inr = next((money(p) for p in prices if "INR" in p), None)
        if inr is None:
            inr = money(re.search(r"₹[\d,]+", r["price_text"]).group()) if re.search(r"₹[\d,]+", r["price_text"]) else None
        n_dates = re.search(r"Show (\d+) Dates?", r["dates_button"] or r["full_text"])
        offer = "Guaranteed with Restrictions" if "Guaranteed with Restrictions" in r["full_text"] else ""
        recs.append({
            "page": r["page"],
            "cruise_name": title,
            "nights": int(nights.group(1)) if nights else None,
            "departure_port": split_port(port.group(1))[0] if port else None,
            "itinerary_note": split_port(port.group(1))[1] if port else "No Note",
            "locations": " | ".join(locs),
            "banner_tag": re.sub(r"\s+", " ", r["banner"]).strip(),
            "offer": offer,
            "price_from_inr": inr,
            "num_dates": int(n_dates.group(1)) if n_dates else None,
            "link": r["link"],
        })
    df = pd.DataFrame(recs)

    n0 = len(df)
    # Duplicates: the same cruise card appearing twice.
    df = df.drop_duplicates(subset=["cruise_name", "locations", "price_from_inr", "num_dates", "banner_tag"])
    print(f"duplicates removed: {n0 - len(df)}")

    # Empty-field rules. Locations must exist; the cards without a "Sailing to"
    # block fall back to the destination named in the cruise title.
    df["locations"] = df["locations"].where(df["locations"] != "", df["departure_port"])
    df["banner_tag"] = df["banner_tag"].replace("", "No Banner")
    df["offer"] = df["offer"].replace("", "No Offer")
    required = ["cruise_name", "departure_port", "locations", "price_from_inr", "num_dates", "nights"]
    bad = df[df[required].isna().any(axis=1) | (df[required].astype(str) == "").any(axis=1)]
    if len(bad):
        print(f"dropping {len(bad)} rows with empty required fields")
    df = df.drop(bad.index).reset_index(drop=True)
    return df


# --------------------------------------------------------------------------
# Answers
# --------------------------------------------------------------------------
def answers(df, api_total=None):
    pacific = df["cruise_name"].str.contains("Pacific", case=False) | df["locations"].str.contains("Pacific", case=False)
    holiday_tags = ["Very Merrytime", "Halloween on the High Seas"]   # site lists these under "Holiday Cruises"
    holiday = df["banner_tag"].isin(holiday_tags)
    themed = df["banner_tag"].isin(["Marvel Days at Sea", "Pixar Days at Sea"])
    two_plus = df["num_dates"] > 2
    miami = df["departure_port"].str.contains("Miami", case=False).sum()
    london = df["departure_port"].str.contains("London", case=False).sum()
    print("\n=========== ANSWERS ===========")
    print(f"(i)   Pacific cruises .............. {int(pacific.sum())}   ({int(df.loc[pacific, 'num_dates'].sum())} sailings)")
    print(f"(ii)  Total cruises ................ {int(df['num_dates'].sum())}"
          f"   (= site header; {len(df)} distinct cruise cards on {df['page'].max()} pages)")
    print(f"(iii) Holiday cruises .............. {int(holiday.sum())}   {df.loc[holiday, 'banner_tag'].value_counts().to_dict()}"
          f"   [+{int(themed.sum())} themed Marvel/Pixar]")
    print(f"(iv)  Cruises with > 2 dates ....... {int(two_plus.sum())}")
    print(f"(v)   Departing Miami / London ..... Miami={miami}, London={london}, total={miami + london}")
    print("departure ports:", df["departure_port"].value_counts().to_dict())


if __name__ == "__main__":
    if "--clean" in sys.argv:
        raw = json.load(open(RAW_JSON, encoding="utf-8"))
    else:
        t0 = time.time()
        raw = scrape()
        print(f"scrape took {time.time() - t0:.0f}s")
    frame = clean(raw)
    frame.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"wrote {OUT_CSV}: {frame.shape[0]} rows x {frame.shape[1]} cols")
    try:
        api_total = json.load(open(API_JSON))["info"].get("totalAvailableCruises")
    except Exception:
        api_total = None
    answers(frame, api_total)
