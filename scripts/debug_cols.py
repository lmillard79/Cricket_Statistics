from bs4 import BeautifulSoup

with open("data/statsguru_response.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

tables = [t for t in soup.find_all("table", class_="engineTable") if t.find("tr", class_="data1")]
print(f"Tables with data1 rows: {len(tables)}")
t = tables[0]
all_rows = t.find_all("tr")
print(f"All rows in table: {len(all_rows)}")
for i, row in enumerate(all_rows[:5]):
    cls = row.get("class", [])
    cols = [td.get_text(strip=True) for td in row.find_all("td")]
    print(f"  Row {i} cls={cls}: {cols}")
