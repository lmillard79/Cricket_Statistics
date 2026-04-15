"""
Bradman vs Smith: GEV Flood Frequency Comparison
=================================================
Plots GEV-fitted AEP curves for Bradman and Smith using each player's
Annual Maxima Series (peak innings score per season).

X-axis : Annual Exceedance Probability (AEP), log scale, inverted (0.5 -> 0.001)
Y-axis : Peak Innings Score (runs)
Output : outputs/plot_bradman_vs_smith_gev.png

Data sources:
  - Bradman : embedded career records (1928-1948, Wisden / ESPNcricinfo)
  - Smith   : Cricsheet ball-by-ball JSON (2001-present)
"""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import requests
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
# WRM palette
# ---------------------------------------------------------------------------
BRADMAN_COLOUR = "#1e4164"   # WRM Blue
SMITH_COLOUR = "#00928f"     # WRM Teal

FOOTER = (
    "A water resources engineer's Sunday thought experiment.  "
    "GEV fits illustrative -- not peer reviewed."
)

# ---------------------------------------------------------------------------
# Bradman innings (embedded -- ball-by-ball data does not exist pre-1948)
# Source: ESPNcricinfo / Wisden Cricketers' Almanack
# ---------------------------------------------------------------------------
BRADMAN_INNINGS: list[dict] = [
    {"date": "1928-11-30", "runs": 18},
    {"date": "1928-12-01", "runs": 1},
    {"date": "1928-12-14", "runs": 79},
    {"date": "1928-12-15", "runs": 112},
    {"date": "1929-01-01", "runs": 40},
    {"date": "1929-01-02", "runs": 58},
    {"date": "1929-02-01", "runs": 123},
    {"date": "1929-02-02", "runs": 37},
    {"date": "1930-06-13", "runs": 8},
    {"date": "1930-06-14", "runs": 131},
    {"date": "1930-06-28", "runs": 254},
    {"date": "1930-06-29", "runs": 1},
    {"date": "1930-07-11", "runs": 334},
    {"date": "1930-07-25", "runs": 14},
    {"date": "1930-07-26", "runs": 232},
    {"date": "1930-08-16", "runs": 47},
    {"date": "1930-08-17", "runs": 232},
    {"date": "1930-12-12", "runs": 4},
    {"date": "1930-12-13", "runs": 25},
    {"date": "1931-01-01", "runs": 223},
    {"date": "1931-01-02", "runs": 152},
    {"date": "1931-01-16", "runs": 43},
    {"date": "1931-02-06", "runs": 33},
    {"date": "1931-02-07", "runs": 3},
    {"date": "1931-02-20", "runs": 2},
    {"date": "1931-11-27", "runs": 226},
    {"date": "1931-12-18", "runs": 112},
    {"date": "1931-12-19", "runs": 2},
    {"date": "1932-01-13", "runs": 167},
    {"date": "1932-01-14", "runs": 30},
    {"date": "1932-02-12", "runs": 299},
    {"date": "1932-12-02", "runs": 0},
    {"date": "1932-12-03", "runs": 103},
    {"date": "1932-12-30", "runs": 8},
    {"date": "1932-12-31", "runs": 66},
    {"date": "1933-01-13", "runs": 48},
    {"date": "1933-01-14", "runs": 66},
    {"date": "1933-02-10", "runs": 76},
    {"date": "1933-02-11", "runs": 24},
    {"date": "1934-07-06", "runs": 29},
    {"date": "1934-07-07", "runs": 25},
    {"date": "1934-07-20", "runs": 36},
    {"date": "1934-07-21", "runs": 13},
    {"date": "1934-07-27", "runs": 304},
    {"date": "1934-08-01", "runs": 244},
    {"date": "1934-08-18", "runs": 77},
    {"date": "1934-08-19", "runs": 49},
    {"date": "1936-12-04", "runs": 38},
    {"date": "1936-12-05", "runs": 0},
    {"date": "1936-12-18", "runs": 0},
    {"date": "1936-12-19", "runs": 82},
    {"date": "1937-01-01", "runs": 270},
    {"date": "1937-01-02", "runs": 26},
    {"date": "1937-01-29", "runs": 212},
    {"date": "1937-02-26", "runs": 169},
    {"date": "1938-06-10", "runs": 51},
    {"date": "1938-06-11", "runs": 144},
    {"date": "1938-06-24", "runs": 102},
    {"date": "1938-07-22", "runs": 103},
    {"date": "1938-07-23", "runs": 16},
    {"date": "1938-08-20", "runs": 18},
    {"date": "1946-11-29", "runs": 187},
    {"date": "1946-11-30", "runs": 234},
    {"date": "1946-12-13", "runs": 79},
    {"date": "1946-12-14", "runs": 49},
    {"date": "1947-01-01", "runs": 12},
    {"date": "1947-01-02", "runs": 63},
    {"date": "1947-01-31", "runs": 100},
    {"date": "1947-02-01", "runs": 16},
    {"date": "1947-11-28", "runs": 185},
    {"date": "1947-12-12", "runs": 132},
    {"date": "1947-12-26", "runs": 127},
    {"date": "1948-01-23", "runs": 201},
    {"date": "1948-02-06", "runs": 57},
    {"date": "1948-06-10", "runs": 138},
    {"date": "1948-06-11", "runs": 33},
    {"date": "1948-07-08", "runs": 89},
    {"date": "1948-07-09", "runs": 30},
    {"date": "1948-07-22", "runs": 7},
    {"date": "1948-07-23", "runs": 173},
    {"date": "1948-08-14", "runs": 0},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _season(date: datetime) -> int:
    """Australian cricket season start year (Oct-Sep)."""
    return date.year if date.month >= 10 else date.year - 1


def load_bradman_ams() -> pd.Series:
    """Return Bradman Annual Maxima Series (peak runs per season)."""
    rows = [
        {
            "season": _season(datetime.strptime(r["date"], "%Y-%m-%d")),
            "runs": r["runs"],
        }
        for r in BRADMAN_INNINGS
    ]
    df = pd.DataFrame(rows)
    ams = df.groupby("season")["runs"].max()
    log.info("Bradman AMS: %d seasons", len(ams))
    return ams


def download_and_extract() -> None:
    """Download Cricsheet Tests ZIP if not cached; extract if needed."""
    if not ZIP_CACHE.exists():
        log.info("Downloading Cricsheet Tests ...")
        r = requests.get(CRICSHEET_URL, timeout=120)
        r.raise_for_status()
        ZIP_CACHE.write_bytes(r.content)
        log.info("Saved %d MB", len(r.content) // 1_048_576)
    else:
        log.info("Using cached ZIP")

    if EXTRACT_DIR.exists() and any(EXTRACT_DIR.iterdir()):
        log.info("Cricsheet already extracted")
        return
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_CACHE) as zf:
        zf.extractall(EXTRACT_DIR)
    log.info("Extracted %d files", len(list(EXTRACT_DIR.glob("*.json"))))


def load_smith_ams() -> pd.Series:
    """Parse Cricsheet JSON to build Smith Annual Maxima Series."""
    records: list[dict] = []
    for fpath in sorted(EXTRACT_DIR.glob("*.json")):
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        info = data.get("info", {})
        registry = info.get("registry", {}).get("people", {})
        if "SPD Smith" not in registry:
            continue

        dates_raw = info.get("dates", [])
        if not dates_raw:
            continue
        match_date = datetime.strptime(dates_raw[0], "%Y-%m-%d")
        season = _season(match_date)

        for innings in data.get("innings", []):
            batter_runs: dict[str, int] = {}
            batter_balls: dict[str, int] = {}
            dismissed: set[str] = set()

            for over_block in innings.get("overs", []):
                for delivery in over_block.get("deliveries", []):
                    batter = delivery.get("batter")
                    if batter is None:
                        continue
                    batter_runs[batter] = (
                        batter_runs.get(batter, 0)
                        + delivery.get("runs", {}).get("batter", 0)
                    )
                    batter_balls[batter] = batter_balls.get(batter, 0) + 1
                    for wkt in delivery.get("wickets", []):
                        if wkt.get("player_out") == batter:
                            dismissed.add(batter)

            if "SPD Smith" in batter_runs:
                records.append(
                    {"season": season, "runs": batter_runs["SPD Smith"]}
                )

    df = pd.DataFrame(records)
    ams = df.groupby("season")["runs"].max()
    log.info("Smith AMS: %d seasons", len(ams))
    return ams


# ---------------------------------------------------------------------------
# GEV bootstrap CI
# ---------------------------------------------------------------------------

def gev_ci(
    data: pd.Series,
    aep_values: np.ndarray,
    n_bootstrap: int = 1000,
    ci: float = 0.90,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Fit GEV and return (fitted_quantiles, lower_ci, upper_ci).
    Bootstrap resampling used for confidence intervals.
    """
    shape, loc, scale = genextreme.fit(data)
    fitted = genextreme.ppf(1.0 - aep_values, shape, loc, scale)

    rng = np.random.default_rng(42)
    arr = data.to_numpy()
    boot = np.zeros((n_bootstrap, len(aep_values)))
    for i in range(n_bootstrap):
        sample = rng.choice(arr, size=len(arr), replace=True)
        try:
            s, l, sc = genextreme.fit(sample)
            boot[i] = genextreme.ppf(1.0 - aep_values, s, l, sc)
        except Exception:
            boot[i] = np.nan

    alpha = (1.0 - ci) / 2.0
    lower = np.nanpercentile(boot, alpha * 100, axis=0)
    upper = np.nanpercentile(boot, (1 - alpha) * 100, axis=0)

    return fitted, lower, upper


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

def plot_gev_comparison(
    bradman_ams: pd.Series,
    smith_ams: pd.Series,
    output_path: Path,
    y_max: float = 500.0,
) -> None:
    """
    GEV frequency curves for Bradman and Smith on a single AEP plot.
    """
    plt.rcParams.update(
        {
            "figure.dpi": 200,
            "savefig.dpi": 200,
            "font.family": "sans-serif",
            "font.size": 10,
            "grid.color": "0.75",
            "grid.linestyle": "--",
            "grid.linewidth": 0.5,
            "axes.titlepad": 14,
        }
    )

    aep_curve = np.logspace(np.log10(0.001), np.log10(0.5), 400)

    fig, ax = plt.subplots(figsize=(11, 7))

    players = [
        ("Bradman", bradman_ams, BRADMAN_COLOUR),
        ("Smith",   smith_ams,   SMITH_COLOUR),
    ]

    for label, ams, colour in players:
        shape, loc, scale = genextreme.fit(ams)
        log.info(
            "%s  GEV params: shape=%.3f  loc=%.1f  scale=%.1f  (n=%d seasons)",
            label, shape, loc, scale, len(ams),
        )

        fitted, lower, upper = gev_ci(ams, aep_curve, n_bootstrap=1000)
        fitted = np.clip(fitted, 0, y_max)
        lower  = np.clip(lower,  0, y_max)
        upper  = np.clip(upper,  0, y_max)

        # GEV curve
        ax.plot(
            aep_curve, fitted,
            color=colour, linewidth=2.2,
            label=f"{label}  (GEV shape={shape:.3f})",
            zorder=4,
        )
        # 90% CI band
        ax.fill_between(
            aep_curve, lower, upper,
            color=colour, alpha=0.18, zorder=2,
            label=f"{label} 90% CI",
        )

        # Empirical AMS points (Weibull plotting position)
        sorted_runs = np.sort(ams.to_numpy())
        n = len(sorted_runs)
        emp_aep = 1.0 - np.arange(1, n + 1) / (n + 1)
        ax.scatter(
            emp_aep, sorted_runs,
            color=colour, s=30, alpha=0.75, zorder=5,
        )

        # Annotate career-high
        peak = int(ams.max())
        peak_aep = float(1.0 - genextreme.cdf(peak, shape, loc, scale))
        ax.scatter([peak_aep], [peak], color=colour, s=90, marker="*", zorder=6)
        offset_x = peak_aep * 2.5 if label == "Bradman" else peak_aep * 2.5
        offset_y = peak - 25 if label == "Bradman" else peak + 18
        ax.annotate(
            f"{label} career high: {peak}\n(AEP ~ {peak_aep:.3f})",
            xy=(peak_aep, peak),
            xytext=(offset_x, offset_y),
            fontsize=8,
            color=colour,
            arrowprops={"arrowstyle": "->", "color": colour, "lw": 0.9},
        )

    # -----------------------------------------------------------------------
    # Axes formatting
    # -----------------------------------------------------------------------
    ax.set_xscale("log")
    ax.invert_xaxis()

    # Clean tick labels: show as decimals, not scientific notation
    ax.xaxis.set_major_formatter(
        mticker.FuncFormatter(lambda v, _: f"{v:.3f}" if v < 0.1 else f"{v:.2f}")
    )
    ax.xaxis.set_minor_formatter(mticker.NullFormatter())

    ax.set_xlim(0.5, 0.001)
    ax.set_ylim(0, y_max)

    ax.set_xlabel("Annual Exceedance Probability (AEP)", fontsize=12)
    ax.set_ylabel("Peak Innings Score per Season (runs)", fontsize=12)
    ax.set_title(
        "GEV Flood Frequency Analysis: Bradman vs Smith\n"
        "Annual Maxima Series  |  90% bootstrap confidence intervals",
        fontsize=12,
    )

    ax.grid(True, which="both")

    # Deduplicate legend entries (scatter markers share colour with line)
    handles, labels = ax.get_legend_handles_labels()
    # Keep only line + CI entries (not the scatter handles)
    legend_h = [h for h, l in zip(handles, labels) if "CI" in l or "GEV" in l]
    legend_l = [l for l in labels if "CI" in l or "GEV" in l]
    ax.legend(legend_h, legend_l, fontsize=9, loc="upper left")

    fig.text(0.5, -0.01, FOOTER, ha="center", fontsize=7.5, color="#485253", style="italic")
    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved -> %s", output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    bradman_ams = load_bradman_ams()

    download_and_extract()
    smith_ams = load_smith_ams()

    out = OUTPUT_DIR / "plot_bradman_vs_smith_gev.png"
    plot_gev_comparison(bradman_ams, smith_ams, out)

    log.info("Done.")


if __name__ == "__main__":
    main()
