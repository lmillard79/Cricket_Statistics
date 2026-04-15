"""
Cricket as a Hydrological Surrogate
====================================
Applies Extreme Value Theory and Intensity-Duration-Frequency (IDF) analysis
to Test cricket batting statistics for Bradman, Tendulkar, and Smith.

Hydrological framework:
  - Catchment       = individual batsman
  - Event           = individual innings
  - Runoff volume   = runs scored
  - Intensity       = strike rate (runs per 100 balls)
  - Duration        = balls faced
  - Annual Maxima   = peak innings score per season
  - GEV             = fitted to career annual maxima series
  - IFD envelope    = strike rate vs balls faced upper boundary (PMF analogue)

Author: Principal Water Engineer, Brisbane QLD
Date: April 2026
Note: Illustrative analysis. GEV fits not peer reviewed.
"""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

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
# WRM Corporate Palette
# ---------------------------------------------------------------------------
wrmcol = [
    "WRM Green", "WRM Teal", "WRM Blue", "Bright Blue", "Bright Teal",
    "Charcoal", "Citrus", "Light orange", "Sky",
]
WRM = [
    "#8dc63f", "#00928f", "#1e4164", "#00539b", "#00b49d",
    "#485253", "#d7df23", "#d3bd2a", "#6dcff6",
]
WRMcolour: dict[str, str] = dict(zip(wrmcol, WRM))

PLAYER_COLOURS: dict[str, str] = {
    "Bradman": "#1e4164",    # WRM Blue
    "Tendulkar": "#8dc63f",  # WRM Green
    "Smith": "#00928f",      # WRM Teal
}

# Cricsheet registry names (ball-by-ball data starts ~2001; Bradman handled separately)
PLAYER_KEYS: dict[str, str] = {
    "Tendulkar": "SR Tendulkar",
    "Smith": "SPD Smith",
}

# ---------------------------------------------------------------------------
# Bradman innings data
# Embedded directly: ball-by-ball data does not exist for the 1928-1948 era.
# Source: ESPNcricinfo career statistics / Wisden Cricketers' Almanack.
# Columns: date (YYYY-MM-DD), runs, balls_faced (estimated from scoring rate),
#          not_out (bool).
# Balls-faced estimates use Bradman's documented career strike rate of ~60
# per 100 balls for the majority of innings; adjusted for documented long
# innings (334, 304, 270 etc.) using known session lengths from scorecards.
# Strike rate is therefore approximate for individual innings but
# directionally correct for the IFD scatter.
# ---------------------------------------------------------------------------
BRADMAN_INNINGS: list[dict] = [
    # date           runs  balls  not_out
    # --- 1928-29 Australia vs England ---
    {"date": "1928-11-30", "runs": 18,  "balls": 35,  "not_out": False},
    {"date": "1928-12-01", "runs": 1,   "balls": 5,   "not_out": False},
    {"date": "1928-12-14", "runs": 79,  "balls": 130, "not_out": False},
    {"date": "1928-12-15", "runs": 112, "balls": 187, "not_out": False},
    {"date": "1929-01-01", "runs": 40,  "balls": 70,  "not_out": False},
    {"date": "1929-01-02", "runs": 58,  "balls": 100, "not_out": False},
    {"date": "1929-02-01", "runs": 123, "balls": 205, "not_out": False},
    {"date": "1929-02-02", "runs": 37,  "balls": 65,  "not_out": False},
    # --- 1930 England tour ---
    {"date": "1930-06-13", "runs": 8,   "balls": 18,  "not_out": False},
    {"date": "1930-06-14", "runs": 131, "balls": 218, "not_out": False},
    {"date": "1930-06-28", "runs": 254, "balls": 425, "not_out": False},
    {"date": "1930-06-29", "runs": 1,   "balls": 4,   "not_out": False},
    {"date": "1930-07-11", "runs": 334, "balls": 448, "not_out": False},
    {"date": "1930-07-25", "runs": 14,  "balls": 25,  "not_out": False},
    {"date": "1930-07-26", "runs": 232, "balls": 387, "not_out": False},
    {"date": "1930-08-16", "runs": 47,  "balls": 80,  "not_out": False},
    {"date": "1930-08-17", "runs": 232, "balls": 387, "not_out": False},
    # --- 1930-31 Australia vs West Indies ---
    {"date": "1930-12-12", "runs": 4,   "balls": 10,  "not_out": False},
    {"date": "1930-12-13", "runs": 25,  "balls": 45,  "not_out": True},
    {"date": "1931-01-01", "runs": 223, "balls": 372, "not_out": False},
    {"date": "1931-01-02", "runs": 152, "balls": 253, "not_out": False},
    {"date": "1931-01-16", "runs": 43,  "balls": 75,  "not_out": True},
    {"date": "1931-02-06", "runs": 33,  "balls": 58,  "not_out": False},
    {"date": "1931-02-07", "runs": 3,   "balls": 8,   "not_out": False},
    {"date": "1931-02-20", "runs": 2,   "balls": 5,   "not_out": False},
    # --- 1931-32 Australia vs South Africa ---
    {"date": "1931-11-27", "runs": 226, "balls": 377, "not_out": False},
    {"date": "1931-12-18", "runs": 112, "balls": 187, "not_out": False},
    {"date": "1931-12-19", "runs": 2,   "balls": 5,   "not_out": False},
    {"date": "1932-01-13", "runs": 167, "balls": 278, "not_out": False},
    {"date": "1932-01-14", "runs": 30,  "balls": 52,  "not_out": False},
    {"date": "1932-02-12", "runs": 299, "balls": 498, "not_out": True},
    # --- 1932-33 Bodyline series ---
    {"date": "1932-12-02", "runs": 0,   "balls": 1,   "not_out": False},
    {"date": "1932-12-03", "runs": 103, "balls": 172, "not_out": True},
    {"date": "1932-12-30", "runs": 8,   "balls": 18,  "not_out": False},
    {"date": "1932-12-31", "runs": 66,  "balls": 110, "not_out": False},
    {"date": "1933-01-13", "runs": 48,  "balls": 83,  "not_out": False},
    {"date": "1933-01-14", "runs": 66,  "balls": 110, "not_out": False},
    {"date": "1933-02-10", "runs": 76,  "balls": 127, "not_out": False},
    {"date": "1933-02-11", "runs": 24,  "balls": 42,  "not_out": False},
    # --- 1934 England tour ---
    {"date": "1934-07-06", "runs": 29,  "balls": 50,  "not_out": False},
    {"date": "1934-07-07", "runs": 25,  "balls": 43,  "not_out": False},
    {"date": "1934-07-20", "runs": 36,  "balls": 62,  "not_out": False},
    {"date": "1934-07-21", "runs": 13,  "balls": 22,  "not_out": False},
    {"date": "1934-07-27", "runs": 304, "balls": 430, "not_out": False},
    {"date": "1934-08-01", "runs": 244, "balls": 350, "not_out": False},
    {"date": "1934-08-18", "runs": 77,  "balls": 128, "not_out": False},
    {"date": "1934-08-19", "runs": 49,  "balls": 83,  "not_out": False},
    # --- 1936-37 Australia vs England ---
    {"date": "1936-12-04", "runs": 38,  "balls": 65,  "not_out": False},
    {"date": "1936-12-05", "runs": 0,   "balls": 2,   "not_out": False},
    {"date": "1936-12-18", "runs": 0,   "balls": 1,   "not_out": False},
    {"date": "1936-12-19", "runs": 82,  "balls": 137, "not_out": False},
    {"date": "1937-01-01", "runs": 270, "balls": 375, "not_out": False},
    {"date": "1937-01-02", "runs": 26,  "balls": 45,  "not_out": False},
    {"date": "1937-01-29", "runs": 212, "balls": 295, "not_out": False},
    {"date": "1937-02-26", "runs": 169, "balls": 235, "not_out": False},
    # --- 1938 England tour ---
    {"date": "1938-06-10", "runs": 51,  "balls": 87,  "not_out": False},
    {"date": "1938-06-11", "runs": 144, "balls": 200, "not_out": False},
    {"date": "1938-06-24", "runs": 102, "balls": 142, "not_out": True},
    {"date": "1938-07-22", "runs": 103, "balls": 143, "not_out": False},
    {"date": "1938-07-23", "runs": 16,  "balls": 28,  "not_out": False},
    {"date": "1938-08-20", "runs": 18,  "balls": 32,  "not_out": False},
    # --- 1946-47 Australia vs England (post-war return) ---
    {"date": "1946-11-29", "runs": 187, "balls": 260, "not_out": False},
    {"date": "1946-11-30", "runs": 234, "balls": 325, "not_out": False},
    {"date": "1946-12-13", "runs": 79,  "balls": 110, "not_out": False},
    {"date": "1946-12-14", "runs": 49,  "balls": 68,  "not_out": False},
    {"date": "1947-01-01", "runs": 12,  "balls": 17,  "not_out": False},
    {"date": "1947-01-02", "runs": 63,  "balls": 88,  "not_out": False},
    {"date": "1947-01-31", "runs": 100, "balls": 138, "not_out": False},
    {"date": "1947-02-01", "runs": 16,  "balls": 22,  "not_out": False},
    # --- 1947-48 Australia vs India ---
    {"date": "1947-11-28", "runs": 185, "balls": 257, "not_out": False},
    {"date": "1947-12-12", "runs": 132, "balls": 183, "not_out": True},
    {"date": "1947-12-26", "runs": 127, "balls": 176, "not_out": False},
    {"date": "1948-01-23", "runs": 201, "balls": 279, "not_out": True},
    {"date": "1948-02-06", "runs": 57,  "balls": 79,  "not_out": False},
    # --- 1948 Invincibles England tour ---
    {"date": "1948-06-10", "runs": 138, "balls": 192, "not_out": False},
    {"date": "1948-06-11", "runs": 33,  "balls": 46,  "not_out": False},
    {"date": "1948-07-08", "runs": 89,  "balls": 124, "not_out": False},
    {"date": "1948-07-09", "runs": 30,  "balls": 42,  "not_out": False},
    {"date": "1948-07-22", "runs": 7,   "balls": 10,  "not_out": False},
    {"date": "1948-07-23", "runs": 173, "balls": 240, "not_out": False},
    {"date": "1948-08-14", "runs": 0,   "balls": 2,   "not_out": False},
]


def _assign_season(date: datetime) -> int:
    """Australian cricket season: Oct-Sep. Returns start year of season."""
    return date.year if date.month >= 10 else date.year - 1


def load_bradman_innings() -> pd.DataFrame:
    """Load embedded Bradman innings as a DataFrame."""
    rows = []
    for record in BRADMAN_INNINGS:
        date = datetime.strptime(record["date"], "%Y-%m-%d")
        season = _assign_season(date)
        balls = record["balls"]
        runs = record["runs"]
        sr = (runs / balls * 100) if balls > 0 else 0.0
        rows.append(
            {
                "player": "Bradman",
                "season": season,
                "date": date,
                "runs": runs,
                "balls_faced": balls,
                "not_out": record["not_out"],
                "strike_rate": sr,
            }
        )
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    log.info("Bradman: %d innings loaded from embedded data", len(df))
    return df


FOOTER = (
    "A water resources engineer's Sunday thought experiment.  "
    "GEV fits illustrative -- not peer reviewed."
)


def setup_wrm_style() -> None:
    """Apply WRM corporate matplotlib rcParams."""
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=WRM)
    plt.rcParams["figure.dpi"] = 200
    plt.rcParams["savefig.dpi"] = 200
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.size"] = 10
    plt.rcParams["legend.fontsize"] = "small"
    plt.rcParams["figure.titlesize"] = "medium"
    plt.rcParams["grid.color"] = "0.7"
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["grid.linewidth"] = 0.5
    plt.rcParams["axes.titlepad"] = 12


# ---------------------------------------------------------------------------
# Data acquisition (Cricsheet -- covers ~2001 to present)
# ---------------------------------------------------------------------------

def download_cricsheet(url: str, cache_path: Path) -> None:
    """Download Cricsheet Tests ZIP if not already cached."""
    if cache_path.exists():
        log.info("Using cached ZIP: %s", cache_path)
        return
    log.info("Downloading Cricsheet Tests from %s ...", url)
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    cache_path.write_bytes(response.content)
    log.info("Saved %d MB to %s", len(response.content) // 1_048_576, cache_path)


def extract_cricsheet(zip_path: Path, extract_dir: Path) -> None:
    """Extract Cricsheet ZIP to extract_dir if not already extracted."""
    if extract_dir.exists() and any(extract_dir.iterdir()):
        log.info("Cricsheet data already extracted to %s", extract_dir)
        return
    extract_dir.mkdir(parents=True, exist_ok=True)
    log.info("Extracting %s ...", zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    log.info("Extracted %d files", len(list(extract_dir.glob("*.json"))))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_player_innings(
    extract_dir: Path,
    player_keys: dict[str, str],
) -> pd.DataFrame:
    """
    Parse all Test JSON files and extract per-innings records for target players.

    Returns a DataFrame with columns:
        player, season, date, runs, balls_faced, not_out, strike_rate
    """
    json_files = sorted(extract_dir.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {extract_dir}")

    # Build reverse lookup: cricsheet name fragment -> player label
    # Cricsheet uses formats like "DA Bradman", "SR Tendulkar", "SPD Smith"
    reverse: dict[str, str] = {v: k for k, v in player_keys.items()}

    records: list[dict] = []

    for fpath in json_files:
        try:
            with open(fpath, encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue

        info = data.get("info", {})
        dates_raw = info.get("dates", [])
        if not dates_raw:
            continue
        match_date = datetime.strptime(dates_raw[0], "%Y-%m-%d")
        season = _assign_season(match_date)

        # Check if any target player is in the registry
        registry = info.get("registry", {}).get("people", {})
        players_in_match: set[str] = set(registry.keys())
        target_in_match = {
            label: cs_name
            for label, cs_name in player_keys.items()
            if cs_name in players_in_match
        }
        if not target_in_match:
            continue

        for innings in data.get("innings", []):
            for delivery in innings.get("overs", [{}]):
                pass  # structure check only

            # Aggregate per batter across all deliveries in this innings
            batter_stats: dict[str, dict] = {}

            for over_block in innings.get("overs", []):
                for delivery in over_block.get("deliveries", []):
                    batter_name: Optional[str] = delivery.get("batter")
                    if batter_name is None:
                        continue

                    if batter_name not in batter_stats:
                        batter_stats[batter_name] = {
                            "runs": 0,
                            "balls": 0,
                            "dismissed": False,
                        }

                    batter_runs: int = delivery.get("runs", {}).get("batter", 0)
                    batter_stats[batter_name]["runs"] += batter_runs
                    batter_stats[batter_name]["balls"] += 1

                    # Check wicket
                    wicket = delivery.get("wickets", [])
                    for wkt in wicket:
                        if wkt.get("player_out") == batter_name:
                            batter_stats[batter_name]["dismissed"] = True

            # Extract target players from this innings
            for cs_name, label in [(v, k) for k, v in target_in_match.items()]:
                if cs_name in batter_stats:
                    stats = batter_stats[cs_name]
                    runs: int = stats["runs"]
                    balls: int = stats["balls"]
                    not_out: bool = not stats["dismissed"]
                    sr: float = (runs / balls * 100) if balls > 0 else 0.0

                    records.append(
                        {
                            "player": label,
                            "season": season,
                            "date": match_date,
                            "runs": runs,
                            "balls_faced": balls,
                            "not_out": not_out,
                            "strike_rate": sr,
                        }
                    )

    df = pd.DataFrame(records)
    if df.empty:
        raise ValueError("No innings records found for target players.")

    df = df.sort_values(["player", "date"]).reset_index(drop=True)
    log.info(
        "Parsed %d innings records across %d players",
        len(df),
        df["player"].nunique(),
    )
    return df


# ---------------------------------------------------------------------------
# Annual Maxima Series
# ---------------------------------------------------------------------------

def build_ams(innings_df: pd.DataFrame) -> pd.DataFrame:
    """Build Annual Maxima Series (peak innings score per player per season)."""
    ams = (
        innings_df.groupby(["player", "season"])["runs"]
        .max()
        .reset_index()
        .rename(columns={"runs": "peak_runs"})
    )
    log.info("AMS: %d season records", len(ams))
    return ams


# ---------------------------------------------------------------------------
# GEV fitting
# ---------------------------------------------------------------------------

def fit_gev(series: pd.Series) -> tuple[float, float, float]:
    """Fit GEV to a data series. Returns (shape, loc, scale)."""
    shape, loc, scale = genextreme.fit(series)
    return float(shape), float(loc), float(scale)


def gev_quantiles(
    shape: float,
    loc: float,
    scale: float,
    aep_values: np.ndarray,
) -> np.ndarray:
    """Return GEV quantiles for given AEP values (non-exceedance = 1 - AEP)."""
    return genextreme.ppf(1.0 - aep_values, shape, loc, scale)


def gev_confidence_bands(
    data: pd.Series,
    shape: float,
    loc: float,
    scale: float,
    aep_values: np.ndarray,
    n_bootstrap: int = 500,
) -> tuple[np.ndarray, np.ndarray]:
    """Bootstrap 90% confidence bands on GEV quantiles."""
    rng = np.random.default_rng(42)
    boot_quantiles = np.zeros((n_bootstrap, len(aep_values)))
    arr = data.to_numpy()

    for i in range(n_bootstrap):
        sample = rng.choice(arr, size=len(arr), replace=True)
        try:
            s, l, sc = genextreme.fit(sample)
            boot_quantiles[i] = gev_quantiles(s, l, sc, aep_values)
        except Exception:
            boot_quantiles[i] = np.nan

    lower = np.nanpercentile(boot_quantiles, 5, axis=0)
    upper = np.nanpercentile(boot_quantiles, 95, axis=0)
    return lower, upper


# ---------------------------------------------------------------------------
# IFD table
# ---------------------------------------------------------------------------

AEP_LABELS: list[tuple[float, str]] = [
    (0.50, "50% (1 in 2)"),
    (0.20, "20% (1 in 5)"),
    (0.10, "10% (1 in 10)"),
    (0.05, "5% (1 in 20)"),
    (0.02, "2% (1 in 50)"),
    (0.01, "1% (1 in 100)"),
    (0.005, "0.5% (1 in 200)"),
]


def build_ifd_table(
    ams_df: pd.DataFrame,
    players: list[str],
) -> pd.DataFrame:
    """Build IFD-style table of GEV design innings scores."""
    rows = []
    for aep, label in AEP_LABELS:
        row: dict = {"AEP": label}
        for player in players:
            subset = ams_df[ams_df["player"] == player]["peak_runs"].dropna()
            if len(subset) < 5:
                row[f"{player} Design Score (runs)"] = np.nan
                continue
            shape, loc, scale = fit_gev(subset)
            q_arr = gev_quantiles(shape, loc, scale, np.array([aep]))
            row[f"{player} Design Score (runs)"] = int(round(float(q_arr[0])))
        rows.append(row)

    table = pd.DataFrame(rows)
    return table


# ---------------------------------------------------------------------------
# Plot 1: Annual Maxima Series
# ---------------------------------------------------------------------------

def plot_annual_maxima(
    ams_df: pd.DataFrame,
    innings_df: pd.DataFrame,
    players: list[str],
    output_path: Path,
) -> None:
    """Plot 1 -- Annual Maxima Series hydrographs for each player."""
    fig, axes = plt.subplots(len(players), 1, figsize=(12, 3.5 * len(players)))

    # Notable individual innings to annotate
    notable: dict[str, list[tuple[int, int, str]]] = {
        "Bradman": [(1930, 334, "334 at Leeds 1930\n(Record flood event)")],
        "Tendulkar": [(2004, 248, "248* vs Bangladesh 2004\n(Prolonged high-flow event)")],
        "Smith": [(2017, 239, "239 vs England 2017")],
    }

    for ax, player in zip(axes, players):
        colour = PLAYER_COLOURS[player]
        subset = ams_df[ams_df["player"] == player].sort_values("season")

        ax.plot(
            subset["season"],
            subset["peak_runs"],
            color=colour,
            linewidth=1.2,
            zorder=2,
        )
        ax.scatter(
            subset["season"],
            subset["peak_runs"],
            color=colour,
            s=30,
            zorder=3,
        )

        # Annotate notable innings
        for s, r, txt in notable.get(player, []):
            # Find the season record closest to the target season
            argsort_idx = (subset["season"] - s).abs().argsort()
            if len(argsort_idx) == 0:
                continue
            iloc_pos = int(argsort_idx.iloc[0])
            # argsort returns original index positions; use positional iloc on reset subset
            subset_reset = subset.reset_index(drop=True)
            match_row = subset_reset.iloc[iloc_pos]
            ax.annotate(
                txt,
                xy=(match_row["season"], match_row["peak_runs"]),
                xytext=(match_row["season"] + 2, match_row["peak_runs"] + 15),
                fontsize=7,
                color="#485253",
                arrowprops={"arrowstyle": "->", "color": "#485253", "lw": 0.8},
            )

        ax.set_title(f"{player} -- Annual Peak Innings Score (AMS)", fontsize=10)
        ax.set_xlabel("Season (start year)", fontsize=9)
        ax.set_ylabel("Peak Innings Score (runs)", fontsize=9)
        ax.grid(True)
        ax.set_xlim(subset["season"].min() - 1, subset["season"].max() + 1)

    fig.suptitle(
        "Annual Maxima Series: Test Cricket Batting as a Hydrological Gauge Record",
        fontsize=12,
        y=1.01,
    )
    fig.text(0.5, -0.01, FOOTER, ha="center", fontsize=7, color="#485253", style="italic")
    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved Plot 1 -> %s", output_path)


# ---------------------------------------------------------------------------
# Plot 2: GEV Flood Frequency Curves
# ---------------------------------------------------------------------------

def plot_gev_frequency(
    ams_df: pd.DataFrame,
    players: list[str],
    output_path: Path,
) -> None:
    """Plot 2 -- GEV flood frequency curves on AEP log-scale."""
    fig, ax = plt.subplots(figsize=(11, 7))

    aep_plot = np.logspace(np.log10(0.001), np.log10(0.5), 300)

    for player in players:
        colour = PLAYER_COLOURS[player]
        subset = ams_df[ams_df["player"] == player]["peak_runs"].dropna()
        if len(subset) < 5:
            log.warning("Insufficient AMS data for %s (%d records)", player, len(subset))
            continue

        shape, loc, scale = fit_gev(subset)
        log.info(
            "%s GEV: shape=%.3f  loc=%.1f  scale=%.1f",
            player, shape, loc, scale,
        )

        Y_MAX = 600.0  # physical ceiling: no Test innings has exceeded 501*

        quantiles = np.clip(gev_quantiles(shape, loc, scale, aep_plot), 0, Y_MAX)
        lower, upper = gev_confidence_bands(subset, shape, loc, scale, aep_plot)
        lower = np.clip(lower, 0, Y_MAX)
        upper = np.clip(upper, 0, Y_MAX)

        ax.semilogx(aep_plot, quantiles, color=colour, linewidth=2.0, label=player, zorder=3)
        ax.fill_between(
            aep_plot, lower, upper,
            color=colour, alpha=0.15, zorder=2,
        )

        # Plot empirical AMS points using Weibull plotting position
        n = len(subset)
        sorted_runs = np.sort(subset.to_numpy())
        ranks = np.arange(1, n + 1)
        empirical_aep = 1.0 - ranks / (n + 1)

        ax.scatter(
            empirical_aep,
            sorted_runs,
            color=colour,
            s=18,
            alpha=0.7,
            zorder=4,
        )

        # Annotate record innings
        if player == "Bradman":
            record = 334
            record_aep = float(1.0 - genextreme.cdf(record, shape, loc, scale))
            ax.scatter(
                [record_aep], [record],
                color=colour, s=80, marker="*", zorder=5,
            )
            ax.annotate(
                f"334 (AEP ~{record_aep:.3f})",
                xy=(record_aep, record),
                xytext=(record_aep * 3, record - 30),
                fontsize=7.5,
                color=colour,
                arrowprops={"arrowstyle": "->", "color": colour, "lw": 0.8},
            )
            ax.text(
                0.35, 0.82,
                f"Bradman GEV shape = {shape:.3f}\n(Frechet -- unbounded upper tail)",
                fontsize=7.5,
                color=colour,
                transform=ax.transAxes,
                ha="center",
                bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": colour, "alpha": 0.9},
            )
        elif player == "Tendulkar":
            record = 248
            record_aep = float(1.0 - genextreme.cdf(record, shape, loc, scale))
            ax.scatter(
                [record_aep], [record],
                color=colour, s=80, marker="*", zorder=5,
            )
            ax.annotate(
                f"248* (AEP ~{record_aep:.3f})",
                xy=(record_aep, record),
                xytext=(record_aep * 4, record + 20),
                fontsize=7.5,
                color=colour,
                arrowprops={"arrowstyle": "->", "color": colour, "lw": 0.8},
            )

    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.3f}"))

    ax.set_xlabel("Annual Exceedance Probability (AEP)", fontsize=11)
    ax.set_ylabel("Design Innings Score (runs)", fontsize=11)
    ax.set_title(
        "Flood Frequency Analysis: GEV Fit to Career Annual Maxima Series\n"
        "90% confidence bands shown as shaded regions",
        fontsize=11,
    )
    ax.legend(fontsize=9)
    ax.grid(True, which="both")
    ax.set_xlim(0.5, 0.001)
    ax.set_ylim(0, 600)

    fig.text(0.5, -0.02, FOOTER, ha="center", fontsize=7, color="#485253", style="italic")
    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved Plot 2 -> %s", output_path)


# ---------------------------------------------------------------------------
# Plot 3: Intensity-Duration Envelope (The PMF Hero Plot)
# ---------------------------------------------------------------------------

def _upper_envelope(
    x: np.ndarray,
    y: np.ndarray,
    n_bins: int = 25,
    quantile: float = 0.95,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute upper envelope by binning x and taking the quantile of y per bin.
    Returns (bin_centres, envelope_y).
    """
    x_log = np.log10(x + 1)
    bins = np.linspace(x_log.min(), x_log.max(), n_bins + 1)
    centres: list[float] = []
    envelope: list[float] = []

    for i in range(n_bins):
        mask = (x_log >= bins[i]) & (x_log < bins[i + 1])
        if mask.sum() < 3:
            continue
        centres.append(10 ** ((bins[i] + bins[i + 1]) / 2))
        envelope.append(float(np.quantile(y[mask], quantile)))

    return np.array(centres), np.array(envelope)


def plot_intensity_duration(
    innings_df: pd.DataFrame,
    players: list[str],
    output_path: Path,
    min_balls: int = 20,
) -> None:
    """
    Plot 3 (hero plot) -- Intensity-Duration scatter with upper envelope.

    Each point is one innings. X = balls faced (duration).
    Y = strike rate (intensity). Upper envelope = PMF analogue.
    The empty upper-right corner IS the PMF argument.
    """
    fig, ax = plt.subplots(figsize=(13, 8))

    all_x: list[float] = []
    all_y: list[float] = []

    for player in players:
        colour = PLAYER_COLOURS[player]
        subset = innings_df[
            (innings_df["player"] == player) &
            (innings_df["balls_faced"] >= min_balls)
        ]

        ax.scatter(
            subset["balls_faced"],
            subset["strike_rate"],
            color=colour,
            alpha=0.45,
            s=22,
            label=player,
            zorder=3,
        )

        all_x.extend(subset["balls_faced"].tolist())
        all_y.extend(subset["strike_rate"].tolist())

    # Upper envelope across all players
    x_arr = np.array(all_x, dtype=float)
    y_arr = np.array(all_y, dtype=float)

    env_x, env_y = _upper_envelope(x_arr, y_arr, n_bins=30, quantile=0.97)

    # Fit a power-law to the envelope points: SR = a * balls^(-b)
    # Linearise via log-log: log(SR) = log(a) - b*log(balls)
    valid = (env_x > 0) & (env_y > 0)
    log_x = np.log(env_x[valid])
    log_y = np.log(env_y[valid])
    coeffs = np.polyfit(log_x, log_y, 1)   # [slope, intercept]
    a_coeff = np.exp(coeffs[1])
    b_exp = -coeffs[0]

    smooth_x = np.linspace(x_arr.min(), x_arr.max(), 300)
    smooth_y = a_coeff * smooth_x ** (-b_exp)

    ax.plot(
        smooth_x, smooth_y,
        color="#d7df23",
        linewidth=2.5,
        linestyle="-",
        zorder=5,
        label=f"Power-law envelope  SR ~ D^(-{b_exp:.2f})\n(IFD upper boundary / PMF analogue)",
    )

    # T20 baseline intensity reference line
    ax.axhline(
        y=150,
        color="#d3bd2a",
        linestyle="--",
        linewidth=1.2,
        zorder=4,
        label="T20 baseline intensity (SR = 150)",
    )
    ax.text(
        5, 153,
        "T20 baseline intensity",
        fontsize=8,
        color="#d3bd2a",
    )

    # Annotate the empty upper-right corner (PMF zone)
    ax.text(
        0.72, 0.88,
        "Probable Maximum Innings\n(theoretically possible, never observed)\nPMF equivalent",
        transform=ax.transAxes,
        fontsize=9,
        color="#485253",
        ha="center",
        va="center",
        bbox={
            "boxstyle": "round,pad=0.5",
            "facecolor": "#f5f5f5",
            "edgecolor": "#485253",
            "alpha": 0.85,
            "linestyle": "--",
        },
    )

    ax.set_xlabel("Innings Duration (balls faced)", fontsize=12)
    ax.set_ylabel("Scoring Intensity (runs per 100 balls)", fontsize=12)
    ax.set_title(
        "Intensity-Duration Envelope: The PMF Argument in Cricket\n"
        "High intensity and high duration do not coexist. "
        "The empty upper-right corner is the Probable Maximum Innings.",
        fontsize=11,
    )

    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    fig.text(0.5, -0.02, FOOTER, ha="center", fontsize=7, color="#485253", style="italic")
    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved Plot 3 -> %s", output_path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    setup_wrm_style()

    players = ["Bradman", "Tendulkar", "Smith"]

    # Step 1: Acquire data
    download_cricsheet(CRICSHEET_URL, ZIP_CACHE)
    extract_cricsheet(ZIP_CACHE, EXTRACT_DIR)

    # Step 2: Parse innings from Cricsheet (Tendulkar + Smith)
    cricsheet_players = [p for p in players if p != "Bradman"]
    log.info("Parsing Cricsheet innings for: %s", cricsheet_players)
    innings_df = parse_player_innings(EXTRACT_DIR, PLAYER_KEYS)

    # Append Bradman embedded data
    bradman_df = load_bradman_innings()
    innings_df = pd.concat([innings_df, bradman_df], ignore_index=True)

    # Diagnostic summary
    for player in players:
        sub = innings_df[innings_df["player"] == player]
        dismissed = sub[~sub["not_out"]]
        denom = max(len(dismissed), 1)
        log.info(
            "%s: %d innings  |  career avg = %.2f  |  seasons %d-%d",
            player,
            len(sub),
            sub["runs"].sum() / denom,
            int(sub["season"].min()),
            int(sub["season"].max()),
        )

    # Step 3: Annual Maxima Series
    ams_df = build_ams(innings_df)

    # Step 4: IFD table
    ifd_table = build_ifd_table(ams_df, players)
    ifd_path = OUTPUT_DIR / "ifd_table.csv"
    ifd_table.to_csv(ifd_path, index=False)
    log.info("Saved IFD table -> %s", ifd_path)
    print("\n--- IFD Design Innings Scores ---")
    print(ifd_table.to_string(index=False))
    print()

    # Step 5: Plots
    plot_annual_maxima(
        ams_df,
        innings_df,
        players,
        OUTPUT_DIR / "plot1_annual_maxima.png",
    )
    plot_gev_frequency(
        ams_df,
        players,
        OUTPUT_DIR / "plot2_gev_frequency.png",
    )
    plot_intensity_duration(
        innings_df,
        players,
        OUTPUT_DIR / "plot3_intensity_duration_envelope.png",
    )

    log.info("Analysis complete. Outputs written to: %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
