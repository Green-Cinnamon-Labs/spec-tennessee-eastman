"""
Tennessee Eastman Process — simulation log plotter.

Usage (from the analysis/ directory):
    python -m tep_analysis.plot
    python -m tep_analysis.plot --csv ../tennessee-eastman-service/simulation_log.csv
    python -m tep_analysis.plot --csv simulation_log.csv --ramp 2.0
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ── default CSV path (relative to this file → repo root) ──────────────────────
_DEFAULT_CSV = Path(__file__).parent.parent.parent / "tennessee-eastman-service" / "simulation_log.csv"

# ── ISD / alarm thresholds ────────────────────────────────────────────────────
ISD = {
    "XMEAS(7)":  (None, 3000.0),   # Reactor Pressure  kPa  — shut >3000
    "XMEAS(9)":  (None,  175.0),   # Reactor Temp      °C   — shut >175
    "XMEAS(8)":  (10.0,   90.0),   # Reactor Level     %    — shut <10 or >90
    "XMEAS(12)": (10.0,   90.0),   # Sep Level         %    — shut <10 or >90
    "XMEAS(15)": (10.0,   90.0),   # Stripper Level    %    — shut <10 or >90
}

# ── panel layout ──────────────────────────────────────────────────────────────
# (title, ylabel, [(col, label, color), ...], y_limits_or_None)
PANELS = [
    (
        "Reactor Pressure",
        "kPa",
        [("XMEAS(7)", "Reactor P", "#e05c5c")],
        (None, None),
    ),
    (
        "Reactor Temperature",
        "°C",
        [("XMEAS(9)", "Reactor T", "#e08a3c")],
        (None, None),
    ),
    (
        "Reactor Level",
        "%",
        [("XMEAS(8)", "Reactor Lv", "#5c9ee0")],
        (0, 100),
    ),
    (
        "Sep & Stripper Levels",
        "%",
        [
            ("XMEAS(12)", "Sep Lv",      "#5cb85c"),
            ("XMEAS(15)", "Stripper Lv", "#9b59b6"),
        ],
        (0, 100),
    ),
    (
        "Feed Valve Ramp",
        "%",
        [
            ("XMV(1)", "D Feed (XMV1)",   "#3498db"),
            ("XMV(2)", "E Feed (XMV2)",   "#2ecc71"),
            ("XMV(3)", "A Feed (XMV3)",   "#e74c3c"),
            ("XMV(4)", "A&C Feed (XMV4)", "#f39c12"),
        ],
        (0, 100),
    ),
    (
        "Recycle Flow",
        "kscmh",
        [("XMEAS(5)", "Recycle Flow", "#1abc9c")],
        (None, None),
    ),
    (
        "Purge: Flow (kscmh) & Valve (%)",
        "kscmh / %",
        [
            ("XMEAS(10)", "Purge Flow",    "#e74c3c"),
            ("XMV(6)",    "Purge Valve %", "#c0392b"),
        ],
        (None, None),
    ),
    (
        "Sep & Stripper Underflow (MV)",
        "%",
        [
            ("XMV(7)", "Sep Underflow",    "#3498db"),
            ("XMV(8)", "Stripper Product", "#2ecc71"),
        ],
        (0, 100),
    ),
    (
        "max |dx/dt|  (deriv norm)",
        "state units / h",
        [("deriv_norm", "deriv_norm", "#95a5a6")],
        (None, None),
    ),
    # ── ODE state diagnostics (only present when YY columns are logged) ────────
    (
        "Reactor Vapor total  Σ UCVR  (YY[0–7])",
        "kmol",
        [("UCVR_total", "Σ UCVR", "#e05c5c")],
        (None, None),
    ),
    (
        "Compressor Vapor total  Σ UCVV  (YY[27–34])",
        "kmol",
        [("UCVV_total", "Σ UCVV", "#3498db")],
        (None, None),
    ),
    (
        "UCVR components  A–H  (YY[0–7])",
        "kmol",
        [
            ("YY[0]", "A", "#e74c3c"),
            ("YY[1]", "B", "#e67e22"),
            ("YY[2]", "C", "#f1c40f"),
            ("YY[3]", "D", "#2ecc71"),
            ("YY[4]", "E", "#1abc9c"),
            ("YY[5]", "F", "#3498db"),
            ("YY[6]", "G", "#9b59b6"),
            ("YY[7]", "H", "#e91e63"),
        ],
        (None, None),
    ),
]


def _add_thresholds(ax, col: str) -> None:
    if col not in ISD:
        return
    lo, hi = ISD[col]
    kw = dict(linestyle="--", linewidth=0.8, alpha=0.7)
    if hi is not None:
        ax.axhline(hi, color="#e05c5c", **kw, label=f"ISD >{hi}")
    if lo is not None:
        ax.axhline(lo, color="#e05c5c", **kw, label=f"ISD <{lo}")


def _add_ramp_markers(ax, ramp_h: float) -> None:
    """Vertical dotted lines at 25 / 50 / 75 / 100 % of the cold-start ramp."""
    for frac, label in [(0.25, "25%"), (0.5, "50%"), (0.75, "75%"), (1.0, "100%")]:
        t = ramp_h * frac
        ax.axvline(t, color="#888888", linestyle=":", linewidth=0.7, alpha=0.7)
        ylo, yhi = ax.get_ylim()
        ax.text(t, yhi, label, fontsize=5, color="#888888",
                ha="center", va="bottom", clip_on=True)


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename analytics-export style columns (xmeas_7, xmv_6) to plot style (XMEAS(7), XMV(6))."""
    rename = {}
    for col in df.columns:
        low = col.lower()
        if low.startswith("xmeas_") and low[6:].isdigit():
            rename[col] = f"XMEAS({low[6:]})"
        elif low.startswith("xmv_") and low[4:].isdigit():
            rename[col] = f"XMV({low[4:]})"
    return df.rename(columns=rename) if rename else df


def plot(csv_path: Path, ramp_h: float | None = None) -> None:
    print(f"Loading {csv_path} …")
    df = pd.read_csv(csv_path)
    df = _normalise_columns(df)
    print(f"  {len(df)} rows  |  t = {df['t_h'].min():.4f} … {df['t_h'].max():.4f} h")
    print(f"  columns: {list(df.columns)}")

    # ── derived ODE state columns (present only when runtime logs YY) ─────────
    yy_ucvr = [f"YY[{i}]" for i in range(8)]
    yy_ucvv = [f"YY[{i}]" for i in range(27, 35)]
    if all(c in df.columns for c in yy_ucvr):
        df["UCVR_total"] = df[yy_ucvr].sum(axis=1)
    if all(c in df.columns for c in yy_ucvv):
        df["UCVV_total"] = df[yy_ucvv].sum(axis=1)

    t = df["t_h"]

    # Only keep panels that have at least one column present in the data
    active_panels = [
        panel for panel in PANELS
        if any(col in df.columns for col, _, _ in panel[2])
    ]
    if not active_panels:
        print("No matching columns found in CSV — nothing to plot.")
        return

    n_panels = len(active_panels)
    ncols = 2
    nrows = (n_panels + 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(14, max(nrows * 3, 4)),
                             sharex=True, constrained_layout=True)
    fig.suptitle(f"TEP — {csv_path.name}", fontsize=13, fontweight="bold")

    flat_axes = axes.flatten() if hasattr(axes, 'flatten') else [axes]

    for idx, (title, ylabel, series, ylim) in enumerate(active_panels):
        ax = flat_axes[idx]
        for col, label, color in series:
            if col not in df.columns:
                continue
            ax.plot(t, df[col], label=label, color=color, linewidth=1.0)
            _add_thresholds(ax, col)

        ax.set_title(title, fontsize=9, fontweight="bold")
        ax.set_ylabel(ylabel, fontsize=8)
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%.3f"))
        if ylim != (None, None):
            lo, hi = ylim
            current_lo, current_hi = ax.get_ylim()
            ax.set_ylim(lo if lo is not None else current_lo,
                        hi if hi is not None else current_hi)
        if len(series) > 1 or any(col in ISD for col, _, _ in series):
            ax.legend(fontsize=7, loc="upper right")
        ax.grid(True, linewidth=0.4, alpha=0.5)

        if ramp_h is not None:
            _add_ramp_markers(ax, ramp_h)

    # hide any spare axes
    for idx in range(n_panels, len(flat_axes)):
        flat_axes[idx].set_visible(False)

    # shared x label on bottom row
    for ax in flat_axes[(nrows - 1) * ncols:]:
        ax.set_xlabel("Simulated time (h)", fontsize=8)

    out = csv_path.with_suffix(".png")
    fig.savefig(out, dpi=150)
    print(f"Saved → {out}")
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot TEP simulation_log.csv")
    parser.add_argument(
        "--csv",
        type=Path,
        default=_DEFAULT_CSV,
        help=f"Path to simulation_log.csv (default: {_DEFAULT_CSV})",
    )
    parser.add_argument(
        "--ramp",
        type=float,
        default=None,
        metavar="HOURS",
        help="Cold-start ramp duration in simulated hours; draws phase markers at 25/50/75/100%%",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        sys.exit(1)

    plot(args.csv, ramp_h=args.ramp)


if __name__ == "__main__":
    main()
