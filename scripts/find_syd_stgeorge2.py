"""Broader search for Sydney Cricket Ground and St George's Park."""
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

TARGETS = ["Sydney", "St George", "Port Elizabeth", "Gqeberha"]

# Try larger ID ranges and known Australian/SA clusters
CANDIDATES = (
    list(range(320, 420))
    + list(range(800, 870))
    + list(range(3400, 3430))
    + list(range(5000, 5030))
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
