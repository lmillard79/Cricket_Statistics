"""Quick diagnostic: inspect what Statsguru returns for MCG page 1."""
import requests
from bs4 import BeautifulSoup

url = (
    "https://stats.espncricinfo.com/ci/engine/stats/index.html"
    "?class=1;ground=61;orderby=start;page=1;template=results;type=batting;view=innings"
)
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
r = requests.get(url, headers=headers, timeout=20)
print("HTTP status:", r.status_code)
print("Response length:", len(r.text))

soup = BeautifulSoup(r.text, "html.parser")
tables = soup.find_all("table")
print(f"\nTables found: {len(tables)}")
for i, t in enumerate(tables):
    cls = t.get("class", [])
    rows = t.find_all("tr")
    print(f"  Table {i:2d}: class={cls}  rows={len(rows)}")
    for row in rows[:2]:
        row_cls = row.get("class", [])
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if cols:
            print(f"    row_class={row_cls}  cols={cols[:6]}")

# Also check for 'data1' anywhere
data1 = soup.find_all("tr", class_="data1")
print(f"\ntr.data1 rows found: {len(data1)}")
if data1:
    print("  First data1 row:", [td.get_text(strip=True) for td in data1[0].find_all("td")][:6])

# Save snippet for manual inspection
with open("data/statsguru_response.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("\nFull response saved to data/statsguru_response.html")

# Print full column contents of first 3 data1 rows
print("\nFull column dump of first 3 data1 rows:")
for row in data1[:3]:
    cols = [td.get_text(strip=True) for td in row.find_all("td")]
    for i, c in enumerate(cols):
        print(f"  col[{i}]: {c!r}")
