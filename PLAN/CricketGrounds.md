Eden Gardens in Kolkata, established in 1864, is the oldest cricket stadium in India and first hosted a Test in 1934. That is your ground. It also has the added hook of being the home of the Kolkata Knight Riders in the IPL — maximum engagement from Indian followers.

Now let me write the full Windsurf handoff plan.

---

## Windsurf Handoff: Cricket Ground as Hydrological Gauge Station

### Concept

Treat each Test ground as a long-period stream gauge. The annual maxima series (AMS) is the highest individual innings score recorded at that ground in each calendar year. Fit a GEV distribution to each ground's AMS and plot frequency curves. Look for non-stationarity by splitting the record into epochs and comparing GEV parameters across eras.

### Selected Grounds and Rationale

| Ground | Country | First Test | Engagement hook |
|---|---|---|---|
| MCG | Australia | 1877 | Longest record in the world — 148 years |
| Gabba | Australia | 1931 | Brisbane local; scheduling shift post |
| Lord's | England | 1884 | "Home of cricket"; drought framing |
| Headingley | England | 1899 | England Ashes drought anchor |
| Eden Gardens | India | 1934 | Oldest Indian ground; KKR/IPL hook |

---

### Data Source

**Cricsheet** — https://cricsheet.org/downloads/tests_json.zip

All Tests in JSON format, ball by ball. Free and comprehensive.

---

### Step 1: Data ingestion

```python
import requests, zipfile, io, os, json, glob
import pandas as pd
from datetime import datetime

DATA_URL = "https://cricsheet.org/downloads/tests_json.zip"
EXTRACT_PATH = "./cricsheet_data"

def download_and_extract(url, path):
    os.makedirs(path, exist_ok=True)
    r = requests.get(url)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(path)

download_and_extract(DATA_URL, EXTRACT_PATH)
```

---

### Step 2: Parse to ground-level innings records

The key fields to extract from each JSON file:

- `info.venue` — ground name (needs cleaning, see below)
- `info.dates[0]` — match date
- `innings[n].team` — batting team
- Per delivery: `runs.batter` summed per batter per innings to get individual scores

```python
def parse_all_innings(directory):
    records = []
    for fp in glob.glob(f"{directory}/*.json"):
        with open(fp) as f:
            data = json.load(f)
        info = data.get('info', {})
        venue = info.get('venue', 'Unknown')
        date = datetime.strptime(info['dates'][0], '%Y-%m-%d')
        
        for innings in data.get('innings', []):
            team = innings['team']
            # Aggregate runs per batter
            batter_runs = {}
            for over in innings.get('overs', []):
                for delivery in over.get('deliveries', []):
                    batter = delivery['batter']
                    runs = delivery['runs']['batter']
                    batter_runs[batter] = batter_runs.get(batter, 0) + runs
            
            if batter_runs:
                top_score = max(batter_runs.values())
                records.append({
                    'venue': venue,
                    'date': date,
                    'year': date.year,
                    'team': team,
                    'top_score': top_score
                })
    return pd.DataFrame(records)

df = parse_all_innings(EXTRACT_PATH)
```

---

### Step 3: Ground name cleaning

Cricsheet venue strings are inconsistent across 148 years. Map variants to canonical names:

```python
GROUND_MAP = {
    # MCG
    'Melbourne Cricket Ground': 'MCG',
    # Gabba
    'Brisbane Cricket Ground': 'Gabba',
    'The Gabba': 'Gabba',
    'Woolloongabba': 'Gabba',
    # Lords
    "Lord's": "Lord's",
    "Lord's Cricket Ground": "Lord's",
    # Headingley
    'Headingley': 'Headingley',
    'Headingley Cricket Ground': 'Headingley',
    # Eden Gardens
    'Eden Gardens': 'Eden Gardens',
}

df['ground'] = df['venue'].map(GROUND_MAP)
df_grounds = df[df['ground'].notna()]
```

**Note for Windsurf:** Print `df['venue'].value_counts()` after parsing to catch any missed variants before filtering.

---

### Step 4: Annual Maxima Series per ground

```python
# Highest individual score at each ground in each calendar year
ams = (df_grounds
       .groupby(['ground', 'year'])['top_score']
       .max()
       .reset_index()
       .rename(columns={'top_score': 'ams'}))
```

---

### Step 5: GEV fit and epoch comparison

```python
from scipy.stats import genextreme
import numpy as np

EPOCH_SPLIT = 1980  # Pre/post split — adjust after inspecting the record

grounds = ['MCG', 'Gabba', "Lord's", 'Headingley', 'Eden Gardens']

results = {}
for ground in grounds:
    sub = ams[ams['ground'] == ground].dropna()
    pre  = sub[sub['year'] < EPOCH_SPLIT]['ams']
    post = sub[sub['year'] >= EPOCH_SPLIT]['ams']
    
    results[ground] = {
        'all':  genextreme.fit(sub['ams']),
        'pre':  genextreme.fit(pre) if len(pre) >= 10 else None,
        'post': genextreme.fit(post) if len(post) >= 10 else None,
        'data': sub
    }
```

---

### Step 6: Plotting — five-panel frequency curves

One panel per ground. Each panel shows:
- Full record GEV curve (navy)
- Pre-epoch curve (steel blue, dashed)
- Post-epoch curve (orange, dashed)
- Observed AMS scatter points coloured by era
- Ground record annotated (the PMF analogue)
- 90% confidence bands via bootstrap

X-axis: AEP (0.5 to 0.001), log scale, right-to-left convention matching ARR
Y-axis: Innings score (runs), linear

Use WRM corporate palette: `['#1e4164', '#8dc63f', '#00928f', '#e85d26']`

```python
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

fig = plt.figure(figsize=(18, 14))
gs = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.3)

axes = [fig.add_subplot(gs[0,0]), fig.add_subplot(gs[0,1]),
        fig.add_subplot(gs[0,2]), fig.add_subplot(gs[1,0]),
        fig.add_subplot(gs[1,1])]

aep_range = np.logspace(np.log10(0.5), np.log10(0.001), 200)

for ax, ground in zip(axes, grounds):
    r = results[ground]
    data = r['data']
    
    # Full record curve
    c, loc, scale = r['all']
    q_all = genextreme.ppf(1 - aep_range, c, loc, scale)
    ax.semilogx(aep_range, q_all, color='#1e4164', lw=2.5, label='Full record')
    
    # Era curves
    if r['pre']:
        q_pre = genextreme.ppf(1 - aep_range, *r['pre'])
        ax.semilogx(aep_range, q_pre, color='#00539b',
                    lw=1.5, ls='--', label=f'Pre-{EPOCH_SPLIT}')
    if r['post']:
        q_post = genextreme.ppf(1 - aep_range, *r['post'])
        ax.semilogx(aep_range, q_post, color='#e85d26',
                    lw=1.5, ls='--', label=f'Post-{EPOCH_SPLIT}')
    
    # Scatter — Weibull plotting positions
    sorted_ams = data['ams'].sort_values(ascending=False).reset_index(drop=True)
    n = len(sorted_ams)
    aep_plot = (np.arange(1, n+1)) / (n + 1)
    colours = ['#e85d26' if y >= EPOCH_SPLIT else '#00539b'
               for y in data.sort_values('ams', ascending=False)['year']]
    ax.scatter(aep_plot, sorted_ams, c=colours, zorder=5, s=25, alpha=0.7)
    
    # Ground record annotation
    record_score = data['ams'].max()
    record_year  = data.loc[data['ams'].idxmax(), 'year']
    ax.axhline(record_score, color='#c9a227', lw=1, ls=':', alpha=0.8)
    ax.text(0.003, record_score + 3,
            f'Ground record: {record_score} ({record_year})',
            fontsize=7, color='#c9a227')
    
    ax.set_title(ground, fontsize=12, fontweight='bold', color='#1e4164')
    ax.set_xlabel('Annual Exceedance Probability', fontsize=9)
    ax.set_ylabel('Highest innings score (runs)', fontsize=9)
    ax.invert_xaxis()
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3, which='both')

# Use the spare sixth panel for a summary text box
ax6 = fig.add_subplot(gs[1,2])
ax6.axis('off')
ax6.text(0.05, 0.95,
    "METHOD NOTE\n\n"
    "Each ground treated as a stream gauge.\n"
    "AMS = highest individual innings per\n"
    "calendar year at that ground.\n\n"
    "GEV fitted by MLE (scipy.stats).\n"
    "Epoch split at 1980 — pre/post\n"
    "limited-overs era.\n\n"
    "Shift in GEV location parameter (μ)\n"
    "indicates non-stationarity.\n\n"
    "Ground record = PMF analogue.\n\n"
    "Data: Cricsheet (all Tests, JSON)\n"
    "GEV fits illustrative — not peer reviewed.\n"
    "A water resources engineer's Sunday\n"
    "thought experiment.",
    transform=ax6.transAxes,
    va='top', fontsize=8.5,
    fontfamily='monospace',
    color='#1e4164',
    bbox=dict(boxstyle='round', facecolor='#f0f4f8', alpha=0.8))

fig.suptitle(
    "Cricket Grounds as Hydrological Gauges\n"
    "GEV Flood Frequency Analysis of Annual Maxima Series — Five Test Venues",
    fontsize=14, fontweight='bold', color='#1e4164', y=0.98)

plt.savefig('ground_frequency_curves.png', dpi=150,
            bbox_inches='tight', facecolor='white')
plt.show()
```

---

### Things to watch for in Windsurf

- **Short records:** The Gabba only from 1931, and not every year has a Test. If fewer than 15 data points in either epoch, skip the split and just fit the full record.
- **Venue name variants:** Run `df['venue'].value_counts()` and inspect manually before finalising the ground map. Cricsheet uses historical venue names that change over time.
- **Epoch choice:** 1980 (limited-overs era begins to influence approach) is a reasonable first cut. You could also try 2000 (T20 generation) or 2005 (Bazball precursors). Worth plotting all three splits for the MCG which has the longest record.
- **The England drought signal:** For Lord's and Headingley, if you colour the post-2010 AMS points differently you should be able to see whether Australian scores at those grounds have declined — that is your drought framing.

