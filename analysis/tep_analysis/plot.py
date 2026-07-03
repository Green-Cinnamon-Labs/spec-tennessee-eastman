# """
# Tennessee Eastman Process — simulation log plotter.

# Usage (from the analysis/ directory):
#     python -m tep_analysis.plot
#     python -m tep_analysis.plot --csv ../tennessee-eastman-service/simulation_log.csv
#     python -m tep_analysis.plot --csv simulation_log.csv --ramp 2.0
# """

# import argparse
# import sys
# from pathlib import Path

# import pandas as pd
# import matplotlib.pyplot as plt
# import matplotlib.ticker as ticker
# from scipy.signal import savgol_filter

# # ── default paths ─────────────────────────────────────────────────────────────
# _SIMULATIONS_DIR = Path(__file__).parent.parent.parent / "docs" / "simulations"
# _DEFAULT_CSV     = _SIMULATIONS_DIR / "simulation_log.csv"
# _PLOTS_DIR       = _SIMULATIONS_DIR / "plots"

# # ── ISD / alarm thresholds ────────────────────────────────────────────────────
# ISD = {
#     "XMEAS(7)":  (None, 3000.0),   # Reactor Pressure  kPa  — shut >3000
#     "XMEAS(9)":  (None,  175.0),   # Reactor Temp      °C   — shut >175
#     "XMEAS(8)":  (10.0,   90.0),   # Reactor Level     %    — shut <10 or >90
#     "XMEAS(12)": (10.0,   90.0),   # Sep Level         %    — shut <10 or >90
#     "XMEAS(15)": (10.0,   90.0),   # Stripper Level    %    — shut <10 or >90
# }

# # ── panel layout ──────────────────────────────────────────────────────────────
# # (title, ylabel, [(col, label, color), ...], y_limits_or_None)
# PANELS = [
#     (
#         "Reactor Pressure",
#         "kPa",
#         [("XMEAS(7)", "Reactor P", "#e05c5c")],
#         (None, None),
#     ),
#     (
#         "Reactor Temperature",
#         "°C",
#         [("XMEAS(9)", "Reactor T", "#e08a3c")],
#         (None, None),
#     ),
#     (
#         "Reactor Level",
#         "%",
#         [("XMEAS(8)", "Reactor Lv", "#5c9ee0")],
#         (0, 100),
#     ),
#     (
#         "Sep & Stripper Levels",
#         "%",
#         [
#             ("XMEAS(12)", "Sep Lv",      "#5cb85c"),
#             ("XMEAS(15)", "Stripper Lv", "#9b59b6"),
#         ],
#         (0, 100),
#     ),
#     (
#         "Feed Valve Ramp",
#         "%",
#         [
#             ("XMV(1)", "D Feed (XMV1)",   "#3498db"),
#             ("XMV(2)", "E Feed (XMV2)",   "#2ecc71"),
#             ("XMV(3)", "A Feed (XMV3)",   "#e74c3c"),
#             ("XMV(4)", "A&C Feed (XMV4)", "#f39c12"),
#         ],
#         (0, 100),
#     ),
#     (
#         "Reactor A, B & C Composition  (XMEAS(23,24,25))",
#         "mol%",
#         [
#             ("XMEAS(23)", "A mol%  (XMEAS23)", "#e74c3c"),
#             ("XMEAS(24)", "B mol%  (XMEAS24)", "#f39c12"),
#             ("XMEAS(25)", "C mol%  (XMEAS25)", "#2ecc71"),
#         ],
#         (None, None),
#     ),
#     (
#         "Recycle Flow",
#         "kscmh",
#         [("XMEAS(5)", "Recycle Flow", "#1abc9c")],
#         (None, None),
#     ),
#     (
#         "Purge: Flow (kscmh) & Valve (%)",
#         "kscmh / %",
#         [
#             ("XMEAS(10)", "Purge Flow",    "#e74c3c"),
#             ("XMV(6)",    "Purge Valve %", "#c0392b"),
#         ],
#         (None, None),
#     ),
#     (
#         "Sep & Stripper Underflow (MV)",
#         "%",
#         [
#             ("XMV(7)", "Sep Underflow",    "#3498db"),
#             ("XMV(8)", "Stripper Product", "#2ecc71"),
#         ],
#         (0, 100),
#     ),
#     (
#         "max |dx/dt|  (deriv norm)",
#         "state units / h",
#         [("deriv_norm", "deriv_norm", "#95a5a6")],
#         (None, None),
#     ),
#     # ── ODE state diagnostics (only present when YY columns are logged) ────────
#     (
#         "Reactor Vapor total  Σ UCVR  (YY[0–7])",
#         "kmol",
#         [("UCVR_total", "Σ UCVR", "#e05c5c")],
#         (None, None),
#     ),
#     (
#         "Compressor Vapor total  Σ UCVV  (YY[27–34])",
#         "kmol",
#         [("UCVV_total", "Σ UCVV", "#3498db")],
#         (None, None),
#     ),
#     (
#         "UCVR components  A–H  (YY[0–7])",
#         "kmol",
#         [
#             ("YY[0]", "A", "#e74c3c"),
#             ("YY[1]", "B", "#e67e22"),
#             ("YY[2]", "C", "#f1c40f"),
#             ("YY[3]", "D", "#2ecc71"),
#             ("YY[4]", "E", "#1abc9c"),
#             ("YY[5]", "F", "#3498db"),
#             ("YY[6]", "G", "#9b59b6"),
#             ("YY[7]", "H", "#e91e63"),
#         ],
#         (None, None),
#     ),
# ]


# def _add_thresholds(ax, col: str) -> None:
#     if col not in ISD:
#         return
#     lo, hi = ISD[col]
#     kw = dict(linestyle="--", linewidth=0.8, alpha=0.7)
#     if hi is not None:
#         ax.axhline(hi, color="#e05c5c", **kw, label=f"ISD >{hi}")
#     if lo is not None:
#         ax.axhline(lo, color="#e05c5c", **kw, label=f"ISD <{lo}")


# def _add_ramp_markers(ax, ramp_h: float) -> None:
#     """Vertical dotted lines at 25 / 50 / 75 / 100 % of the cold-start ramp."""
#     for frac, label in [(0.25, "25%"), (0.5, "50%"), (0.75, "75%"), (1.0, "100%")]:
#         t = ramp_h * frac
#         ax.axvline(t, color="#888888", linestyle=":", linewidth=0.7, alpha=0.7)
#         ylo, yhi = ax.get_ylim()
#         ax.text(t, yhi, label, fontsize=5, color="#888888",
#                 ha="center", va="bottom", clip_on=True)


# def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
#     """Rename analytics-export style columns (xmeas_7, xmv_6) to plot style (XMEAS(7), XMV(6))."""
#     rename = {}
#     for col in df.columns:
#         low = col.lower()
#         if low.startswith("xmeas_") and low[6:].isdigit():
#             rename[col] = f"XMEAS({low[6:]})"
#         elif low.startswith("xmv_") and low[4:].isdigit():
#             rename[col] = f"XMV({low[4:]})"
#     return df.rename(columns=rename) if rename else df


# def _smooth(series: pd.Series, window: int) -> pd.Series:
#     """Savitzky-Golay com fallback para rolling mean se scipy não disponível."""
#     n = len(series)
#     w = min(window | 1, n if n % 2 == 1 else n - 1)  # garante ímpar e ≤ n
#     if w < 3:
#         return series
#     try:
#         return pd.Series(savgol_filter(series.values, window_length=w, polyorder=2),
#                          index=series.index)
#     except Exception:
#         return series.rolling(window=w, center=True, min_periods=1).mean()


# def plot(csv_path: Path, ramp_h: float | None = None, smooth: int = 0,
#          tmin: float | None = None, tmax: float | None = None) -> None:
#     print(f"Loading {csv_path} ...")
#     df = pd.read_csv(csv_path)
#     df = _normalise_columns(df)
#     print(f"  {len(df)} rows  |  t = {df['t_h'].min():.4f} ... {df['t_h'].max():.4f} h")
#     print(f"  columns: {list(df.columns)}")

#     # ── suavização opcional (Savitzky-Golay) ──────────────────────────────────
#     if smooth > 2:
#         for col in df.columns:
#             if col != "t_h":
#                 df[col] = _smooth(df[col], smooth)

#     # ── derived ODE state columns (present only when runtime logs YY) ─────────
#     yy_ucvr = [f"YY[{i}]" for i in range(8)]
#     yy_ucvv = [f"YY[{i}]" for i in range(27, 35)]
#     if all(c in df.columns for c in yy_ucvr):
#         df["UCVR_total"] = df[yy_ucvr].sum(axis=1)
#     if all(c in df.columns for c in yy_ucvv):
#         df["UCVV_total"] = df[yy_ucvv].sum(axis=1)

#     t = df["t_h"]

#     # Only keep panels that have at least one column present in the data
#     active_panels = [
#         panel for panel in PANELS
#         if any(col in df.columns for col, _, _ in panel[2])
#     ]
#     if not active_panels:
#         print("No matching columns found in CSV — nothing to plot.")
#         return

#     n_panels = len(active_panels)
#     ncols = 2
#     nrows = (n_panels + 1) // ncols

#     fig, axes = plt.subplots(nrows, ncols, figsize=(14, max(nrows * 3, 4)),
#                              sharex=True, constrained_layout=True)
#     fig.suptitle(f"TEP — {csv_path.name}", fontsize=13, fontweight="bold")

#     flat_axes = axes.flatten() if hasattr(axes, 'flatten') else [axes]

#     for idx, (title, ylabel, series, ylim) in enumerate(active_panels):
#         ax = flat_axes[idx]
#         for col, label, color in series:
#             if col not in df.columns:
#                 continue
#             ax.plot(t, df[col], label=label, color=color, linewidth=1.0)
#             _add_thresholds(ax, col)

#         ax.set_title(title, fontsize=9, fontweight="bold")
#         ax.set_ylabel(ylabel, fontsize=8)
#         ax.tick_params(labelsize=7)
#         ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%.3f"))
#         if ylim != (None, None):
#             lo, hi = ylim
#             current_lo, current_hi = ax.get_ylim()
#             ax.set_ylim(lo if lo is not None else current_lo,
#                         hi if hi is not None else current_hi)
#         if len(series) > 1 or any(col in ISD for col, _, _ in series):
#             ax.legend(fontsize=7, loc="upper right")
#         ax.grid(True, linewidth=0.4, alpha=0.5)

#         if ramp_h is not None:
#             _add_ramp_markers(ax, ramp_h)

#     # ── Painel normalizado: variáveis com unidades mistas num eixo 0–1 ─────────
#     # Candidatos: pressão, temperatura, composição A e C — se presentes no CSV
#     norm_candidates = [
#         ("XMEAS(7)",  "Pressão (kPa)",   "#e05c5c", 2400, 3200),
#         ("XMEAS(9)",  "Temperatura (°C)", "#e08a3c",   80,  175),
#         ("XMEAS(23)", "A mol%",           "#e74c3c",   20,   40),
#         ("XMEAS(25)", "C mol%",           "#2ecc71",   20,   40),
#     ]
#     norm_series = [(col, lbl, clr, lo, hi)
#                    for col, lbl, clr, lo, hi in norm_candidates
#                    if col in df.columns]
#     if len(norm_series) >= 2 and n_panels < len(flat_axes):
#         ax_n = flat_axes[n_panels]
#         ax_n.set_visible(True)
#         for col, lbl, clr, lo, hi in norm_series:
#             norm_vals = (df[col] - lo) / (hi - lo)
#             ax_n.plot(t, norm_vals, label=lbl, color=clr, linewidth=1.0)
#         ax_n.set_title("Comparacao normalizada (0=min, 1=max de escala)", fontsize=9, fontweight="bold")
#         ax_n.set_ylabel("[-]", fontsize=8)
#         ax_n.set_ylim(-0.05, 1.05)
#         ax_n.tick_params(labelsize=7)
#         ax_n.xaxis.set_major_formatter(ticker.FormatStrFormatter("%.3f"))
#         ax_n.legend(fontsize=7, loc="upper right")
#         ax_n.grid(True, linewidth=0.4, alpha=0.5)
#         n_panels += 1

#     # hide any spare axes
#     for idx in range(n_panels, len(flat_axes)):
#         flat_axes[idx].set_visible(False)

#     # shared x label on bottom row
#     for ax in flat_axes[(nrows - 1) * ncols:]:
#         ax.set_xlabel("Simulated time (h)", fontsize=8)

#     # zoom de tempo: aplica xlim em todos os eixos visíveis (smooth já usou os dados completos)
#     if tmin is not None or tmax is not None:
#         x_lo = tmin if tmin is not None else t.min()
#         x_hi = tmax if tmax is not None else t.max()
#         for ax in flat_axes[:n_panels]:
#             ax.set_xlim(x_lo, x_hi)

#     _PLOTS_DIR.mkdir(parents=True, exist_ok=True)
#     out = _PLOTS_DIR / (csv_path.stem + ".png")
#     fig.savefig(out, dpi=150)
#     print(f"Saved -> {out}")
#     plt.show()


# def main() -> None:
#     parser = argparse.ArgumentParser(description="Plot TEP simulation_log.csv")
#     parser.add_argument(
#         "--csv",
#         type=Path,
#         default=_DEFAULT_CSV,
#         help=f"Path to simulation_log.csv (default: {_DEFAULT_CSV})",
#     )
#     parser.add_argument(
#         "--ramp",
#         type=float,
#         default=None,
#         metavar="HOURS",
#         help="Cold-start ramp duration in simulated hours; draws phase markers at 25/50/75/100%%",
#     )
#     parser.add_argument("--tmin", type=float, default=None, metavar="H", help="Início do intervalo de tempo (h)")
#     parser.add_argument("--tmax", type=float, default=None, metavar="H", help="Fim do intervalo de tempo (h)")
#     parser.add_argument(
#         "--smooth",
#         type=int,
#         default=11,
#         metavar="N",
#         help="Janela do filtro Savitzky-Golay (impar, default=11; 0 desativa)",
#     )
#     args = parser.parse_args()

#     if not args.csv.exists():
#         print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
#         sys.exit(1)

#     plot(args.csv, ramp_h=args.ramp, smooth=args.smooth, tmin=args.tmin, tmax=args.tmax)


# if __name__ == "__main__":
#     main()
