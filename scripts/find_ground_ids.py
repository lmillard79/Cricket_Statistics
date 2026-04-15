"""
Probe Statsguru to identify which ground each ID corresponds to,
by reading the 'At ground' header row from Table 0.

Tests a range of candidate IDs around the ones in the plan.
"""
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
BASE = "https://stats.espncricinfo.com/ci/engine/stats/index.html"
TARGETS = ["Gabba", "Brisbane", "Headingley", "Leeds", "Eden Gardens", "Kolkata", "Lord"]

# Candidates to probe: plan IDs + known correct IDs
CANDIDATES = [44, 45, 46, 47, 61, 164, 174, 179, 209, 292, 3404]

print(f"{'ID':>6}  {'At ground text'}")
print("-" * 60)
for gid in CANDIDATES:
    url = f"{BASE}?class=1;ground={gid};template=results;type=batting;view=innings"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        # 'At ground' is in a data2 row in the first engineTable
        at_ground = ""
        for t in soup.find_all("table", class_="engineTable"):
            for row in t.find_all("tr", class_="data2"):
                text = row.get_text(strip=True)
                if "ground" in text.lower() or any(k.lower() in text.lower() for k in TARGETS):
                    at_ground = text
                    break
            if at_ground:
                break
        n_data1 = len(soup.find_all("tr", class_="data1"))
        print(f"{gid:>6}  rows={n_data1:>3}  {at_ground[:80]}")
    except Exception as e:
        print(f"{gid:>6}  ERROR: {e}")
    time.sleep(1.5)
