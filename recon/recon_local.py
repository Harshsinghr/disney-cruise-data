from playwright.sync_api import sync_playwright
log=[]
with sync_playwright() as p:
    b=p.chromium.launch(channel="msedge",headless=False)
    ctx=b.new_context(viewport={"width":1440,"height":900},locale="en-IN")
    pg=ctx.new_page()
    pg.on("response",lambda r: log.append((r.status,r.url)) if "json" in (r.headers.get("content-type") or "") else None)
    pg.goto("https://disneycruise.disney.go.com/en-in/",wait_until="domcontentloaded"); pg.wait_for_timeout(6000)
    print("HOME:",pg.title(),pg.url); pg.screenshot(path="r1_home.png")
    pg.get_by_text("Leaving",exact=True).first.click(); pg.wait_for_timeout(2000); pg.screenshot(path="r2_leaving.png")
    print(pg.locator("body").inner_text()[:600])
    pg.locator(".view-cruises-button").first.click(); pg.wait_for_timeout(9000)
    print("AFTER:",pg.title(),pg.url); pg.screenshot(path="r3_results.png",full_page=True)
    open("results.html","w",encoding="utf-8").write(pg.content())
    b.close()
for s,u in log[:40]: print(s,u[:160])
