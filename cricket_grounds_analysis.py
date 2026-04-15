"""
Cricket Grounds as Hydrological Gauge Stations
===============================================
Each Test ground is treated as a long-period stream gauge.
The Annual Maxima Series (AMS) is the highest individual innings score
recorded at that ground in each calendar year.

A GEV distribution is fitted to each ground's full AMS, then the record
is split at EPOCH_SPLIT (1980) to expose non-stationarity -- analogous to
detecting a shift in catchment response after land-use change.

Grounds:
  MCG            (est. 1877 -- longest Test record in the world)
  Gabba          (est. 1931 -- Brisbane local context)
  Lord's         (est. 1884 -- "home of cricket", drought framing)
  Headingley     (est. 1899 -- Ashes drought anchor)
  Eden Gardens   (est. 1934 -- oldest Indian ground, IPL hook)

Data: Cricsheet ball-by-ball JSON (all Tests, ~2001-present).
Note: Cricsheet coverage starts 2001. Pre-2001 ground records are absent.
      The MCG 1877-2000 record is therefore truncated in this dataset.

Output: outputs/plot_grounds_gev.png

Author: Principal Water Engineer, Brisbane QLD
Date: April 2026
"""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import requests
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
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

CRICSHEET_URL = "https://cricsheet.org/downloads/tests_json.zip"
ZIP_CACHE = DATA_DIR / "tests_json.zip"
EXTRACT_DIR = DATA_DIR / "cricsheet_tests"

# ---------------------------------------------------------------------------
# Ground configuration
# ---------------------------------------------------------------------------
EPOCH_SPLIT: int = 1980
MIN_EPOCH_POINTS: int = 10   # minimum AMS points required to fit epoch curve

GROUNDS: list[str] = ["MCG", "Gabba", "Lord's", "Headingley", "Eden Gardens"]

# Cricsheet venue strings -> canonical ground name
# Confirmed against actual data: venue_counts inspection April 2026
GROUND_MAP: dict[str, str] = {
    "Melbourne Cricket Ground": "MCG",
    "Brisbane Cricket Ground, Woolloongabba": "Gabba",
    "Brisbane Cricket Ground, Woolloongabba, Brisbane": "Gabba",
    "Brisbane Cricket Ground": "Gabba",
    "Lord's": "Lord's",
    "Lord's, London": "Lord's",
    "Headingley": "Headingley",
    "Headingley, Leeds": "Headingley",
    "Eden Gardens": "Eden Gardens",
    "Eden Gardens, Kolkata": "Eden Gardens",
}

# Engagement hook subtitle per ground
GROUND_SUBTITLES: dict[str, str] = {
    "MCG":           "Melbourne  |  First Test 1877",
    "Gabba":         "Brisbane   |  First Test 1931",
    "Lord's":        "London     |  First Test 1884",
    "Headingley":    "Leeds      |  First Test 1899",
    "Eden Gardens":  "Kolkata    |  First Test 1934",
}

# ---------------------------------------------------------------------------
# WRM Corporate Palette
# ---------------------------------------------------------------------------
C_FULL    = "#1e4164"   # WRM Blue   -- full record GEV
C_PRE     = "#00539b"   # Bright Blue -- pre-epoch
C_POST    = "#e85d26"   # burnt orange (outside WRM but plan-specified)
C_RECORD  = "#d3bd2a"   # Light orange -- ground record line
C_TEXT    = "#485253"   # Charcoal

FOOTER = (
    "A water resources engineer's Sunday thought experiment.  "
    "GEV fits illustrative -- not peer reviewed.  "
    "Data: Cricsheet (Tests JSON, 2001-present)."
)


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


# ---------------------------------------------------------------------------
# Data acquisition
# ---------------------------------------------------------------------------

def download_and_extract() -> None:
    if not ZIP_CACHE.exists():
        log.info("Downloading Cricsheet Tests ...")
        r = requests.get(CRICSHEET_URL, timeout=120)
        r.raise_for_status()
        ZIP_CACHE.write_bytes(r.content)
        log.info("Saved %d MB", len(r.content) // 1_048_576)
    else:
        log.info("Using cached ZIP: %s", ZIP_CACHE)

    if EXTRACT_DIR.exists() and any(EXTRACT_DIR.iterdir()):
        log.info("Cricsheet already extracted to %s", EXTRACT_DIR)
        return
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_CACHE) as zf:
        zf.extractall(EXTRACT_DIR)
    log.info("Extracted %d files", len(list(EXTRACT_DIR.glob("*.json"))))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_ground_innings(extract_dir: Path) -> pd.DataFrame:
    """
    Parse all Cricsheet JSON files and return one row per innings played
    at any of the five target grounds.

    Returns DataFrame columns:
        ground, year, venue_raw, top_score
        where top_score = highest individual batter score in that innings.
    """
    records: list[dict] = []
    json_files = sorted(extract_dir.glob("*.json"))
    log.info("Scanning %d JSON files ...", len(json_files))

    for fpath in json_files:
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        info = data.get("info", {})
        venue_raw: str = info.get("venue", "")
        ground = GROUND_MAP.get(venue_raw)
        if ground is None:
            continue

        dates_raw = info.get("dates", [])
        if not dates_raw:
            continue
        match_date = datetime.strptime(dates_raw[0], "%Y-%m-%d")
        year: int = match_date.year

        for innings in data.get("innings", []):
            batter_runs: dict[str, int] = {}
            for over_block in innings.get("overs", []):
                for delivery in over_block.get("deliveries", []):
                    batter: Optional[str] = delivery.get("batter")
                    if batter is None:
                        continue
                    batter_runs[batter] = (
                        batter_runs.get(batter, 0)
                        + delivery.get("runs", {}).get("batter", 0)
                    )
            if batter_runs:
                records.append(
                    {
                        "ground": ground,
                        "year": year,
                        "venue_raw": venue_raw,
                        "top_score": max(batter_runs.values()),
                    }
                )

    df = pd.DataFrame(records)
    log.info(
        "Parsed %d innings records across %d grounds",
        len(df),
        df["ground"].nunique() if not df.empty else 0,
    )
    return df


# ---------------------------------------------------------------------------
# Annual Maxima Series
# ---------------------------------------------------------------------------

def build_ground_ams(innings_df: pd.DataFrame) -> pd.DataFrame:
    """Highest individual score per ground per calendar year."""
    ams = (
        innings_df.groupby(["ground", "year"])["top_score"]
        .max()
        .reset_index()
        .rename(columns={"top_score": "ams"})
    )
    for ground in GROUNDS:
        sub = ams[ams["ground"] == ground]
        log.info(
            "%-14s  AMS years: %d  (range %s-%s)  max=%d",
            ground,
            len(sub),
            int(sub["year"].min()) if not sub.empty else "n/a",
            int(sub["year"].max()) if not sub.empty else "n/a",
            int(sub["ams"].max()) if not sub.empty else 0,
        )
    return ams


# ---------------------------------------------------------------------------
# GEV utilities
# ---------------------------------------------------------------------------

def _lmom_gev(data: np.ndarray) -> tuple[float, float, float]:
    """
    Fit GEV distribution using L-moments (Hosking 1990).
    More robust than MLE for small samples (n < 30), standard in ARR.

    Returns (shape, loc, scale) matching scipy.stats.genextreme convention
    where shape > 0 = Frechet (heavy tail), shape < 0 = Weibull (bounded).
    Note: Hosking uses the opposite sign convention for shape; we negate here.
    """
    x = np.sort(data)
    n = len(x)

    # Vectorised probability weighted moments (Hosking & Wallis 1997, eq 2.2)
    i_idx = np.arange(1, n + 1, dtype=float)
    b0 = np.mean(x)
    b1 = np.sum((i_idx - 1) / (n - 1) * x) / n
    b2 = np.sum((i_idx - 1) * (i_idx - 2) / ((n - 1) * (n - 2)) * x) / n

    # L-moments
    l1 = b0
    l2 = 2.0 * b1 - b0
    l3 = 6.0 * b2 - 6.0 * b1 + b0

    if l2 <= 0:
        raise ValueError("L2 <= 0: degenerate sample")

    t3 = float(l3 / l2)  # L-skewness

    # Hosking (1990) rational approximation for GEV shape k from L-skewness
    # Valid for -0.5 <= t3 <= 0.5; clip to keep approximation valid
    t3 = float(np.clip(t3, -0.45, 0.45))
    c = 2.0 / (3.0 + t3) - np.log(2.0) / np.log(3.0)
    k = 7.8590 * c + 2.9554 * c ** 2  # Hosking k (positive = heavy tail)

    # scipy.stats.genextreme uses shape = -k
    shape = -k

    # Scale and location from L-moments
    if abs(k) < 1e-6:
        scale = float(l2 / np.log(2.0))
        loc = float(l1 - scale * 0.5772156649)
    else:
        gk = math.gamma(1.0 + k)
        scale = float(l2 * k / ((1.0 - 2.0 ** (-k)) * gk))
        loc = float(l1 - scale * (1.0 - math.gamma(1.0 + k)) / k)

    return float(shape), float(loc), float(scale)


def fit_gev(series: pd.Series) -> tuple[float, float, float]:
    """
    Fit GEV to series using L-moments (robust for small AMS samples).
    Falls back to MLE if L-moments produce an extreme shape (|k|>0.45).
    Shape is clamped to [-0.5, 1.0] to prevent physically implausible fits.
    """
    arr = series.dropna().to_numpy(dtype=float)
    try:
        shape, loc, scale = _lmom_gev(arr)
    except Exception:
        shape, loc, scale = genextreme.fit(arr)

    # Safety clamp: shape outside [-0.5, 1.0] is physically implausible for
    # cricket innings scores and indicates numerical instability.
    if not (-0.5 <= shape <= 1.0):
        log.warning(
            "L-moments shape=%.3f outside [-0.5, 1.0] -- falling back to MLE",
            shape,
        )
        shape, loc, scale = genextreme.fit(arr)
        # Second clamp after MLE if still degenerate
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
    y_max: float = 500.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap CI on GEV quantiles. Returns (lower, upper) clipped to y_max."""
    rng = np.random.default_rng(42)
    arr = data.to_numpy()
    boot = np.zeros((n_bootstrap, len(aep)))
    for i in range(n_bootstrap):
        sample = rng.choice(arr, size=len(arr), replace=True)
        try:
            s, l, sc = genextreme.fit(sample)
            boot[i] = np.clip(gev_quantiles(s, l, sc, aep), 0, y_max)
        except Exception:
            boot[i] = np.nan
    alpha = (1.0 - ci) / 2.0
    lower = np.nanpercentile(boot, alpha * 100, axis=0)
    upper = np.nanpercentile(boot, (1.0 - alpha) * 100, axis=0)
    return lower, upper


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

AEP_RANGE = np.logspace(np.log10(0.001), np.log10(0.5), 300)
Y_MAX = 500.0  # physical ceiling for axis / clipping


def _plot_ground_panel(
    ax: plt.Axes,
    ground: str,
    ams_df: pd.DataFrame,
) -> None:
    """Draw a single ground panel onto ax."""
    sub = ams_df[ams_df["ground"] == ground].copy()

    if sub.empty or len(sub) < 5:
        ax.text(0.5, 0.5, f"Insufficient data\n({len(sub)} seasons)",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=9, color=C_TEXT)
        ax.set_title(f"{ground}\n{GROUND_SUBTITLES.get(ground, '')}", fontsize=9,
                     color=C_FULL, fontweight="bold")
        return

    # --- Full record GEV ---
    shape_all, loc_all, scale_all = fit_gev(sub["ams"])
    q_all = np.clip(gev_quantiles(shape_all, loc_all, scale_all, AEP_RANGE), 0, Y_MAX)
    lower, upper = gev_bootstrap_ci(sub["ams"], AEP_RANGE, y_max=Y_MAX)

    ax.plot(AEP_RANGE, q_all, color=C_FULL, linewidth=2.2, zorder=4,
            label=f"Full record (n={len(sub)})")
    ax.fill_between(AEP_RANGE, lower, upper,
                    color=C_FULL, alpha=0.15, zorder=2, label="90% CI")

    # --- Epoch split ---
    pre  = sub[sub["year"] < EPOCH_SPLIT]["ams"]
    post = sub[sub["year"] >= EPOCH_SPLIT]["ams"]

    if len(pre) >= MIN_EPOCH_POINTS:
        s, l, sc = fit_gev(pre)
        q_pre = np.clip(gev_quantiles(s, l, sc, AEP_RANGE), 0, Y_MAX)
        ax.plot(AEP_RANGE, q_pre, color=C_PRE, linewidth=1.4, linestyle="--",
                zorder=3, label=f"Pre-{EPOCH_SPLIT} (n={len(pre)})")
        log.info("  %s pre-%d  GEV: shape=%.3f loc=%.1f scale=%.1f",
                 ground, EPOCH_SPLIT, s, l, sc)
    else:
        log.info("  %s pre-%d: only %d points -- skipping epoch fit",
                 ground, EPOCH_SPLIT, len(pre))

    if len(post) >= MIN_EPOCH_POINTS:
        s, l, sc = fit_gev(post)
        q_post = np.clip(gev_quantiles(s, l, sc, AEP_RANGE), 0, Y_MAX)
        ax.plot(AEP_RANGE, q_post, color=C_POST, linewidth=1.4, linestyle="--",
                zorder=3, label=f"Post-{EPOCH_SPLIT} (n={len(post)})")
        log.info("  %s post-%d GEV: shape=%.3f loc=%.1f scale=%.1f",
                 ground, EPOCH_SPLIT, s, l, sc)
    else:
        log.info("  %s post-%d: only %d points -- skipping epoch fit",
                 ground, EPOCH_SPLIT, len(post))

    # --- Empirical AMS scatter (Weibull plotting position) ---
    sorted_sub = sub.sort_values("ams", ascending=False).reset_index(drop=True)
    n = len(sorted_sub)
    emp_aep = (np.arange(1, n + 1)) / (n + 1)
    point_colours = [
        C_POST if yr >= EPOCH_SPLIT else C_PRE
        for yr in sorted_sub["year"]
    ]
    ax.scatter(emp_aep, sorted_sub["ams"],
               c=point_colours, s=22, alpha=0.75, zorder=5)

    # --- Ground record annotation ---
    record_score = int(sub["ams"].max())
    record_year  = int(sub.loc[sub["ams"].idxmax(), "year"])
    ax.axhline(record_score, color=C_RECORD, linewidth=0.9,
               linestyle=":", alpha=0.85, zorder=3)
    ax.text(0.003, record_score + 4,
            f"Ground record: {record_score} ({record_year})",
            fontsize=6.5, color=C_RECORD, zorder=6)

    # --- GEV parameter annotation ---
    ax.text(
        0.97, 0.05,
        f"GEV shape = {shape_all:.3f}",
        transform=ax.transAxes,
        fontsize=7, color=C_FULL, ha="right",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white",
              "edgecolor": C_FULL, "alpha": 0.85},
    )

    # --- Axes ---
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(
            lambda v, _: f"{v:.2f}" if v >= 0.1 else f"{v:.3f}"
        )
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


def _method_note_panel(ax: plt.Axes) -> None:
    """Draw the method note text panel (sixth GridSpec cell)."""
    ax.axis("off")
    ax.text(
        0.06, 0.96,
        "METHOD NOTE\n\n"
        "Each ground treated as a stream gauge.\n"
        "AMS = highest individual innings per\n"
        "calendar year at that ground.\n\n"
        "GEV fitted by MLE (scipy.stats).\n\n"
        f"Epoch split at {EPOCH_SPLIT}:\n"
        "  Blue dashed  = pre-1980\n"
        "  Orange dashed = post-1980\n\n"
        "A shift in GEV location (mu)\n"
        "indicates non-stationarity --\n"
        "analogous to catchment land-use\n"
        "change in hydrology.\n\n"
        "Ground record = PMF analogue:\n"
        "the deterministic upper limit.\n\n"
        "90% bootstrap CI on full-record\n"
        "GEV shown as shaded band.\n\n"
        "Data: Cricsheet all Tests JSON\n"
        "(2001-present).\n"
        "GEV fits illustrative only.",
        transform=ax.transAxes,
        va="top",
        fontsize=8,
        fontfamily="monospace",
        color=C_FULL,
        linespacing=1.45,
        bbox={
            "boxstyle": "round,pad=0.6",
            "facecolor": "#f0f4f8",
            "edgecolor": C_FULL,
            "alpha": 0.9,
        },
    )


def plot_grounds(ams_df: pd.DataFrame, output_path: Path) -> None:
    """Five-panel GEV frequency plot, one panel per ground + method note."""
    setup_style()

    fig = plt.figure(figsize=(20, 13))
    gs = GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.28)

    panel_positions = [
        gs[0, 0], gs[0, 1], gs[0, 2],
        gs[1, 0], gs[1, 1],
    ]
    axes = [fig.add_subplot(pos) for pos in panel_positions]

    log.info("Plotting GEV panels ...")
    for ax, ground in zip(axes, GROUNDS):
        log.info("  Panel: %s", ground)
        _plot_ground_panel(ax, ground, ams_df)

    # Sixth panel -- method note
    ax6 = fig.add_subplot(gs[1, 2])
    _method_note_panel(ax6)

    fig.suptitle(
        "Cricket Grounds as Hydrological Gauge Stations\n"
        "GEV Flood Frequency Analysis of Annual Maxima Series  |  Five Test Venues",
        fontsize=13,
        fontweight="bold",
        color=C_FULL,
        y=0.995,
    )
    fig.text(
        0.5, -0.005, FOOTER,
        ha="center", fontsize=7.5, color=C_TEXT, style="italic",
    )

    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log.info("Saved -> %s", output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    download_and_extract()

    innings_df = parse_ground_innings(EXTRACT_DIR)

    # Diagnostic: show unmapped venue strings that contain ground keywords
    all_venues = innings_df["venue_raw"].value_counts() if not innings_df.empty else pd.Series(dtype=int)
    log.info("Mapped venue counts:\n%s", all_venues.to_string())

    ams_df = build_ground_ams(innings_df)

    out = OUTPUT_DIR / "plot_grounds_gev.png"
    plot_grounds(ams_df, out)

    # Print GEV summary table
    print("\n--- GEV Parameters by Ground (full record) ---")
    print(f"{'Ground':<16} {'n':>4}  {'shape':>8}  {'loc':>8}  {'scale':>8}")
    for ground in GROUNDS:
        sub = ams_df[ams_df["ground"] == ground]["ams"].dropna()
        if len(sub) < 5:
            print(f"{ground:<16} {'<5':>4}  {'--':>8}  {'--':>8}  {'--':>8}")
            continue
        s, l, sc = fit_gev(sub)
        print(f"{ground:<16} {len(sub):>4}  {s:>8.3f}  {l:>8.1f}  {sc:>8.1f}")

    log.info("Done.")


if __name__ == "__main__":
    main()
