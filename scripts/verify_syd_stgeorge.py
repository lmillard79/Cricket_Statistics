"""Quick verify: Sydney=132, St George's Park=173."""
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

for gid in [132, 173]:
    url = f"{BASE}?class=1;ground={gid};template=results;type=batting;view=innings"
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
    print(f"ID {gid:>5}  rows={n:>3}  {at_ground}")
