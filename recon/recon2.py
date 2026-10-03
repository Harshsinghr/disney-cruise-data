from playwright.sync_api import sync_playwright
import json
store={}
with sync_playwright() as p:
    b=p.chromium.launch(channel="msedge",headless=False)
    ctx=b.new_context(viewport={"width":1440,"height":900},locale="en-IN")
    pg=ctx.new_page()
    def on(r):
        if "productavail" in r.url and "json" in (r.headers.get("content-type") or ""):
            try: store[r.url]=r.json()
            except: pass
    pg.on("response",on)
    pg.goto("https://disneycruise.disney.go.com/en-in/",wait_until="domcontentloaded"); pg.wait_for_timeout(5000)
    pg.locator(".view-cruises-button").first.click(); pg.wait_for_timeout(8000)
    sel="dcl-product-card"
    print("cards initial:",pg.locator(sel).count())
    prev=0
    for i in range(8):
        pg.mouse.wheel(0,6000); pg.wait_for_timeout(1500)
        n=pg.locator(sel).count()
        if i%3==0 or n!=prev: print(i,n)
        prev=n
    print("final cards",pg.locator(sel).count())
    print("buttons:",[t for t in pg.locator("button").all_inner_texts() if "more" in t.lower() or "load" in t.lower()][:5])
    open("cards_text.txt","w",encoding="utf-8").write("
=====
".join(pg.locator(sel).all_inner_texts()))
    open("card_first.html","w",encoding="utf-8").write(pg.locator(sel).first.evaluate("e=>e.outerHTML"))
    b.close()
for u,j in store.items(): print(u[:130], len(json.dumps(j)))
json.dump(store,open("api_dump.json","w"))
