from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=False)
    pg = b.new_context(viewport={"width": 1440, "height": 900}, locale="en-IN").new_page()
    pg.goto("https://disneycruise.disney.go.com/en-in/", wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    # More Filters: list its options
    pg.get_by_text("More Filters", exact=True).first.click()
    pg.wait_for_timeout(2000)
    pg.screenshot(path="f0_more.png")
    print("MORE FILTERS:", [t.strip() for t in pg.locator("quick-quote-filter, dcl-ui-global-quick-quote").all_inner_texts()][:1])

    # Sailing to -> Pacific Coast Cruises
    pg.get_by_text("Sailing to", exact=True).first.click()
    pg.wait_for_timeout(1500)
    pg.get_by_text("Pacific Coast Cruises", exact=True).last.click()
    pg.wait_for_timeout(1500)
    pg.screenshot(path="f1_selected.png")
    pg.locator(".view-cruises-button").first.click()
    pg.wait_for_selector("dcl-product-card", timeout=60000)
    pg.wait_for_timeout(4000)
    for _ in range(12):
        pg.mouse.wheel(0, 8000)
        pg.wait_for_timeout(1200)
    print("cards:", pg.locator("dcl-product-card").count())
    print([t for t in pg.locator("h1,h2,h3,p,span").all_inner_texts() if "Cruises" in t and len(t) < 20][:5])
    for t in pg.locator("dcl-product-card h2").all_inner_texts():
        print(" -", t)
    pg.screenshot(path="f2_result.png")
    b.close()
