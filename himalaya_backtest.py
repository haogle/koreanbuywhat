"""
Himalaya Capital Management — 13F Copy-Trade Backtest
Li Lu / CIK: 0001709323
Simulation: Q1 2022 → Q4 2025

Strategy:
  - On each 13F release date (~45 days after quarter end), rebalance
    portfolio to match Himalaya's disclosed weights.
  - Starting capital: $100,000
  - No leverage, long-only, proportional weighting.
  - Benchmark: SPY (S&P 500 ETF)

Data source: yfinance (free, no API key required)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
STARTING_CAPITAL = 100_000
BENCHMARK = "SPY"

# ─────────────────────────────────────────────────────────────
# 13F PORTFOLIO SNAPSHOTS
# Keys = 13F release date (the day we act on the filing)
# Values = {ticker: portfolio weight}  (must sum to ~1.0)
#
# Sources: SEC EDGAR CIK 0001709323, StockCircle, HedgeFollow,
#          ValuSider, 13f.info, WhaleWisdom
# ─────────────────────────────────────────────────────────────
SNAPSHOTS = {
    # ── 2022 ────────────────────────────────────────────────
    # Q1 2022 filing  (filed May 16, 2022) — baseline
    "2022-05-16": {
        "MU":    0.5117,
        "BAC":   0.2417,
        "GOOG":  0.0898,
        "META":  0.0853,
        "AAPL":  0.0469,
        "BRK-B": 0.0246,
    },
    # Q2 2022 filing  (filed Aug 15, 2022) — sold META 100%, bought GOOGL/GOOG
    "2022-08-15": {
        "MU":    0.4200,
        "BAC":   0.2300,
        "GOOG":  0.1400,
        "GOOGL": 0.0900,
        "AAPL":  0.0500,
        "BRK-B": 0.0700,
    },
    # Q3 2022 filing  (filed Nov 14, 2022) — held all positions
    "2022-11-14": {
        "MU":    0.4000,
        "BAC":   0.2200,
        "GOOG":  0.1400,
        "GOOGL": 0.1000,
        "AAPL":  0.0600,
        "BRK-B": 0.0800,
    },
    # Q4 2022 filing  (filed Feb 14, 2023) — added GOOGL +168%
    "2023-02-14": {
        "MU":    0.2500,
        "BAC":   0.1900,
        "GOOGL": 0.2400,
        "GOOG":  0.1700,
        "AAPL":  0.0600,
        "BRK-B": 0.0900,
    },
    # ── 2023 ────────────────────────────────────────────────
    # Q1 2023 filing  (filed May 15, 2023) — added EWBC (new), added BAC, MU -40.5%
    "2023-05-15": {
        "BAC":   0.2900,
        "GOOGL": 0.2300,
        "GOOG":  0.1700,
        "MU":    0.1400,
        "EWBC":  0.0800,
        "BRK-B": 0.0500,
        "AAPL":  0.0400,
    },
    # Q2 2023 filing  (filed Aug 14, 2023) — sold MU 100%, added EWBC
    "2023-08-14": {
        "BAC":   0.3000,
        "GOOGL": 0.2500,
        "GOOG":  0.1800,
        "EWBC":  0.1300,
        "BRK-B": 0.0700,
        "AAPL":  0.0700,
    },
    # Q3 2023 filing  (filed Nov 14, 2023) — no trades
    "2023-11-14": {
        "BAC":   0.3000,
        "GOOGL": 0.2500,
        "GOOG":  0.1800,
        "EWBC":  0.1300,
        "BRK-B": 0.0700,
        "AAPL":  0.0700,
    },
    # Q4 2023 filing  (filed Feb 14, 2024) — no trades
    "2024-02-14": {
        "BAC":   0.3000,
        "GOOGL": 0.2500,
        "GOOG":  0.1800,
        "EWBC":  0.1200,
        "BRK-B": 0.0800,
        "AAPL":  0.0700,
    },
    # ── 2024 ────────────────────────────────────────────────
    # Q1 2024 filing  (filed May 15, 2024) — no major changes
    "2024-05-15": {
        "BAC":   0.3000,
        "GOOGL": 0.2500,
        "GOOG":  0.1700,
        "EWBC":  0.1200,
        "BRK-B": 0.0800,
        "AAPL":  0.0800,
    },
    # Q2 2024 filing  (filed Aug 14, 2024) — added OXY (new)
    "2024-08-14": {
        "BAC":   0.2800,
        "GOOGL": 0.2200,
        "GOOG":  0.1600,
        "EWBC":  0.1100,
        "BRK-B": 0.0900,
        "OXY":   0.0700,
        "AAPL":  0.0700,
    },
    # Q3 2024 filing  (filed Nov 14, 2024) — held
    "2024-11-14": {
        "BAC":   0.2800,
        "GOOGL": 0.2200,
        "GOOG":  0.1600,
        "EWBC":  0.1100,
        "BRK-B": 0.0900,
        "OXY":   0.0700,
        "AAPL":  0.0700,
    },
    # Q4 2024 filing  (filed Feb 14, 2025) — held; AUM $2.71B
    "2025-02-14": {
        "BAC":   0.2800,
        "GOOGL": 0.2200,
        "GOOG":  0.1600,
        "EWBC":  0.1100,
        "BRK-B": 0.0900,
        "OXY":   0.0700,
        "AAPL":  0.0700,
    },
    # ── 2025 ────────────────────────────────────────────────
    # Q1 2025 filing  (filed May 15, 2025) — trimmed BAC -23.4%, new PDD
    "2025-05-15": {
        "GOOGL": 0.2400,
        "GOOG":  0.2000,
        "BAC":   0.1800,
        "PDD":   0.1500,
        "BRK-B": 0.1000,
        "EWBC":  0.0900,
        "OXY":   0.0500,
        "AAPL":  0.0400,
    },
    # Q2 2025 filing  (filed Aug 14, 2025) — trimmed BAC -24.7%, GOOG -19.5%, AAPL -65%
    "2025-08-14": {
        "GOOGL": 0.2400,
        "GOOG":  0.1600,
        "BAC":   0.1400,
        "PDD":   0.1800,
        "BRK-B": 0.1100,
        "EWBC":  0.1000,
        "OXY":   0.0500,
        "AAPL":  0.0200,
    },
    # Q3 2025 filing  (filed Nov 12, 2025) — held; AUM $3.23B (exact weights from SEC)
    "2025-11-12": {
        "GOOGL": 0.2331,
        "GOOG":  0.2155,
        "BAC":   0.1608,
        "PDD":   0.1464,
        "BRK-B": 0.1264,
        "EWBC":  0.0874,
        "OXY":   0.0169,
        "AAPL":  0.0084,
        "SOC":   0.0050,
    },
    # Q4 2025 filing  (filed Feb 18, 2026) — new CROX, sold SOC; AUM $3.57B (exact)
    "2026-02-18": {
        "GOOGL": 0.2231,
        "GOOG":  0.2155,
        "BAC":   0.1608,
        "PDD":   0.1464,
        "BRK-B": 0.1264,
        "EWBC":  0.0874,
        "OXY":   0.0169,
        "CROX":  0.0151,
        "AAPL":  0.0084,
    },
}

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def next_trading_day(date_str: str, prices_df: pd.DataFrame) -> str:
    """Return first available trading day on or after date_str."""
    d = pd.Timestamp(date_str)
    while d.strftime("%Y-%m-%d") not in prices_df.index:
        d += timedelta(days=1)
        if d > prices_df.index[-1]:
            return prices_df.index[-1]
    return d.strftime("%Y-%m-%d")

def get_price(ticker: str, date: str, prices: dict) -> float:
    """Return closing price for ticker on date (or nearest available)."""
    if ticker not in prices:
        return None
    df = prices[ticker]
    if date in df.index:
        return df.loc[date, "Close"]
    # fallback: last known price before date
    before = df[df.index <= date]
    if len(before) == 0:
        return None
    return before.iloc[-1]["Close"]


# ─────────────────────────────────────────────────────────────
# STEP 1 — COLLECT ALL TICKERS & FETCH PRICES
# ─────────────────────────────────────────────────────────────

all_tickers = set()
for snap in SNAPSHOTS.values():
    all_tickers.update(snap.keys())
all_tickers.add(BENCHMARK)

print(f"Fetching price data for: {sorted(all_tickers)}")
print("(This may take ~15 seconds…)\n")

raw = yf.download(
    list(all_tickers),
    start="2022-01-01",
    end="2026-03-11",
    auto_adjust=True,
    progress=False,
)

# Build per-ticker DataFrames
prices = {}
for ticker in all_tickers:
    try:
        if isinstance(raw.columns, pd.MultiIndex):
            df = raw["Close"][[ticker]].rename(columns={ticker: "Close"}).dropna()
        else:
            df = raw[["Close"]].dropna()
        df.index = df.index.strftime("%Y-%m-%d")
        prices[ticker] = df
    except Exception:
        print(f"  ⚠  Could not load {ticker}")

print(f"Loaded {len(prices)} tickers successfully.\n")


# ─────────────────────────────────────────────────────────────
# STEP 2 — RUN THE BACKTEST
# ─────────────────────────────────────────────────────────────

filing_dates = sorted(SNAPSHOTS.keys())

# Normalise weights to sum to 1.0
for date in filing_dates:
    snap = SNAPSHOTS[date]
    total = sum(snap.values())
    SNAPSHOTS[date] = {k: v / total for k, v in snap.items()}

records = []           # one row per rebalance event
portfolio_history = [] # daily portfolio value

portfolio_value = STARTING_CAPITAL
holdings = {}          # {ticker: shares}

for i, filing_date in enumerate(filing_dates):
    action_date = next_trading_day(filing_date, prices[BENCHMARK])
    weights = SNAPSHOTS[filing_date]

    # ── Get prices on action date ──
    current_prices = {}
    for ticker, w in weights.items():
        p = get_price(ticker, action_date, prices)
        if p is not None:
            current_prices[ticker] = p
        else:
            print(f"  ⚠  No price for {ticker} on {action_date}, skipping.")

    # ── Calculate current portfolio value before rebalance ──
    if holdings:
        pv = sum(
            shares * (get_price(t, action_date, prices) or 0)
            for t, shares in holdings.items()
        )
        portfolio_value = pv

    # ── Rebalance ──
    new_holdings = {}
    trade_log = []
    for ticker, weight in weights.items():
        if ticker not in current_prices:
            continue
        price = current_prices[ticker]
        target_value = portfolio_value * weight
        shares = target_value / price
        prev_shares = holdings.get(ticker, 0)
        new_holdings[ticker] = shares
        delta = shares - prev_shares
        trade_log.append({
            "ticker": ticker,
            "action": "BUY" if delta > 0 else ("SELL" if delta < 0 else "HOLD"),
            "delta_shares": round(delta, 4),
            "price": round(price, 2),
            "weight_%": round(weight * 100, 1),
        })

    # Tickers fully exited
    for ticker in list(holdings.keys()):
        if ticker not in weights and ticker in holdings:
            p = get_price(ticker, action_date, prices) or 0
            trade_log.append({
                "ticker": ticker,
                "action": "SELL (EXIT)",
                "delta_shares": -round(holdings[ticker], 4),
                "price": round(p, 2),
                "weight_%": 0,
            })

    holdings = new_holdings
    records.append({
        "filing_date": filing_date,
        "action_date": action_date,
        "portfolio_value": round(portfolio_value, 2),
        "n_holdings": len(new_holdings),
        "trades": trade_log,
    })

# ─────────────────────────────────────────────────────────────
# STEP 3 — DAILY PORTFOLIO VALUE (between rebalances)
# ─────────────────────────────────────────────────────────────

# Build date range
all_dates = sorted(prices[BENCHMARK].index)
start_idx = all_dates.index(records[0]["action_date"])

# Walk through days with last-known holdings
current_holdings = {}
rebalance_map = {r["action_date"]: r for r in records}

running_value = STARTING_CAPITAL
for date in all_dates[start_idx:]:
    if date in rebalance_map:
        rec = rebalance_map[date]
        # Rebuild share counts from weights + portfolio value
        snap = SNAPSHOTS[rec["filing_date"]]
        pv_before = sum(
            current_holdings.get(t, 0) * (get_price(t, date, prices) or 0)
            for t in current_holdings
        ) or STARTING_CAPITAL
        current_holdings = {}
        for ticker, weight in snap.items():
            p = get_price(ticker, date, prices)
            if p:
                current_holdings[ticker] = (pv_before * weight) / p

    day_value = sum(
        shares * (get_price(t, date, prices) or 0)
        for t, shares in current_holdings.items()
    )
    portfolio_history.append({"date": date, "portfolio": day_value})

port_df = pd.DataFrame(portfolio_history).set_index("date")

# ─────────────────────────────────────────────────────────────
# STEP 4 — BENCHMARK (SPY) — same starting capital
# ─────────────────────────────────────────────────────────────

spy_df = prices[BENCHMARK].loc[port_df.index[0]:]
spy_start = spy_df.iloc[0]["Close"]
port_start = port_df.iloc[0]["portfolio"]

spy_normalized = (spy_df["Close"] / spy_start) * port_start
port_df["benchmark"] = spy_normalized.reindex(port_df.index)

# ─────────────────────────────────────────────────────────────
# STEP 5 — PRINT RESULTS
# ─────────────────────────────────────────────────────────────

print("=" * 70)
print("  HIMALAYA CAPITAL — 13F COPY-TRADE BACKTEST RESULTS")
print("=" * 70)

for rec in records:
    print(f"\n{'─'*60}")
    print(f"  Filing: {rec['filing_date']}  |  Acted: {rec['action_date']}")
    print(f"  Portfolio value on rebalance: ${rec['portfolio_value']:,.0f}")
    print(f"  Holdings: {rec['n_holdings']}")
    print(f"  {'Ticker':<8} {'Action':<14} {'Δ Shares':>12}  {'Price':>8}  {'Weight%':>7}")
    for t in rec["trades"]:
        print(f"  {t['ticker']:<8} {t['action']:<14} {t['delta_shares']:>12.2f}  "
              f"${t['price']:>7.2f}  {t['weight_%']:>6.1f}%")

final_port  = port_df["portfolio"].iloc[-1]
final_bench = port_df["benchmark"].dropna().iloc[-1]

port_return  = (final_port  / STARTING_CAPITAL - 1) * 100
bench_return = (final_bench / STARTING_CAPITAL - 1) * 100
alpha        = port_return - bench_return

print(f"\n{'='*70}")
print(f"  SUMMARY  ({port_df.index[0]} → {port_df.index[-1]})")
print(f"{'='*70}")
print(f"  Starting capital          : ${STARTING_CAPITAL:>12,.0f}")
print(f"  Final portfolio value     : ${final_port:>12,.0f}")
print(f"  Final benchmark (SPY)     : ${final_bench:>12,.0f}")
print(f"  Portfolio total return    : {port_return:>+.1f}%")
print(f"  SPY total return          : {bench_return:>+.1f}%")
print(f"  Alpha vs SPY              : {alpha:>+.1f}%")

# Max drawdown
rolling_max = port_df["portfolio"].cummax()
drawdown = (port_df["portfolio"] - rolling_max) / rolling_max * 100
max_dd = drawdown.min()
print(f"  Max drawdown              : {max_dd:.1f}%")
print(f"{'='*70}\n")

# ─────────────────────────────────────────────────────────────
# STEP 6 — PER-TRADE P&L TABLE
# ─────────────────────────────────────────────────────────────

print("  KEY POSITION TIMELINE  (entry/exit prices vs returns)")
print(f"  {'Ticker':<7} {'Entry Date':<13} {'Entry $':>8}  {'Exit Date':<13} {'Exit $':>8}  {'Return':>8}")

# Track entry prices per ticker
entry_info = {}  # ticker -> (date, price)
position_results = []

for rec in records:
    snap = SNAPSHOTS[rec["filing_date"]]
    date = rec["action_date"]
    # Check for exits
    prev_snap = SNAPSHOTS[filing_dates[max(0, filing_dates.index(rec["filing_date"]) - 1)]]
    for ticker in prev_snap:
        if ticker not in snap:  # exited
            if ticker in entry_info:
                ep, ep_price = entry_info[ticker]
                exit_price = get_price(ticker, date, prices) or ep_price
                ret = (exit_price / ep_price - 1) * 100
                position_results.append((ticker, ep, ep_price, date, exit_price, ret))
                del entry_info[ticker]
    # New entries
    for ticker in snap:
        if ticker not in entry_info:
            p = get_price(ticker, date, prices)
            if p:
                entry_info[ticker] = (date, p)

for ticker, ed, ep, xd, xp, ret in sorted(position_results, key=lambda x: x[0]):
    flag = "✓" if ret > 0 else "✗"
    print(f"  {ticker:<7} {ed:<13} ${ep:>7.2f}  {xd:<13} ${xp:>7.2f}  {ret:>+7.1f}% {flag}")

# Still open positions
print(f"\n  OPEN POSITIONS (as of last filing):")
last_snap = SNAPSHOTS[filing_dates[-1]]
last_date = records[-1]["action_date"]
for ticker, weight in last_snap.items():
    if ticker in entry_info:
        ed, ep = entry_info[ticker]
        cp = get_price(ticker, last_date, prices) or ep
        ret = (cp / ep - 1) * 100
        flag = "✓" if ret > 0 else "✗"
        print(f"  {ticker:<7} entered {ed}  @ ${ep:>7.2f} → ${cp:>7.2f}  {ret:>+7.1f}% {flag}  ({weight*100:.1f}%)")

print()

# ─────────────────────────────────────────────────────────────
# STEP 7 — PLOT
# ─────────────────────────────────────────────────────────────

fig, axes = plt.subplots(3, 1, figsize=(14, 12))
fig.suptitle("Himalaya Capital (Li Lu) — 13F Copy-Trade Backtest\n"
             f"${STARTING_CAPITAL:,.0f} Starting Capital  |  Q1 2022 – Q4 2025",
             fontsize=14, fontweight="bold")

# ── Panel 1: Portfolio vs SPY ──
ax1 = axes[0]
ax1.plot(pd.to_datetime(port_df.index), port_df["portfolio"],
         color="#2196F3", linewidth=2, label=f"Himalaya Copy ({port_return:+.1f}%)")
ax1.plot(pd.to_datetime(port_df.index), port_df["benchmark"],
         color="#FF9800", linewidth=2, linestyle="--", label=f"SPY ({bench_return:+.1f}%)")
for rec in records:
    ax1.axvline(pd.to_datetime(rec["action_date"]), color="gray",
                alpha=0.3, linewidth=1, linestyle=":")
ax1.set_ylabel("Portfolio Value ($)")
ax1.set_title("Portfolio Value vs SPY Benchmark")
ax1.legend()
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax1.grid(True, alpha=0.3)

# ── Panel 2: Drawdown ──
ax2 = axes[1]
ax2.fill_between(pd.to_datetime(port_df.index), drawdown, 0,
                 color="#F44336", alpha=0.6, label="Drawdown")
ax2.set_ylabel("Drawdown (%)")
ax2.set_title("Portfolio Drawdown")
ax2.legend()
ax2.grid(True, alpha=0.3)
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))

# ── Panel 3: Portfolio composition over time ──
ax3 = axes[2]
all_t = sorted({t for snap in SNAPSHOTS.values() for t in snap})
colors = plt.cm.tab20(np.linspace(0, 1, len(all_t)))
color_map = dict(zip(all_t, colors))

dates_plot = [pd.to_datetime(r["action_date"]) for r in records]
bottom = np.zeros(len(records))

for ticker in all_t:
    weights_series = []
    for rec in records:
        snap = SNAPSHOTS[rec["filing_date"]]
        weights_series.append(snap.get(ticker, 0) * 100)
    weights_arr = np.array(weights_series)
    if weights_arr.sum() > 0:
        ax3.bar(dates_plot, weights_arr, bottom=bottom,
                color=color_map[ticker], label=ticker, width=45, alpha=0.85)
        bottom += weights_arr

ax3.set_ylabel("Portfolio Weight (%)")
ax3.set_title("Portfolio Composition at Each 13F Rebalance")
ax3.legend(loc="upper right", ncol=4, fontsize=7)
ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
ax3.grid(True, alpha=0.3, axis="y")

for ax in axes:
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=8)

plt.tight_layout()
output_path = "/Users/huhao/Documents/Claude/himalaya_backtest.png"
plt.savefig(output_path, dpi=150, bbox_inches="tight")
print(f"Chart saved → {output_path}")
plt.show()
