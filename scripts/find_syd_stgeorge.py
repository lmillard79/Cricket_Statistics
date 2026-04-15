"""Find Sydney Cricket Ground and St George's Park IDs."""
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}
BASE = "https://stats.espncricinfo.com/ci/engine/stats/index.html"

TARGETS = ["Sydney", "St George", "Port Elizabeth", "Gqeberha", "Buffalo"]

# Sydney likely in Australian range (near MCG=61, Gabba=209, WACA=213, Adelaide~?)
# St George's Park likely near other SA grounds (Newlands=174, Durban=212)
CANDIDATES = (
    list(range(80, 120))    # likely Australian/early grounds
    + list(range(190, 215)) # SA range
    + list(range(215, 240))
    + list(range(280, 300))
    + list(range(300, 320))
)

print(f"{'ID':>6}  {'rows':>5}  {'At ground text'}")
print("-" * 75)
found = {}
for gid in CANDIDATES:
    url = f"{BASE}?class=1;ground={gid};template=results;type=batting;view=innings"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        at_ground = ""
        for t in soup.find_all("table", class_="engineTable"):
            for row in t.find_all("tr", class_="data2"):
                text = row.get_text(strip=True)
                if "ground" in text.lower():
                    at_ground = text[:90]
                    break
            if at_ground:
                break
        n = len(soup.find_all("tr", class_="data1"))
        if n > 1:
            print(f"{gid:>6}  {n:>5}  {at_ground}")
            if any(k.lower() in at_ground.lower() for k in TARGETS):
                found[gid] = at_ground
    except Exception as e:
        print(f"{gid:>6}  ERROR: {e}")
    time.sleep(1.2)

print("\n--- TARGET MATCHES ---")
for gid, txt in found.items():
    print(f"  {gid}: {txt}")
print("Done.")
