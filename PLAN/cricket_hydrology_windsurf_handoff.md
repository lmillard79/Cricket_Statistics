# Windsurf Handoff: Cricket as a Hydrological Surrogate
## LinkedIn Content Project — April 2026

---

## Project Context

This is a thought experiment for a LinkedIn post aimed at water resources practitioners, planners, and engineers. The framing uses Test cricket batting statistics as a surrogate dataset to illustrate concepts from extreme value hydrology: non-stationarity, GEV distribution fitting, IFD relationships, and the physical limits argument underlying Probable Maximum Precipitation (PMP) / Probable Maximum Flood (PMF).

**Core insight driving the analysis:**

> Maximum Precipitable Water (runs per over) never produces a Probable Maximum Flood (20 overs of 6s). You cannot sustain maximum intensity for maximum duration. The PMP/PMF critique lives inside the cricket analogy.

This is the analytical centrepiece. The plots must make this visible.

**Audience:** Water engineers and hydrologists primarily. Cricket fans secondarily. Indian and Pakistani followers are a significant segment — Tendulkar is a deliberate hook.

---

## Data Sources

### Primary: Cricsheet
- URL: https://cricsheet.org/downloads/
- Download the **Tests** dataset (ball-by-ball CSV format)
- Contains all Test matches from 1877 to present
- Filter to: Bradman, Tendulkar, Smith innings records

### Secondary: ESPNcricinfo (for verification)
- Bradman career: https://www.espncricinfo.com/cricketers/don-bradman-1234
- Tendulkar career: https://www.espncricinfo.com/cricketers/sachin-tendulkar-35320
- Smith career: https://www.espncricinfo.com/cricketers/steve-smith-267192

### Key statistics to extract per player (per innings):
- Runs scored
- Balls faced
- Strike rate (runs per 100 balls)
- Match date (for time-series / non-stationarity)
- Dismissed or not out

### Annual Maxima Series construction:
```python
# Cricket seasons run Oct–Sep in Australia
# For international records, use calendar year or career phase
df['Season'] = df['Date'].apply(
    lambda x: x.year if x.month < 10 else x.year + 1
)
ams = df.groupby('Season')['Runs'].max().reset_index()
```

---

## Hydrological Surrogate Framework

| Hydrological Concept | Cricket Surrogate |
|---|---|
| Catchment | Individual batsman |
| Rainfall event | Individual innings |
| Runoff volume (mm) | Runs scored |
| Rainfall intensity (mm/hr) | Strike rate (runs per 100 balls) |
| Storm duration (hrs) | Balls faced |
| Annual Maxima Series | Peak innings score per season |
| GEV distribution | Fitted to career AMS |
| IFD curve | Strike rate vs balls faced envelope |
| Loss model | Dot balls, defensive play (infiltration/storage) |
| Maximum Precipitable Water | Maximum sustainable strike rate |
| Probable Maximum Flood | Theoretical maximum innings score |

---

## The PMF / PMP Insight — Core Analytical Story

**The argument to make visible in the plots:**

PMP is derived from maximum precipitable water in an atmospheric column combined with maximum wind convergence. The physical argument is that you cannot sustain both simultaneously for an extended duration. Hence PMP is a theoretical ceiling, not an observed event.

The cricket equivalent: a batsman cannot sustain T20 strike rates (>150) for a Test innings duration (300+ balls). Maximum intensity decays with duration. The IFD relationship captures this.

**What this means for each player:**

- **Bradman**: Extreme outlier in volume (runs). His career average of 99.94 sits impossibly far into the tail — like a gauge record with a single 1-in-10,000 event distorting the GEV fit. But his strike rate (~60) was not extreme by modern standards. High volume, moderate intensity, long duration.

- **Tendulkar**: The long record. 200 Tests, 329 innings. Reliable high-volume events. The workhorse gauge station. Strike rate ~54 over career — the steady, sustained event, not the flash flood.

- **Smith**: The modern era comparison. Higher strike rate than Tendulkar (~65), shorter career to date, record spanning the non-stationarity break point (pre/post Bazball era). Useful for showing regime shift.

**The PMF plot to make:** Strike rate (intensity) on y-axis, balls faced (duration) on x-axis, each innings as a scatter point. The upper-right corner (high intensity AND high duration) should be empty. That empty space IS the PMF argument. Draw an envelope curve along the upper boundary. Label it "Theoretical Maximum Innings (PMF equivalent)."

---

## Plots Required

### Plot 1: Annual Maxima Series — Career Hydrographs
**Type:** Line/scatter, three panels or overlaid  
**X-axis:** Season / career year  
**Y-axis:** Peak innings score (runs) — equivalent to annual peak flow  
**Series:** Bradman (WRM Blue #1e4164), Tendulkar (WRM Green #8dc63f), Smith (WRM Teal #00928f)  
**Annotations:** Bradman's 334 at Leeds 1930 (label as "Record flood event"). Tendulkar's 248* vs Bangladesh (label as "Prolonged high-flow event").  
**Style note:** Treat like a hydrograph. Use markers at data points. Grid on.

---

### Plot 2: GEV Flood Frequency Curves
**Type:** Log-linear frequency plot  
**X-axis:** Annual Exceedance Probability (log scale: 0.5 to 0.001) — label as "Annual Exceedance Probability (AEP)"  
**Y-axis:** Innings score (runs) — label as "Design Innings Score (runs)"  
**Series:** GEV fit for each player, with 90% confidence bounds as shaded bands  
**Key annotation:** Mark Bradman's 334 on his curve and label its implied AEP ("~1 in 400 AEP"). Mark Tendulkar's 248* similarly.  
**Bradman note:** His GEV fit will have an extreme shape parameter. Note this in a text box: "GEV shape parameter suggests unbounded upper tail — consistent with outlier record."  
**Style:** WRM colour palette. Log x-axis. Grid on.

```python
from scipy.stats import genextreme
import numpy as np

shape, loc, scale = genextreme.fit(ams_runs)
aep_values = np.logspace(-3, -0.3, 200)
quantiles = genextreme.ppf(1 - aep_values, shape, loc, scale)
```

---

### Plot 3: Intensity–Duration Envelope (The PMF Plot)
**Type:** Scatter with envelope curve  
**X-axis:** Balls faced (duration) — label as "Innings Duration (balls faced)"  
**Y-axis:** Strike rate (runs per 100 balls) — label as "Scoring Intensity (runs per 100 balls)"  
**Data:** Every innings for all three players (filter: minimum 20 balls faced to remove tail-enders)  
**Colour by player:** Bradman, Tendulkar, Smith in WRM colours  
**Envelope curve:** Fit a upper boundary curve (convex hull or quantile regression at 95th percentile). This is the "IFD envelope" — the PMF analogue.  
**The empty upper-right corner:** Annotate with: "Probable Maximum Innings — theoretically possible, never observed"  
**Secondary annotation:** Add a horizontal dashed line at SR=150 labelled "T20 baseline intensity". Very few Test innings breach this at duration >100 balls.  
**This is the hero plot.** Make it the largest of the three.

---

### Plot 4: IFD Table (optional, for infographic version)
Reproduce the standard ARR IFD table format but with cricket variables:

| AEP | Bradman Design Score | Tendulkar Design Score | Smith Design Score |
|---|---|---|---|
| 50% (1 in 2) | ~70 | ~55 | ~60 |
| 20% (1 in 5) | ~150 | ~100 | ~110 |
| 10% (1 in 10) | ~200 | ~130 | ~140 |
| 2% (1 in 50) | ~280 | ~170 | ~185 |
| 1% (1 in 100) | ~310 | ~190 | ~205 |

*Values are illustrative pending fitted GEV results from actual data.*

---

## Styling Requirements

### Corporate Palette (WRM Water & Environment)
```python
wrmcol = ['WRM Green', 'WRM Teal', 'WRM Blue', 'Bright Blue', 'Bright Teal', 'Charcoal', 'Citrus', 'Light orange', 'Sky']
WRM    = ['#8dc63f',   '#00928f',  '#1e4164',  '#00539b',     '#00b49d',     '#485253',  '#d7df23', '#d3bd2a',      '#6dcff6']
```

### Standard rcParams
```python
import matplotlib as mpl
from matplotlib import cycler

def setup_wrm_style():
    mpl.rcParams['axes.prop_cycle'] = cycler('color', [
        '#8dc63f', '#00928f', '#1e4164', '#00539b', '#00b49d',
        '#485253', '#d7df23', '#d3bd2a', '#6dcff6'
    ])
    mpl.rcParams['figure.figsize']   = [10, 6]
    mpl.rcParams['figure.dpi']       = 200
    mpl.rcParams['savefig.dpi']      = 200
    mpl.rcParams['font.family']      = 'sans-serif'  # Calibri if available
    mpl.rcParams['font.size']        = 10
    mpl.rcParams['legend.fontsize']  = 'small'
    mpl.rcParams['figure.titlesize'] = 'medium'
    mpl.rcParams['grid.color']       = '0.7'
    mpl.rcParams['grid.linestyle']   = '--'
    mpl.rcParams['grid.linewidth']   = 0.5
    mpl.rcParams['axes.titlepad']    = 20

setup_wrm_style()
```

### Figure Checklist
- [ ] `setup_wrm_style()` called before any figure
- [ ] Colours from WRM palette only
- [ ] DPI 200 for screen and save
- [ ] Grid on, dashed, 0.5 linewidth
- [ ] `tight_layout()` applied
- [ ] All axes labelled with units in parentheses
- [ ] Legend present if more than one series
- [ ] Footer text: *"A water resources engineer's Sunday thought experiment. GEV fits illustrative — not peer reviewed."*

---

## Tone and Framing Notes

This is deliberately playful but technically rigorous. The joke is that the methodology is real. Use real hydrological terminology throughout. The fun comes from applying it straight-faced to cricket, not from winking at the audience.

The LinkedIn post will reference these plots directly. The hero line is:

> Maximum precipitable water (runs per over) never produces a probable maximum flood. You cannot sustain maximum intensity for maximum duration. The upper-right corner of the intensity-duration plot is empty. That empty space is the PMF argument.

The plots must make that empty corner visible and annotated. Everything else is supporting evidence.

---

## Output Files

Deliver as:
1. `cricket_hydrology_analysis.py` — standalone script, fully commented
2. `plot1_annual_maxima.png` — 200 dpi
3. `plot2_gev_frequency.png` — 200 dpi  
4. `plot3_intensity_duration_envelope.png` — 200 dpi (hero plot, 12x7 inches)
5. `ifd_table.csv` — GEV quantiles for all three players

---

*Project: LinkedIn thought leadership series — Water Resources Engineering*  
*Author: Principal Water Engineer, Brisbane QLD*  
*Date: April 2026*
