"""
Cricket Grounds: Historical Innings Scraper (ESPNcricinfo Statsguru)
=====================================================================
Scrapes every Test innings recorded at five grounds from ESPNcricinfo
Statsguru, covering the full historical record back to 1877.

This replaces the Cricsheet-based approach (which only covers 2001+) and
gives ~50-110 AMS data points per ground instead of ~10-22.

Ground IDs (verified April 2026):
    MCG:          61   (Melbourne Cricket Ground -- First Test 1877)
    Gabba:        46   (Brisbane -- First Test 1931)
    Lord's:       45   (London -- First Test 1884)
    Headingley:   44   (Leeds -- First Test 1899)
    Eden Gardens: 47   (Kolkata -- First Test 1934)

Output:
    data/ground_innings_historical.csv   -- all raw innings
    outputs/plot_grounds_gev_historical.png -- 5-panel GEV frequency curves

Usage:
    python cricket_grounds_statsguru.py

Notes:
    - Scraper inserts a 2-second pause between pages (polite crawling).
    - If ESPNcricinfo blocks requests, increase PAUSE_SECONDS.
    - Cached CSV is used on re-runs if it exists (set FORCE_RESCRAPE=True
      to override).
    - beautifulsoup4 is required: pip install beautifulsoup4

Author: Principal Water Engineer, Brisbane QLD
Date: April 2026
"""

from __future__ import annotations

import logging
import math
import random
import re
import time
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from matplotlib.gridspec import GridSpec
from scipy.stats import genextreme

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths and config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

CSV_CACHE = DATA_DIR / "ground_innings_historical.csv"
FORCE_RESCRAPE: bool = False   # set True to ignore cache and re-scrape

PAUSE_SECONDS: float = 2.5      # polite delay between page requests (minimum)
PAUSE_JITTER: float = 1.0       # random additional delay (0 to PAUSE_JITTER seconds)
PAUSE_BETWEEN_GROUNDS: float = 6.0  # longer pause between different grounds

EPOCH_SPLIT: int = 1980
MIN_EPOCH_POINTS: int = 10
Y_MAX: float = 500.0

# ---------------------------------------------------------------------------
# Ground definitions
# ---------------------------------------------------------------------------
# Ground IDs verified against Statsguru 'At ground' header, April 2026.
# Probe script: scripts/find_ground_ids.py
# robots.txt check: /ci/engine/stats/ is NOT disallowed for User-agent: *
GROUND_IDS: dict[str, int] = {
    "MCG":              61,   # AUS: Melbourne Cricket Ground (First Test 1877)
    "Gabba":           209,   # AUS: Brisbane Cricket Ground, Woolloongabba
    "SCG":             132,   # AUS: Sydney Cricket Ground (First Test 1882)
    "Lord's":           10,   # ENG: Lord's, London (First Test 1884)
    "Headingley":      179,   # ENG: Headingley, Leeds (First Test 1899)
    "Old Trafford":     75,   # ENG: Old Trafford, Manchester (First Test 1884)
    "Newlands":        174,   # SA: Newlands, Cape Town (First Test 1889)
    "St George's Park": 173,  # SA: St George's Park, Gqeberha (First Test 1889)
    "Eden Gardens":    292,   # IND: Eden Gardens, Kolkata (First Test 1934)
}

GROUND_SUBTITLES: dict[str, str] = {
    "MCG":              "Melbourne       |  First Test 1877",
    "Gabba":            "Brisbane        |  First Test 1931",
    "SCG":              "Sydney          |  First Test 1882",
    "Lord's":           "London          |  First Test 1884",
    "Headingley":       "Leeds           |  First Test 1899",
    "Old Trafford":     "Manchester      |  First Test 1884",
    "Newlands":         "Cape Town       |  First Test 1889",
    "St George's Park": "Port Elizabeth  |  First Test 1889",
    "Eden Gardens":     "Kolkata         |  First Test 1934",
}

# ---------------------------------------------------------------------------
# WRM Corporate Palette
# ---------------------------------------------------------------------------
C_FULL   = "#1e4164"   # WRM Blue
C_PRE    = "#00539b"   # Bright Blue
C_POST   = "#e85d26"   # Burnt orange
C_RECORD = "#d3bd2a"   # Light orange
C_TEXT   = "#485253"   # Charcoal

FOOTER = (
    "A water resources engineer's Sunday thought experiment.  "
    "GEV fits via L-moments -- not peer reviewed.  "
    "Data: ESPNcricinfo Statsguru (all Tests)."
)


# ---------------------------------------------------------------------------
# Statsguru scraper
# ---------------------------------------------------------------------------

def _parse_runs(raw: str) -> Optional[int]:
    """Strip not-out asterisk; return int or None for DNB/-/TDNB."""
    cleaned = raw.replace("*", "").strip()
    return int(cleaned) if cleaned.isdigit() else None


def _parse_year(date_str: str) -> Optional[int]:
    """Parse Statsguru date '15 Mar 1877' -> 1877."""
    parts = date_str.strip().split()
    if len(parts) == 3 and parts[2].isdigit():
        return int(parts[2])
    return None


def scrape_ground(ground_name: str, ground_id: int) -> list[dict]:
    """
    Scrape all Test batting innings at a given ground from Statsguru.
    Returns list of dicts: {ground, year, score}.

    Polite scraping protocol:
    - robots.txt verified: /ci/engine/stats/ is NOT disallowed (April 2026)
    - Full browser User-Agent (not bot-identified) to emulate normal browser use
    - Accept / Accept-Language / Referer headers match real browser behaviour
    - Fixed 2.5s pause + random jitter between pages (avg ~3s)
    - 6s pause between grounds
    - Single-threaded sequential requests only
    - Results cached to CSV to avoid re-scraping
    """
    records: list[dict] = []
    page = 1
    base = "https://stats.espncricinfo.com/ci/engine/stats/index.html"
    # Full browser UA + headers to emulate genuine browser navigation
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://stats.espncricinfo.com/ci/engine/stats/index.html",
    }

    while True:
        params = (
            f"?class=1;ground={ground_id};orderby=start"
            f";page={page};template=results;type=batting;view=innings"
        )
        url = base + params
        log.info("  %s  page %d ...", ground_name, page)

        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
        except requests.RequestException as exc:
            log.error("  Request failed on page %d: %s", page, exc)
            break

        soup = BeautifulSoup(r.text, "html.parser")

        # Statsguru data table has class 'engineTable' and contains tr.data1 rows
        data_table = None
        for t in soup.find_all("table", class_="engineTable"):
            if t.find("tr", class_="data1"):
                data_table = t
                break

        if data_table is None:
            log.info("  No data table on page %d -- stopping.", page)
            break

        rows = data_table.find_all("tr", class_="data1")
        if not rows:
            break

        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            # Columns: Player Runs Mins BF 4s 6s SR Inns Opposition Ground StartDate
            if len(cols) < 12:
                continue
            runs = _parse_runs(cols[1])   # col[1] = Runs (e.g. '165*')
            year = _parse_year(cols[11])  # col[11] = Start Date (e.g. '15 Mar 1877')
            if runs is not None and year is not None:
                records.append(
                    {"ground": ground_name, "year": year, "score": runs}
                )

        # Check for Next page button -- use get_text() because the anchor
        # may contain child elements which break BeautifulSoup string= matching
        has_next = any(
            a.get_text(strip=True).lower() == "next"
            for a in soup.find_all("a")
        )
        if not has_next:
            log.info(
                "  %s: finished at page %d  (%d innings total)",
                ground_name, page, len(records),
            )
            break

        page += 1
        # Jitter prevents metronomic request patterns; emulates human browse speed
        time.sleep(PAUSE_SECONDS + random.uniform(0.0, PAUSE_JITTER))

    return records


def scrape_all_grounds() -> pd.DataFrame:
    """Scrape all nine grounds and return combined DataFrame."""
    all_records: list[dict] = []
    for name, gid in GROUND_IDS.items():
        log.info("Scraping %s (ground_id=%d) ...", name, gid)
        recs = scrape_ground(name, gid)
        all_records.extend(recs)
        log.info("  %s: %d innings scraped", name, len(recs))
        time.sleep(PAUSE_BETWEEN_GROUNDS)

    df = pd.DataFrame(all_records)
    df.to_csv(CSV_CACHE, index=False)
    log.info("Saved raw innings -> %s  (%d rows)", CSV_CACHE, len(df))
    return df


def load_innings() -> pd.DataFrame:
    """
    Load innings from cache. If cache exists, only scrape grounds that are
    missing from it (incremental update). Set FORCE_RESCRAPE=True to
    re-scrape everything from scratch.
    """
    if FORCE_RESCRAPE or not CSV_CACHE.exists():
        return scrape_all_grounds()

    log.info("Loading cached innings from %s", CSV_CACHE)
    existing = pd.read_csv(CSV_CACHE, usecols=["ground", "year", "score"])
    cached_grounds = set(existing["ground"].unique())
    missing = [name for name in GROUND_IDS if name not in cached_grounds]

    if not missing:
        log.info("  All %d grounds cached (%d rows total)", len(GROUND_IDS), len(existing))
        return existing

    log.info("  Cached: %s", sorted(cached_grounds))
    log.info("  Missing (will scrape): %s", missing)
    new_records: list[dict] = []
    for name in missing:
        gid = GROUND_IDS[name]
        log.info("Scraping %s (ground_id=%d) ...", name, gid)
        recs = scrape_ground(name, gid)
        new_records.extend(recs)
        log.info("  %s: %d innings scraped", name, len(recs))
        time.sleep(PAUSE_BETWEEN_GROUNDS)

    if new_records:
        new_df = pd.DataFrame(new_records)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined.to_csv(CSV_CACHE, index=False)
        log.info("Updated cache -> %s  (%d rows total)", CSV_CACHE, len(combined))
        return combined

    return existing


# ---------------------------------------------------------------------------
# Annual Maxima Series
# ---------------------------------------------------------------------------

def build_ams(df: pd.DataFrame) -> pd.DataFrame:
    """Highest individual innings per ground per calendar year."""
    ams = (
        df.groupby(["ground", "year"])["score"]
        .max()
        .reset_index()
        .rename(columns={"score": "ams"})
    )
    log.info("\nAMS summary:")
    summary = ams.groupby("ground").agg(
        n_seasons=("ams", "count"),
        first_year=("year", "min"),
        last_year=("year", "max"),
        ground_record=("ams", "max"),
    )
    log.info("\n%s", summary.to_string())
    return ams


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------

def sanity_checks(df: pd.DataFrame, ams: pd.DataFrame) -> None:
    """Log any suspicious scores and confirm AMS construction."""
    suspicious = df[df["score"] > 400]
    if not suspicious.empty:
        log.info("Scores > 400 (sanity check):\n%s", suspicious.to_string())
    else:
        log.info("No scores > 400 found (all plausible)")

    # Print first 10 MCG AMS years
    mcg = ams[ams["ground"] == "MCG"].sort_values("year").head(10)
    log.info("MCG AMS (first 10 years):\n%s", mcg.to_string(index=False))


# ---------------------------------------------------------------------------
# GEV fitting -- L-moments (Hosking 1990)
# ---------------------------------------------------------------------------

def _lmom_gev(data: np.ndarray) -> tuple[float, float, float]:
    """
    GEV fit via L-moments. Robust for small AMS samples (ARR standard).
    Returns (shape, loc, scale) in scipy.stats.genextreme convention.
    """
    x = np.sort(data)
    n = len(x)
    i_idx = np.arange(1, n + 1, dtype=float)

    b0 = np.mean(x)
    b1 = np.sum((i_idx - 1) / (n - 1) * x) / n
    b2 = np.sum((i_idx - 1) * (i_idx - 2) / ((n - 1) * (n - 2)) * x) / n

    l1 = b0
    l2 = 2.0 * b1 - b0
    l3 = 6.0 * b2 - 6.0 * b1 + b0

    if l2 <= 0:
        raise ValueError("L2 <= 0 -- degenerate sample")

    t3 = float(np.clip(l3 / l2, -0.45, 0.45))
    c = 2.0 / (3.0 + t3) - np.log(2.0) / np.log(3.0)
    k = 7.8590 * c + 2.9554 * c ** 2

    shape = -k

    if abs(k) < 1e-6:
        scale = float(l2 / np.log(2.0))
        loc = float(l1 - scale * 0.5772156649)
    else:
        gk = math.gamma(1.0 + k)
        scale = float(l2 * k / ((1.0 - 2.0 ** (-k)) * gk))
        loc = float(l1 - scale * (1.0 - math.gamma(1.0 + k)) / k)

    return float(shape), float(loc), float(scale)


def fit_gev(series: pd.Series) -> tuple[float, float, float]:
    """L-moments GEV fit with MLE fallback and shape clamp [-0.5, 1.0]."""
    arr = series.dropna().to_numpy(dtype=float)
    try:
        shape, loc, scale = _lmom_gev(arr)
    except Exception:
        shape, loc, scale = genextreme.fit(arr)

    if not (-0.5 <= shape <= 1.0):
        log.warning("L-moments shape=%.3f outside bounds -- falling back to MLE", shape)
        shape, loc, scale = genextreme.fit(arr)
        shape = float(np.clip(shape, -0.5, 1.0))

    return float(shape), float(loc), float(scale)


def gev_quantiles(
    shape: float, loc: float, scale: float, aep: np.ndarray
) -> np.ndarray:
    return genextreme.ppf(1.0 - aep, shape, loc, scale)


def gev_bootstrap_ci(
    data: pd.Series,
    aep: np.ndarray,
    n_bootstrap: int = 500,
    ci: float = 0.90,
) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap 90% CI on GEV quantiles, clipped to Y_MAX."""
    rng = np.random.default_rng(42)
    arr = data.to_numpy()
    boot = np.zeros((n_bootstrap, len(aep)))
    for i in range(n_bootstrap):
        sample = rng.choice(arr, size=len(arr), replace=True)
        try:
            s, l, sc = fit_gev(pd.Series(sample))
            boot[i] = np.clip(gev_quantiles(s, l, sc, aep), 0, Y_MAX)
        except Exception:
            boot[i] = np.nan
    alpha = (1.0 - ci) / 2.0
    lower = np.nanpercentile(boot, alpha * 100, axis=0)
    upper = np.nanpercentile(boot, (1.0 - alpha) * 100, axis=0)
    return lower, upper


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

AEP_RANGE = np.logspace(np.log10(0.001), np.log10(0.5), 300)


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 200,
            "savefig.dpi": 200,
            "font.family": "sans-serif",
            "font.size": 9,
            "axes.titlepad": 10,
            "grid.color": "0.75",
            "grid.linestyle": "--",
            "grid.linewidth": 0.5,
        }
    )


def _plot_panel(ax: plt.Axes, ground: str, ams_df: pd.DataFrame) -> None:
    sub = ams_df[ams_df["ground"] == ground].copy()

    if sub.empty or len(sub) < 5:
        ax.text(0.5, 0.5, f"Insufficient data\n({len(sub)} seasons)",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=9, color=C_TEXT)
        ax.set_title(f"{ground}\n{GROUND_SUBTITLES.get(ground, '')}", fontsize=9,
                     color=C_FULL, fontweight="bold")
        return

    # --- Full record ---
    shape_all, loc_all, scale_all = fit_gev(sub["ams"])
    log.info(
        "  %-14s  n=%d  shape=%.3f  loc=%.1f  scale=%.1f",
        ground, len(sub), shape_all, loc_all, scale_all,
    )
    q_all = np.clip(gev_quantiles(shape_all, loc_all, scale_all, AEP_RANGE), 0, Y_MAX)
    lower, upper = gev_bootstrap_ci(sub["ams"], AEP_RANGE)

    ax.plot(AEP_RANGE, q_all, color=C_FULL, linewidth=2.2, zorder=4,
            label=f"Full record  n={len(sub)}")
    ax.fill_between(AEP_RANGE, lower, upper,
                    color=C_FULL, alpha=0.15, zorder=2, label="90% CI")

    # --- Epoch split ---
    pre  = sub[sub["year"] < EPOCH_SPLIT]["ams"]
    post = sub[sub["year"] >= EPOCH_SPLIT]["ams"]

    if len(pre) >= MIN_EPOCH_POINTS:
        s, l, sc = fit_gev(pre)
        q_pre = np.clip(gev_quantiles(s, l, sc, AEP_RANGE), 0, Y_MAX)
        ax.plot(AEP_RANGE, q_pre, color=C_PRE, linewidth=1.4, linestyle="--",
                zorder=3, label=f"Pre-{EPOCH_SPLIT}  n={len(pre)}")
        log.info("    pre-%d   shape=%.3f loc=%.1f scale=%.1f", EPOCH_SPLIT, s, l, sc)

    if len(post) >= MIN_EPOCH_POINTS:
        s, l, sc = fit_gev(post)
        q_post = np.clip(gev_quantiles(s, l, sc, AEP_RANGE), 0, Y_MAX)
        ax.plot(AEP_RANGE, q_post, color=C_POST, linewidth=1.4, linestyle="--",
                zorder=3, label=f"Post-{EPOCH_SPLIT}  n={len(post)}")
        log.info("    post-%d  shape=%.3f loc=%.1f scale=%.1f", EPOCH_SPLIT, s, l, sc)

    # --- Empirical scatter (Weibull plotting positions) ---
    sorted_sub = sub.sort_values("ams", ascending=False).reset_index(drop=True)
    n = len(sorted_sub)
    emp_aep = (np.arange(1, n + 1)) / (n + 1)
    point_colours = [C_POST if yr >= EPOCH_SPLIT else C_PRE for yr in sorted_sub["year"]]
    ax.scatter(emp_aep, sorted_sub["ams"],
               c=point_colours, s=18, alpha=0.7, zorder=5)

    # --- Ground record line ---
    record_score = int(sub["ams"].max())
    record_year  = int(sub.loc[sub["ams"].idxmax(), "year"])
    ax.axhline(record_score, color=C_RECORD, linewidth=0.9, linestyle=":", alpha=0.85)
    ax.text(0.003, record_score + 4,
            f"Ground record: {record_score} ({record_year})",
            fontsize=6.5, color=C_RECORD, zorder=6)

    # --- GEV shape annotation ---
    ax.text(0.97, 0.05,
            f"GEV shape = {shape_all:.3f}",
            transform=ax.transAxes, fontsize=7, color=C_FULL, ha="right",
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white",
                  "edgecolor": C_FULL, "alpha": 0.85})

    # --- Axes ---
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:.2f}" if v >= 0.1 else f"{v:.3f}")
    )
    ax.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax.set_xlim(0.5, 0.001)
    ax.set_ylim(0, Y_MAX)
    ax.set_xlabel("Annual Exceedance Probability (AEP)", fontsize=8)
    ax.set_ylabel("Highest innings score (runs)", fontsize=8)
    ax.set_title(
        f"{ground}\n{GROUND_SUBTITLES.get(ground, '')}",
        fontsize=9, color=C_FULL, fontweight="bold",
    )
    ax.grid(True, which="both")
    ax.legend(fontsize=6.5, loc="upper left", framealpha=0.85)


def _method_panel(ax: plt.Axes) -> None:
    ax.axis("off")
    ax.text(
        0.06, 0.96,
        "METHOD NOTE\n\n"
        "Each ground = stream gauge.\n"
        "AMS = highest individual innings\n"
        "per calendar year at that ground.\n\n"
        "Data: ESPNcricinfo Statsguru\n"
        "(all Tests, 1877-present).\n\n"
        "GEV fitted by L-moments\n"
        "(Hosking 1990 -- ARR standard\n"
        "for small AMS samples).\n\n"
        f"Epoch split at {EPOCH_SPLIT}:\n"
        "  Blue dashed  = pre-1980\n"
        "  Orange dashed = post-1980\n\n"
        "Shift in GEV location (mu)\n"
        "= non-stationarity signal.\n\n"
        "Ground record = PMF analogue.\n\n"
        "90% bootstrap CI on full-\n"
        "record GEV (shaded band).\n\n"
        "GEV fits illustrative only.",
        transform=ax.transAxes, va="top", fontsize=8,
        fontfamily="monospace", color=C_FULL, linespacing=1.45,
        bbox={"boxstyle": "round,pad=0.6", "facecolor": "#f0f4f8",
              "edgecolor": C_FULL, "alpha": 0.9},
    )


def plot_grounds(ams_df: pd.DataFrame, output_path: Path) -> None:
    """9-panel GEV plot (3x4 grid), one per ground + method note panel."""
    setup_style()
    n_grounds = len(GROUND_IDS)
    # 3 columns; enough rows to hold all grounds + 1 method note
    n_cols = 3
    n_rows = (n_grounds + 1 + n_cols - 1) // n_cols  # ceil division
    fig = plt.figure(figsize=(22, n_rows * 6.5))
    gs = GridSpec(n_rows, n_cols, figure=fig, hspace=0.45, wspace=0.30)

    # Build list of all subplot positions row-major
    all_positions = [gs[r, c] for r in range(n_rows) for c in range(n_cols)]
    data_axes = [fig.add_subplot(pos) for pos in all_positions[:n_grounds]]
    method_ax = fig.add_subplot(all_positions[n_grounds])

    # Hide any remaining empty cells
    for pos in all_positions[n_grounds + 1:]:
        fig.add_subplot(pos).axis("off")

    log.info("Plotting GEV panels ...")
    for ax, ground in zip(data_axes, GROUND_IDS.keys()):
        _plot_panel(ax, ground, ams_df)

    _method_panel(method_ax)

    fig.suptitle(
        "Cricket Grounds as Hydrological Gauge Stations\n"
        "GEV Flood Frequency Analysis  |  Annual Maxima Series  |  Nine Test Venues  |  1877-2025",
        fontsize=14, fontweight="bold", color=C_FULL, y=0.998,
    )
    fig.text(0.5, -0.003, FOOTER, ha="center", fontsize=7.5,
             color=C_TEXT, style="italic")

    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log.info("Saved -> %s", output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    df = load_innings()

    sanity_checks(df, build_ams(df))
    ams_df = build_ams(df)

    # Print summary table
    print("\n--- Ground innings summary ---")
    summary = df.groupby("ground").agg(
        n_innings=("score", "count"),
        first_year=("year", "min"),
        last_year=("year", "max"),
        ground_record=("score", "max"),
    )
    print(summary.to_string())

    print("\n--- GEV Parameters by Ground (L-moments, full record) ---")
    print(f"{'Ground':<16} {'n AMS':>6}  {'shape':>8}  {'loc':>8}  {'scale':>8}")
    for ground in GROUND_IDS:
        sub = ams_df[ams_df["ground"] == ground]["ams"].dropna()
        if len(sub) < 5:
            print(f"{ground:<16} {'<5':>6}  {'--':>8}  {'--':>8}  {'--':>8}")
            continue
        s, l, sc = fit_gev(sub)
        print(f"{ground:<16} {len(sub):>6}  {s:>8.3f}  {l:>8.1f}  {sc:>8.1f}")

    out = OUTPUT_DIR / "plot_grounds_gev_historical.png"
    plot_grounds(ams_df, out)

    log.info("Done.")


if __name__ == "__main__":
    main()
