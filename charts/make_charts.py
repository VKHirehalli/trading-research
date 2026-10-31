"""Draw the README charts from data/*.csv, once for GitHub's light theme and
once for its dark theme (the README swaps them with <picture>).

Run: python charts/make_charts.py      (needs pandas and matplotlib)

Images are 1760 px wide, twice GitHub's ~880 px README column, so one design
pixel is two image pixels: px() converts design pixels to points.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.ticker import FuncFormatter, MultipleLocator

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
DPI = 200
WIDTH_IN = 8.8

plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]


def px(n):
    return n * 2 * 72 / DPI


# Reference palette, light and dark steps; surfaces are GitHub's own
THEMES = {
    "light": dict(surface="#ffffff", primary="#0b0b0b", secondary="#52514e", muted="#898781",
                  grid="#e1e0d9", axis="#c3c2b7", neg="#e34948", mid="#f0efec", pos="#2a78d6",
                  series=["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]),
    "dark": dict(surface="#0d1117", primary="#f0efec", secondary="#c3c2b7", muted="#898781",
                 grid="#2c2c2a", axis="#383835", neg="#e66767", mid="#383835", pos="#3987e5",
                 series=["#3987e5", "#d95926", "#199e70", "#c98500"]),
}
STRATEGIES = ["Gap trading", "Contrarian basket", "Opening-range breakout", "All three combined"]
RUPEES_M = FuncFormatter(lambda v, _: f"₹{v:.0f}M" if v else "0")


def figure(t, height):
    fig, ax = plt.subplots(figsize=(WIDTH_IN, height), dpi=DPI)
    fig.patch.set_facecolor(t["surface"])
    ax.set_facecolor(t["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["axis"])
    ax.spines["bottom"].set_linewidth(px(1))
    ax.tick_params(colors=t["muted"], labelsize=px(12), length=0, pad=px(6))
    return fig, ax


def titles(fig, t, title, subtitle):
    fig.text(0.02, 0.965, title, color=t["primary"], fontsize=px(16), fontweight="semibold", va="top")
    fig.text(0.02, 0.965 - px(24) / (fig.get_figheight() * 72), subtitle, color=t["secondary"],
             fontsize=px(13), va="top")


def save(fig, name, mode):
    fig.savefig(HERE / f"{name}-{mode}.png", facecolor=fig.get_facecolor())
    plt.close(fig)


def month_ends(df):
    return pd.to_datetime(dict(year=df["year"], month=df["month"], day=1)) + pd.offsets.MonthEnd(0)


def stocks_cumulative(t, mode):
    m = pd.read_csv(DATA / "stocks_monthly.csv")
    m["date"] = month_ends(m)
    fig, ax = figure(t, 4.8)
    fig.subplots_adjust(left=0.08, right=0.70, top=0.80, bottom=0.10)
    ax.grid(axis="y", color=t["grid"], linewidth=px(1))
    ax.set_axisbelow(True)
    for i, name in enumerate(STRATEGIES):
        s = m[m["strategy"] == name].sort_values("date")
        dates = [s["date"].iloc[0] - pd.offsets.MonthEnd(1), *s["date"]]
        total = [0.0, *(s["net_pnl_rs"].cumsum() / 1e6)]
        color = t["series"][i]
        ax.plot(dates, total, color=color, lw=px(2), solid_joinstyle="round", solid_capstyle="round", label=name)
        ax.plot(dates[-1], total[-1], "o", ms=px(8), color=color, mec=t["surface"], mew=px(2))
        ax.annotate(f"{name}  ₹{total[-1]:.1f}M", (dates[-1], total[-1]), xytext=(px(10), 0),
                    textcoords="offset points", va="center", color=t["primary"], fontsize=px(12),
                    annotation_clip=False)
    ax.yaxis.set_major_locator(MultipleLocator(5))
    ax.yaxis.set_major_formatter(RUPEES_M)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylim(bottom=0)
    legend = ax.legend(loc="upper left", frameon=False, fontsize=px(12), handlelength=1.6)
    for text in legend.get_texts():
        text.set_color(t["secondary"])
    titles(fig, t, "Stock strategies: cumulative net P&L, 2020–2025",
           "Backtest on minute data · ₹10 lakh (₹1M) fixed capital · 5x intraday leverage · after all costs")
    save(fig, "stocks-cumulative", mode)


def stocks_heatmap(t, mode):
    m = pd.read_csv(DATA / "stocks_monthly.csv")
    grid = m[m["strategy"] == "All three combined"].pivot(index="year", columns="month", values="return_pct")
    lim = grid.abs().max().max()
    cmap = LinearSegmentedColormap.from_list("diverging", [t["neg"], t["mid"], t["pos"]])
    fig, ax = figure(t, 3.9)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.76, bottom=0.22)
    ax.spines["bottom"].set_visible(False)
    mesh = ax.pcolormesh(grid.values, cmap=cmap, norm=TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim),
                         edgecolors=t["surface"], linewidth=px(2))
    ax.set_xticks([c + 0.5 for c in range(12)],
                  ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_yticks([r + 0.5 for r in range(len(grid))], grid.index.astype(str))
    ax.invert_yaxis()
    bar = fig.colorbar(mesh, ax=ax, orientation="horizontal", fraction=0.06, pad=0.12, aspect=50)
    bar.outline.set_visible(False)
    bar.ax.tick_params(colors=t["muted"], labelsize=px(11), length=0)
    bar.ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.0f}%".replace("-", "−") if v else "0%"))
    titles(fig, t, "All three stock strategies combined: return each month",
           "Red is a losing month, blue a winning one · % of ₹10 lakh fixed capital")
    save(fig, "stocks-monthly", mode)


def options_cumulative(t, mode):
    o = pd.read_csv(DATA / "nifty_options_orb_monthly.csv")
    o["date"] = pd.to_datetime(o["month"]) + pd.offsets.MonthEnd(0)
    dates = [o["date"].iloc[0] - pd.offsets.MonthEnd(1), *o["date"]]
    net = [0.0, *(o["net"].cumsum() / 1e6)]
    color = t["series"][0]
    fig, ax = figure(t, 4.2)
    fig.subplots_adjust(left=0.08, right=0.88, top=0.78, bottom=0.11)
    ax.grid(axis="y", color=t["grid"], linewidth=px(1))
    ax.set_axisbelow(True)
    ax.fill_between(dates, net, color=color, alpha=0.10, linewidth=0)
    ax.plot(dates, net, color=color, lw=px(2), solid_joinstyle="round", solid_capstyle="round")
    ax.plot(dates[-1], net[-1], "o", ms=px(8), color=color, mec=t["surface"], mew=px(2))
    ax.annotate(f"₹{net[-1]:.2f}M", (dates[-1], net[-1]), xytext=(px(10), 0), textcoords="offset points",
                va="center", color=t["primary"], fontsize=px(12), annotation_clip=False)
    ax.yaxis.set_major_locator(MultipleLocator(0.5))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"₹{v:.1f}M" if v else "0"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_ylim(bottom=0)
    titles(fig, t, "NIFTY options, opening-range breakout: cumulative net P&L",
           "Backtest on minute data · position capped at ₹1 lakh per trade · after all charges")
    save(fig, "options-orb-cumulative", mode)


if __name__ == "__main__":
    for mode, theme in THEMES.items():
        stocks_cumulative(theme, mode)
        stocks_heatmap(theme, mode)
        options_cumulative(theme, mode)
    print("wrote", sorted(p.name for p in HERE.glob("*.png")))
