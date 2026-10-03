import json
cells = [
"# Disney Cruise - Colab recon\nRun cells top to bottom. Goal: find out if Colab can load the site and reach the results list.",
"!pip -q install playwright nest_asyncio\n!playwright install chromium --with-deps >/dev/null 2>&1\nprint('ok')",
'''from playwright.sync_api import sync_playwright
import json, time
URL = "https://disneycruise.disney.go.com/en-in/"
log = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(viewport={"width":1440,"height":900}, locale="en-IN",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    pg = ctx.new_page()
    pg.on("response", lambda r: log.append((r.status, r.url)) if "json" in (r.headers.get("content-type") or "") else None)
    pg.goto(URL, wait_until="domcontentloaded"); pg.wait_for_timeout(5000)
    print("HOME:", pg.title(), "|", pg.url)
    pg.screenshot(path="01_home.png")
    # open filters + click View Dates
    for label in ["Leaving", "Sailing to", "Departing from"]:
        try: pg.get_by_text(label, exact=True).first.click(timeout=3000); pg.wait_for_timeout(1500); pg.screenshot(path=f"02_{label.split()[0]}.png")
        except Exception as e: print("filter fail", label, str(e)[:80])
    pg.screenshot(path="03_filters.png")
    pg.locator(".view-cruises-button").first.click(); pg.wait_for_timeout(8000)
    print("AFTER VIEW DATES:", pg.title(), "|", pg.url)
    pg.screenshot(path="04_results.png", full_page=True)
    open("results.html","w",encoding="utf-8").write(pg.content())
    b.close()
print("\nJSON responses seen:")
for s,u in log[:40]: print(s,u[:150])''',
"from IPython.display import Image, display\nimport glob\nfor f in sorted(glob.glob('0*.png')): print(f); display(Image(f))",
"# Download everything to share back\nfrom google.colab import files\n!zip -q recon.zip 0*.png results.html\nfiles.download('recon.zip')",
]
nb = {"cells":[{"cell_type":"markdown" if i==0 else "code","metadata":{},"source":c, **({} if i==0 else {"outputs":[],"execution_count":None})} for i,c in enumerate(cells)],
      "metadata":{"kernelspec":{"name":"python3","display_name":"Python 3"}},"nbformat":4,"nbformat_minor":5}
json.dump(nb, open("01_recon.ipynb","w"), indent=1)
print("written")
