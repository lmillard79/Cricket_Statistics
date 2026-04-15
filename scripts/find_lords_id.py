"""Probe IDs in range likely to contain Lord's."""
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}
BASE = "https://stats.espncricinfo.com/ci/engine/stats/index.html"

# Test IDs likely to be Lord's -- common suggestions online are 45, 46, 2, 3
CANDIDATES = [2, 3, 10, 40, 41, 42, 43, 48, 49, 50, 51, 52, 53, 54, 55]

print(f"{'ID':>6}  {'rows':>5}  {'At ground text'}")
print("-" * 70)
for gid in CANDIDATES:
    url = f"{BASE}?class=1;ground={gid};template=results;type=batting;view=innings"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        at_ground = ""
        for t in soup.find_all("table", class_="engineTable"):
            for row in t.find_all("tr", class_="data2"):
                text = row.get_text(strip=True)
                if "ground" in text.lower() or "lord" in text.lower() or "ENG" in text:
                    at_ground = text[:80]
                    break
            if at_ground:
                break
        n = len(soup.find_all("tr", class_="data1"))
        print(f"{gid:>6}  {n:>5}  {at_ground}")
    except Exception as e:
        print(f"{gid:>6}  ERROR: {e}")
    time.sleep(1.5)
