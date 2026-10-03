from playwright.sync_api import sync_playwright
import json

SEL = "dcl-product-card"
api = {}

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=False)
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="en-IN")
    pg = ctx.new_page()

    def on(r):
        if "productavail" in r.url and "json" in (r.headers.get("content-type") or ""):
            try:
                api[r.url] = r.json()
            except Exception:
                pass

    pg.on("response", on)
    pg.goto("https://disneycruise.disney.go.com/en-in/", wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    pg.locator(".view-cruises-button").first.click()
    pg.wait_for_timeout(8000)
    for _ in range(6):
        pg.mouse.wheel(0, 6000)
        pg.wait_for_timeout(1500)
    print("cards:", pg.locator(SEL).count())
    texts = pg.locator(SEL).all_inner_texts()
    with open("cards_text.txt", "w", encoding="utf-8") as f:
        f.write("\n=====\n".join(texts))
    with open("card_first.html", "w", encoding="utf-8") as f:
        f.write(pg.locator(SEL).nth(2).evaluate("e => e.outerHTML"))
    b.close()

with open("api_dump.json", "w", encoding="utf-8") as f:
    json.dump(api, f)
for u, j in api.items():
    print(u[:140], len(json.dumps(j)))
