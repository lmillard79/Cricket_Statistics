"""Probe Statsguru to find IDs for four new grounds."""
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

TARGETS = ["Old Trafford", "Manchester", "Sydney", "Newlands", "Cape Town",
           "St George", "Port Elizabeth", "Gqeberha"]

# Probe a broad range -- known IDs: MCG=61, Lord's=10, Headingley=179,
# Gabba=209, Eden Gardens=292, The Oval=45, Edgbaston=164, Newlands=174
# Sydney and Old Trafford likely in lower ranges; St George's likely near Newlands
CANDIDATES = list(range(1, 80)) + [174, 175, 176, 177, 178, 180, 181, 182,
                                    210, 211, 212, 213, 214, 215]

print(f"{'ID':>6}  {'rows':>5}  {'At ground text'}")
print("-" * 75)
for gid in CANDIDATES:
    url = f"{BASE}?class=1;ground={gid};template=results;type=batting;view=innings"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        at_ground = ""
        for t in soup.find_all("table", class_="engineTable"):
            for row in t.find_all("tr", class_="data2"):
                text = row.get_text(strip=True)
                if any(k.lower() in text.lower() for k in TARGETS + ["ground"]):
                    at_ground = text[:80]
                    break
            if at_ground:
                break
        n = len(soup.find_all("tr", class_="data1"))
        if n > 1 or any(k.lower() in at_ground.lower() for k in TARGETS):
            print(f"{gid:>6}  {n:>5}  {at_ground}")
    except Exception as e:
        print(f"{gid:>6}  ERROR: {e}")
    time.sleep(1.2)

print("\nDone.")
