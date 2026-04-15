Excellent — the Statsguru query is working and the data goes back to 15 March 1877. That is a 148-year gauge record for the MCG. Note the ground ID in that URL is **61**, not 56 as I suggested earlier — so verify all five ground IDs before running the scraper.

Here are corrected instructions for Windsurf:

---

## Corrected Windsurf Instructions: ESPNcricinfo Statsguru Scraper

### Step 1: Verify ground IDs manually first

Open each URL in a browser and confirm the venue name before running any code:

```
MCG:          https://stats.espncricinfo.com/ci/engine/stats/index.html?class=1;ground=61;template=results;type=batting;view=innings
Gabba:        https://stats.espncricinfo.com/ci/engine/stats/index.html?class=1;ground=46;template=results;type=batting;view=innings
Lord's:       https://stats.espncricinfo.com/ci/engine/stats/index.html?class=1;ground=45;template=results;type=batting;view=innings
Headingley:   https://stats.espncricinfo.com/ci/engine/stats/index.html?class=1;ground=44;template=results;type=batting;view=innings
Eden Gardens: https://stats.espncricinfo.com/ci/engine/stats/index.html?class=1;ground=47;template=results;type=batting;view=innings
```

Note: Statsguru uses semicolons as parameter separators, not ampersands. The scraper must replicate this exactly.

---

### Step 2: Scraper

The screenshot confirms the table structure. Key observations from the image:
- The page header shows **4884 innings records** across **98 pages** for the MCG
- Columns are: Player, Runs, Mins, BF, 4s, 6s, SR, Inns, Opposition, Ground, Start Date
- Runs column contains asterisks for not-out innings (e.g. `165*`) — strip these
- Some Runs cells contain `-` or `DNB` — skip these
- Start Date format is `15 Mar 1877` — parse accordingly

```python
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

GROUND_IDS = {
    'MCG':          61,  # confirmed from URL
    'Gabba':        46,  # verify before running
    "Lord's":       45,  # verify before running
    'Headingley':   44,  # verify before running
    'Eden Gardens': 47,  # verify before running
}

def parse_runs(raw):
    """Strip not-out asterisk and return integer, or None if not a score."""
    cleaned = raw.replace('*', '').strip()
    if cleaned.isdigit():
        return int(cleaned)
    return None

def parse_year(date_str):
    """Extract year from Statsguru date format: '15 Mar 1877'."""
    parts = date_str.strip().split()
    if len(parts) == 3 and parts[2].isdigit():
        return int(parts[2])
    return None

def scrape_ground(ground_name, ground_id, pause=2.0):
    records = []
    page = 1
    base = "https://stats.espncricinfo.com/ci/engine/stats/index.html"

    while True:
        params = (
            f"?class=1;ground={ground_id};orderby=start"
            f";page={page};template=results;type=batting;view=innings"
        )
        url = base + params
        headers = {'User-Agent': 'Mozilla/5.0 (compatible)'}

        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  Request failed page {page}: {e}")
            break

        soup = BeautifulSoup(r.text, 'html.parser')

        # Statsguru results table has class 'engineTable'
        tables = soup.find_all('table', class_='engineTable')
        # The data table is typically the second engineTable
        data_table = None
        for t in tables:
            if t.find('tr', class_='data1'):
                data_table = t
                break

        if not data_table:
            print(f"  No data table found on page {page} — stopping.")
            break

        rows = data_table.find_all('tr', class_='data1')
        if not rows:
            break

        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all('td')]
            if len(cols) < 11:
                continue

            runs  = parse_runs(cols[0])
            date  = parse_year(cols[10])  # Start Date is 11th column (index 10)

            if runs is not None and date is not None:
                records.append({
                    'ground': ground_name,
                    'year':   date,
                    'score':  runs,
                })

        # Check for a Next page link
        next_btn = soup.find('a', string=re.compile(r'Next', re.I))
        if not next_btn:
            print(f"  {ground_name}: finished at page {page} ({len(records)} innings)")
            break

        page += 1
        time.sleep(pause)

    return records


# Run scraper for all five grounds
all_records = []
for name, gid in GROUND_IDS.items():
    print(f"\nScraping {name} (ground_id={gid})...")
    recs = scrape_ground(name, gid)
    all_records.extend(recs)
    time.sleep(3)  # pause between grounds

df = pd.DataFrame(all_records)
df.to_csv('outputs/ground_innings_historical.csv', index=False)
print("\nDone. Record counts:")
print(df.groupby('ground').agg(
    n_innings=('score','count'),
    first_year=('year','min'),
    last_year=('year','max'),
    ground_record=('score','max')
))
```

---

### Step 3: Build Annual Maxima Series

```python
# Highest individual innings per ground per year
ams = (df.groupby(['ground', 'year'])['score']
         .max()
         .reset_index()
         .rename(columns={'score': 'ams'}))

print("\nAMS sample sizes:")
print(ams.groupby('ground').agg(
    n_seasons=('ams','count'),
    first=('year','min'),
    last=('year','max'),
    max_ams=('ams','max')
))
```

---

### Step 4: Sanity checks before fitting

Run these before proceeding to GEV fitting:

```python
# 1. Check for any suspicious scores (e.g. > 501 is all-time Test record)
print(df[df['score'] > 400][['ground','year','score']])

# 2. Check years with multiple Tests — confirm max is being taken correctly
print(ams[ams['ground'] == 'MCG'].sort_values('year').head(20))

# 3. Plot raw AMS as a time series for each ground before fitting anything
import matplotlib.pyplot as plt
fig, axes = plt.subplots(5, 1, figsize=(12, 16), sharex=False)
for ax, ground in zip(axes, GROUND_IDS.keys()):
    sub = ams[ams['ground'] == ground]
    ax.plot(sub['year'], sub['ams'], 'o-', color='#1e4164', ms=4, lw=1)
    ax.set_title(ground, fontsize=10, fontweight='bold')
    ax.set_ylabel('AMS (runs)')
    ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('outputs/ams_timeseries_raw.png', dpi=120, bbox_inches='tight')
plt.show()
```

The time series plot is the first thing to look at. If you can see a visual shift in the level or variability after a certain decade, that is your non-stationarity signal before any GEV is fitted.

---

### What to expect once this runs correctly

| Ground | Expected n | Record year | Notable innings |
|---|---|---|---|
| MCG | ~90–110 | 1877 | Len Hutton 364 at The Oval; MCG record likely ~307 (Bob Cowper 1966) |
| Lord's | ~75–90 | 1884 | Graham Gooch 333 in 1990 is the Lord's record |
| Gabba | ~45–55 | 1931 | Matthew Hayden era likely dominates upper tail |
| Headingley | ~60–70 | 1899 | Len Hutton 364 is at The Oval not here — Headingley record is Wally Hammond 336 in 1938 |
| Eden Gardens | ~55–70 | 1934 | VVS Laxman 281 in 2001 is the standout event |

Those sample sizes will give stable GEV fits and make the epoch split genuinely informative.s