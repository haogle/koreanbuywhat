"""
SeekingAlpha Top 10 Picks — Annual Backtest
============================================
Strategy: Buy equal-weight on first trading day of the year,
          hold until last trading day of the year.
Compare to SPY each year and cumulatively.

Data source: seekalpha.xlsx (user provided)
Price data:  yfinance (actual, auto-adjusted)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings("ignore")

STARTING_CAPITAL = 100_000

# ─────────────────────────────────────────────────────────────
# PICKS FROM EXCEL
# ─────────────────────────────────────────────────────────────
PICKS = {
    2022: ["XOM", "CI", "FNF", "BAC", "BNTX", "LYG"],
    2023: ["SMCI", "MOD", "PDD", "MNSO", "VRNA", "JXN", "ASC", "VLO", "HDSN", "ENGIY"],
    2024: ["APP", "CLS", "ANF", "RYCEY", "MOD", "META", "GCT", "MHO", "ISNPY", "LPG"],
    2025: ["CLS", "OPFI", "AGX", "EAT", "GCT", "CRDO", "NBIS", "WLDN", "DXPE", "PTGX"],
    2026: ["CLS", "MU", "AMD", "CIEN", "COHR", "ALL", "INCY", "B", "WLDN", "ATI"],
}

REPORTED = {
    2022: {"XOM": 0.80, "CI": 0.40, "FNF": -0.10, "BAC": -0.26, "BNTX": -0.35, "LYG": -0.05},
    2023: {"SMCI": 2.46, "MOD": 1.55, "PDD": 0.79, "MNSO": 0.85, "VRNA": 0.50,
           "JXN": 0.40, "ASC": 0.12, "VLO": 0.05, "HDSN": -0.15, "ENGIY": 0.18},
    2024: {"APP": 7.13, "CLS": 2.41, "ANF": 2.85, "RYCEY": 2.20, "MOD": 0.94,
           "META": 0.58, "GCT": 0.505, "MHO": 0.25, "ISNPY": 0.35, "LPG": -0.054},
    2025: {"CLS": 2.418, "OPFI": 1.340, "AGX": 0.905, "EAT": 0.652, "GCT": 0.284,
           "CRDO": 0.153, "NBIS": -0.124, "WLDN": 0.051, "DXPE": 0.082, "PTGX": -0.056},
}

YEAR_RANGES = {
    2022: ("2022-01-03", "2022-12-30"),
    2023: ("2023-01-03", "2023-12-29"),
    2024: ("2024-01-02", "2024-12-31"),
    2025: ("2025-01-02", "2025-12-31"),
    2026: ("2026-01-02", "2026-03-11"),   # YTD
}

# ─────────────────────────────────────────────────────────────
# FETCH ALL PRICES
# ─────────────────────────────────────────────────────────────
all_tickers = set(["SPY"])
for t_list in PICKS.values():
    all_tickers.update(t_list)

print(f"Fetching prices for {len(all_tickers)} tickers…\n")
raw = yf.download(
    list(all_tickers),
    start="2022-01-01",
    end="2026-03-12",
    auto_adjust=True,
    progress=False,
)

prices = {}
for t in all_tickers:
    try:
        if isinstance(raw.columns, pd.MultiIndex):
            s = raw["Close"][t].dropna()
        else:
            s = raw["Close"].dropna()
        if len(s) > 0:
            s.index = s.index.strftime("%Y-%m-%d")
            prices[t] = s
    except Exception:
        pass

def get_px(ticker, date):
    if ticker not in prices:
        return None
    s = prices[ticker]
    candidates = s[s.index <= date]
    return float(candidates.iloc[-1]) if len(candidates) > 0 else None

def first_trading_day(year_str_start):
    """Find first available date on or after start."""
    s = prices["SPY"]
    candidates = s[s.index >= year_str_start]
    return candidates.index[0] if len(candidates) > 0 else None

def last_trading_day(year_str_end):
    s = prices["SPY"]
    candidates = s[s.index <= year_str_end]
    return candidates.index[-1] if len(candidates) > 0 else None

# ─────────────────────────────────────────────────────────────
# STEP 1 — VERIFICATION TABLE
# ─────────────────────────────────────────────────────────────
print("=" * 72)
print("  DATA VERIFICATION  (Reported vs Actual annual returns)")
print("=" * 72)

issues = []
for year in [2022, 2023, 2024, 2025]:
    start_d, end_d = YEAR_RANGES[year]
    buy_d  = first_trading_day(start_d)
    sell_d = last_trading_day(end_d)
    print(f"\n  ── {year}  (buy {buy_d} → sell {sell_d}) ──")
    print(f"  {'Ticker':<7} {'Reported':>10}  {'Actual':>10}  {'Diff':>8}  {'Status'}")
    for t in PICKS[year]:
        rep = REPORTED[year].get(t)
        p0  = get_px(t, buy_d)
        p1  = get_px(t, sell_d)
        if p0 and p1 and rep is not None:
            actual = p1 / p0 - 1
            diff   = actual - rep
            if abs(diff) < 0.08:
                status = "✓ match"
            elif abs(diff) < 0.20:
                status = "~ close"
            else:
                status = f"✗ off by {diff:+.0%}"
                issues.append((year, t, rep, actual))
            print(f"  {t:<7} {rep:>+10.1%}  {actual:>+10.1%}  {diff:>+8.1%}  {status}")
        elif rep is not None:
            print(f"  {t:<7} {rep:>+10.1%}  {'N/A':>10}  {'N/A':>8}  ⚠ no price data")
        else:
            print(f"  {t:<7} {'N/A':>10}  {'N/A':>10}  {'N/A':>8}  ⚠ no reported return")

print(f"\n  Total significant discrepancies: {len(issues)}")
if issues:
    print("  Notable issues:")
    for yr, t, rep, act in issues:
        print(f"    {yr} {t}: reported {rep:+.1%}, actual {act:+.1%}")

# ─────────────────────────────────────────────────────────────
# STEP 2 — ANNUAL BACKTEST (equal weight, actual prices)
# ─────────────────────────────────────────────────────────────
print(f"\n\n{'='*72}")
print("  BACKTEST RESULTS  (Equal-weight, buy Jan 1st, sell Dec 31st)")
print(f"{'='*72}")
print(f"  {'Year':<6} {'Portfolio':>10}  {'SPY':>8}  {'Alpha':>8}  "
      f"{'Best Pick':>20}  {'Worst Pick':>20}")
print(f"  {'-'*6} {'-'*10}  {'-'*8}  {'-'*8}  {'-'*20}  {'-'*20}")

annual_results = {}
cumulative_port  = STARTING_CAPITAL
cumulative_spy   = STARTING_CAPITAL
cumulative_hist  = []

for year in [2022, 2023, 2024, 2025, 2026]:
    start_d, end_d = YEAR_RANGES[year]
    buy_d  = first_trading_day(start_d)
    sell_d = last_trading_day(end_d)

    pick_returns = {}
    for t in PICKS[year]:
        p0 = get_px(t, buy_d)
        p1 = get_px(t, sell_d)
        if p0 and p1:
            pick_returns[t] = p1 / p0 - 1

    if not pick_returns:
        continue

    port_ret  = np.mean(list(pick_returns.values()))
    spy_p0    = get_px("SPY", buy_d)
    spy_p1    = get_px("SPY", sell_d)
    spy_ret   = spy_p1 / spy_p0 - 1 if spy_p0 and spy_p1 else 0
    alpha     = port_ret - spy_ret

    best_t    = max(pick_returns, key=pick_returns.get)
    worst_t   = min(pick_returns, key=pick_returns.get)
    label     = "(YTD)" if year == 2026 else ""

    print(f"  {year}{label:<3} {port_ret:>+10.1%}  {spy_ret:>+8.1%}  {alpha:>+8.1%}  "
          f"{best_t+' '+f'({pick_returns[best_t]:+.0%})':>20}  "
          f"{worst_t+' '+f'({pick_returns[worst_t]:+.0%})':>20}")

    cumulative_port *= (1 + port_ret)
    cumulative_spy  *= (1 + spy_ret)
    annual_results[year] = {
        "port_ret": port_ret,
        "spy_ret": spy_ret,
        "alpha": alpha,
        "pick_returns": pick_returns,
        "buy_date": buy_d,
        "sell_date": sell_d,
    }
    cumulative_hist.append({
        "year": year,
        "port": cumulative_port,
        "spy": cumulative_spy,
        "port_ret": port_ret,
        "spy_ret": spy_ret,
    })

cum_port_ret = (cumulative_port / STARTING_CAPITAL - 1) * 100
cum_spy_ret  = (cumulative_spy  / STARTING_CAPITAL - 1) * 100
print(f"\n  {'CUMULATIVE':<6} {cum_port_ret:>+10.1f}%  {cum_spy_ret:>+8.1f}%  "
      f"{cum_port_ret-cum_spy_ret:>+8.1f}%")
print(f"  Starting $100K → Portfolio: ${cumulative_port:,.0f}  |  SPY: ${cumulative_spy:,.0f}")

# ─────────────────────────────────────────────────────────────
# STEP 3 — PER-STOCK DETAIL TABLE
# ─────────────────────────────────────────────────────────────
print(f"\n\n{'='*72}")
print("  PER-STOCK RETURNS (Actual from yfinance)")
print(f"{'='*72}")
for year, res in annual_results.items():
    label = " (YTD)" if year == 2026 else ""
    print(f"\n  {year}{label}")
    sorted_picks = sorted(res["pick_returns"].items(), key=lambda x: -x[1])
    for t, r in sorted_picks:
        bar = "█" * int(abs(r) * 10)
        sign = "+" if r >= 0 else ""
        color_tag = "↑" if r >= 0 else "↓"
        print(f"    {t:<7} {f'{r:+.1%}':<10}  {color_tag} {bar[:30]}")

# ─────────────────────────────────────────────────────────────
# STEP 4 — DAILY PORTFOLIO CURVES
# ─────────────────────────────────────────────────────────────
# Build daily series for plotting (each year independent + cumulative run)
spy_series  = prices["SPY"]
port_daily  = {}   # year -> pd.Series of daily values

for year, res in annual_results.items():
    buy_d  = res["buy_date"]
    sell_d = res["sell_date"]
    tickers = list(res["pick_returns"].keys())
    n = len(tickers)
    alloc = STARTING_CAPITAL / n  # equal weight per pick

    # date range
    date_range = [d for d in spy_series.index if buy_d <= d <= sell_d]
    daily_vals = []
    for d in date_range:
        val = 0
        for t in tickers:
            p0 = get_px(t, buy_d)
            pd_ = get_px(t, d)
            if p0 and pd_:
                val += alloc * (pd_ / p0)
            else:
                val += alloc  # flat if no data
        daily_vals.append(val)
    port_daily[year] = pd.Series(daily_vals, index=pd.to_datetime(date_range))

# cumulative path (chain years)
cum_port_series = []
cum_spy_series  = []
running_port = STARTING_CAPITAL
running_spy  = STARTING_CAPITAL

for year, res in annual_results.items():
    buy_d  = res["buy_date"]
    sell_d = res["sell_date"]
    tickers = list(res["pick_returns"].keys())
    n = len(tickers)
    date_range = [d for d in spy_series.index if buy_d <= d <= sell_d]
    alloc_port = running_port / n
    alloc_spy  = running_spy

    for d in date_range:
        val_port = sum(
            alloc_port * (get_px(t, d) or get_px(t, buy_d)) / (get_px(t, buy_d) or 1)
            for t in tickers
        )
        spy0 = get_px("SPY", buy_d)
        spyd = get_px("SPY", d)
        val_spy = alloc_spy * (spyd / spy0) if spy0 and spyd else alloc_spy
        cum_port_series.append({"date": pd.Timestamp(d), "value": val_port})
        cum_spy_series.append({"date": pd.Timestamp(d), "value": val_spy})

    running_port = val_port
    running_spy  = val_spy

cum_port_df = pd.DataFrame(cum_port_series).set_index("date")
cum_spy_df  = pd.DataFrame(cum_spy_series).set_index("date")

# ─────────────────────────────────────────────────────────────
# STEP 5 — PLOTS
# ─────────────────────────────────────────────────────────────
YEAR_COLORS = {2022: "#F44336", 2023: "#4CAF50", 2024: "#2196F3",
               2025: "#FF9800", 2026: "#9C27B0"}

fig = plt.figure(figsize=(16, 16))
gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

ax_cum  = fig.add_subplot(gs[0, :])   # cumulative full width
ax_ann  = fig.add_subplot(gs[1, 0])   # annual bar
ax_heat = fig.add_subplot(gs[1, 1])   # alpha heatmap
axes_yr = [fig.add_subplot(gs[2, i]) for i in range(2)]  # per-year

fig.suptitle(
    "SeekingAlpha Top-10 Picks Backtest  |  Equal-Weight  |  Buy Jan 1st → Hold Full Year",
    fontsize=13, fontweight="bold"
)

# ── Cumulative curve ──
ax_cum.plot(cum_port_df.index, cum_port_df["value"],
            color="#2196F3", linewidth=2.5, label=f"SA Portfolio ({cum_port_ret:+.1f}%)")
ax_cum.plot(cum_spy_df.index, cum_spy_df["value"],
            color="#888888", linewidth=2, linestyle="--",
            label=f"SPY ({cum_spy_ret:+.1f}%)")
ax_cum.set_title("Cumulative Portfolio vs SPY  (2022–2026 YTD)")
ax_cum.set_ylabel("Portfolio Value ($)")
ax_cum.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax_cum.legend(fontsize=10)
ax_cum.grid(True, alpha=0.3)
# year shading
for year, res in annual_results.items():
    ax_cum.axvspan(pd.Timestamp(res["buy_date"]), pd.Timestamp(res["sell_date"]),
                   alpha=0.04, color=YEAR_COLORS[year])
    mid = pd.Timestamp(res["buy_date"]) + (pd.Timestamp(res["sell_date"]) - pd.Timestamp(res["buy_date"])) / 2
    ax_cum.text(mid, ax_cum.get_ylim()[0] * 1.02 if ax_cum.get_ylim()[0] > 0 else 5000,
                str(year), ha="center", fontsize=8, color=YEAR_COLORS[year], alpha=0.7)

import matplotlib.dates as mdates
ax_cum.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
ax_cum.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.setp(ax_cum.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)

# ── Annual return bar ──
years_list = list(annual_results.keys())
port_rets  = [annual_results[y]["port_ret"] * 100 for y in years_list]
spy_rets   = [annual_results[y]["spy_ret"]  * 100 for y in years_list]
x = np.arange(len(years_list))
w = 0.35
b1 = ax_ann.bar(x - w/2, port_rets, w, label="SA Portfolio",
                color=[YEAR_COLORS[y] for y in years_list], alpha=0.85)
b2 = ax_ann.bar(x + w/2, spy_rets,  w, label="SPY",
                color="#888888", alpha=0.6)
ax_ann.set_xticks(x)
ax_ann.set_xticklabels([str(y) + (" YTD" if y == 2026 else "") for y in years_list])
ax_ann.set_ylabel("Return (%)")
ax_ann.set_title("Annual Return: SA Portfolio vs SPY")
ax_ann.axhline(0, color="black", linewidth=0.8)
ax_ann.legend()
ax_ann.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
ax_ann.grid(True, alpha=0.3, axis="y")
for bar, val in zip(b1, port_rets):
    ax_ann.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + (1 if val >= 0 else -4),
                f"{val:+.0f}%", ha="center", va="bottom", fontsize=7)

# ── Per-stock heatmap ──
all_tickers_heat = []
heat_data = {}
for year in years_list:
    for t, r in annual_results[year]["pick_returns"].items():
        if t not in all_tickers_heat:
            all_tickers_heat.append(t)
        heat_data[(t, year)] = r * 100

heat_matrix = np.full((len(all_tickers_heat), len(years_list)), np.nan)
for i, t in enumerate(all_tickers_heat):
    for j, y in enumerate(years_list):
        if (t, y) in heat_data:
            heat_matrix[i, j] = heat_data[(t, y)]

im = ax_heat.imshow(heat_matrix, cmap="RdYlGn", aspect="auto", vmin=-80, vmax=200)
ax_heat.set_xticks(range(len(years_list)))
ax_heat.set_xticklabels([str(y) for y in years_list], fontsize=8)
ax_heat.set_yticks(range(len(all_tickers_heat)))
ax_heat.set_yticklabels(all_tickers_heat, fontsize=7)
ax_heat.set_title("Return Heatmap by Stock & Year")
for i in range(len(all_tickers_heat)):
    for j in range(len(years_list)):
        v = heat_matrix[i, j]
        if not np.isnan(v):
            ax_heat.text(j, i, f"{v:+.0f}%", ha="center", va="center",
                         fontsize=6, color="black" if abs(v) < 100 else "white")
plt.colorbar(im, ax=ax_heat, shrink=0.8, label="Return %")

# ── Per-year curves (2022-23 | 2024-25) ──
year_pairs = [(2022, 2023), (2024, 2025)]
for ax, (ya, yb) in zip(axes_yr, year_pairs):
    for year in [ya, yb]:
        if year not in port_daily:
            continue
        s = port_daily[year]
        spy0 = get_px("SPY", annual_results[year]["buy_date"])
        spy_norm = pd.Series(
            [get_px("SPY", d.strftime("%Y-%m-%d")) for d in s.index],
            index=s.index
        )
        spy_norm = spy_norm / spy_norm.iloc[0] * STARTING_CAPITAL

        label_yr = str(year) + (" YTD" if year == 2026 else "")
        ax.plot(s.index, s.values, color=YEAR_COLORS[year], linewidth=2,
                label=f"{label_yr} SA ({annual_results[year]['port_ret']:+.1%})")
        ax.plot(s.index, spy_norm.values, color=YEAR_COLORS[year],
                linewidth=1.2, linestyle="--", alpha=0.6,
                label=f"{label_yr} SPY ({annual_results[year]['spy_ret']:+.1%})")
    ax.set_title(f"{ya} & {yb} — Daily Performance")
    ax.set_ylabel("Value ($)")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=7)

output = "/Users/huhao/Documents/Claude/seekingalpha_backtest.png"
plt.savefig(output, dpi=150, bbox_inches="tight")
print(f"\nChart saved → {output}")
plt.show()
