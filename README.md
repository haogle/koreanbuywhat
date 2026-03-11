# 📊 Investment Research Dashboard

An interactive investment research dashboard built with Streamlit.

## Features

| Tab | Description |
|-----|-------------|
| 🏔️ **13F Fund Tracker** | Copy-trade simulation following S-tier fund 13F filings (Himalaya, Pershing Square, Berkshire, Pabrai) |
| 🎯 **SeekingAlpha Picks** | Backtest SeekingAlpha's annual top-10 picks (2022–2026 YTD) |
| 🔍 **Stock Research** | Price charts, candlestick, key stats for any ticker |
| 🧪 **Custom Backtest** | Enter your own tickers + weights, pick any date range |
| 📁 **Upload Data** | Upload any Excel/CSV with a Ticker column and auto-backtest |

## Quick Start

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

Open **http://localhost:8501** in your browser.

## Data Sources

- Price data: [Yahoo Finance](https://finance.yahoo.com) via `yfinance`
- 13F filings: SEC EDGAR, HedgeFollow, ValuSider, 13f.info

## Backtests Included

### 13F Copy-Trade Results (May 2022 – Mar 2026, $100K start)

| Fund | Return | Alpha vs SPY |
|------|--------|-------------|
| Pershing Square (Ackman) | +108.7% | +30.3% |
| Himalaya Capital (Li Lu) | +104.4% | +26.0% |
| SPY Benchmark | +78.4% | — |
| Berkshire (Buffett) | +54.5% | -23.9% |
| Pabrai Funds | -58.9% | -137.3%* |

*Pabrai's real alpha comes from India/Turkey positions not visible in US 13F filings.

### SeekingAlpha Top-10 Picks (2022–2026 YTD, $100K start)

| | Portfolio | SPY |
|--|-----------|-----|
| Cumulative | ~$1,007,790 (+908%) | ~$151,436 (+51%) |

## Disclaimer

For research and educational purposes only. Not financial advice.
