"""
Vercel Serverless Function — 韩国投资者海外股票 TOP5 报告
GET /                          → HTML 页面（带日期选择器）
GET /?start=&end=&market=      → JSON 数据
"""

import json
import sys
import os
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import BaseHTTPRequestHandler
from main import fetch_week
from stock_names import format_display

MARKETS = [
    ("US", "美股", "United States"),
    ("HK", "港股", "Hong Kong"),
    ("CN", "A股", "Mainland China"),
    ("JP", "日股", "Japan"),
    ("VN", "越股", "Vietnam"),
]


def fetch_one(country, label_cn, label_en, start, end):
    df = fetch_week(country, start, end)
    if df.empty:
        return {"market": label_cn, "market_en": label_en, "code": country, "data": None}

    def make_row(r):
        ticker, cn_name = format_display(
            r["KOR_SECN_NM"],
            isin=r.get("ISIN", ""),
            is_hk=(country == "HK"),
        )
        return {
            "name": r["KOR_SECN_NM"],
            "ticker": ticker,
            "cn_name": cn_name,
            "buy": round(r["buy"]),
            "sell": round(r["sell"]),
            "net": round(r["net"]),
        }

    top_buy = df.sort_values("net", ascending=False).head(5).apply(make_row, axis=1).tolist()
    top_sell = df.sort_values("net", ascending=True).head(5).apply(make_row, axis=1).tolist()

    return {
        "market": label_cn,
        "market_en": label_en,
        "code": country,
        "weekly_net": round(df["net"].sum()),
        "top_buy": top_buy,
        "top_sell": top_sell,
    }


def generate_report(start, end, market=None):
    start_fmt = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_fmt = f"{end[:4]}-{end[4:6]}-{end[6:]}"

    markets = MARKETS
    if market:
        markets = [m for m in markets if m[0] == market.upper()]

    with ThreadPoolExecutor(max_workers=max(1, len(markets))) as pool:
        futures = [pool.submit(fetch_one, c, lc, le, start, end) for c, lc, le in markets]
        results = [f.result() for f in futures]

    return {
        "period": f"{start_fmt} ~ {end_fmt}",
        "source": "Korea Securities Depository · SEIBro",
        "markets": results,
    }


PAGE_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>韩国人买什么 · 서학개미 레이더</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Young+Serif&family=Archivo:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Geist+Mono:wght@400;500&family=Noto+Serif+SC:wght@500;600&family=Noto+Sans+SC:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    /* Editorial palette — warm paper & ink */
    --paper:     oklch(97.2% 0.008 85);
    --paper-dim: oklch(94% 0.008 85);
    --ink:       oklch(19% 0.012 85);
    --ink-soft:  oklch(42% 0.01 85);
    --ink-faint: oklch(63% 0.006 85);
    --rule:      oklch(86% 0.006 85);
    --accent:    oklch(48% 0.19 25);
    --gain:      oklch(44% 0.11 150);
    --loss:      oklch(48% 0.19 25);

    --serif-en: 'Young Serif', 'Noto Serif SC', ui-serif, Georgia, serif;
    --serif-cn: 'Noto Serif SC', 'Young Serif', ui-serif, serif;
    --sans:     'Archivo', 'Noto Sans SC', -apple-system, system-ui, sans-serif;
    --mono:     'Geist Mono', 'SF Mono', 'Menlo', ui-monospace, monospace;

    --s-1: 4px;  --s-2: 8px;   --s-3: 12px;  --s-4: 16px;
    --s-5: 24px; --s-6: 32px;  --s-7: 48px;  --s-8: 64px;  --s-9: 96px;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  html { background: var(--paper); }
  body {
    font-family: var(--sans);
    color: var(--ink);
    font-size: 15px;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
    font-feature-settings: "ss01", "cv11";
  }
  ::selection { background: var(--ink); color: var(--paper); }

  .page {
    max-width: 880px;
    margin: 0 auto;
    padding: var(--s-7) var(--s-5) var(--s-8);
  }

  /* ── Masthead ── */
  .masthead {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: var(--s-4);
    align-items: baseline;
    padding-bottom: var(--s-3);
    border-bottom: 2px solid var(--ink);
  }
  .kicker {
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-soft);
  }
  .masthead-right {
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.14em;
    color: var(--ink-soft);
    text-align: right;
  }
  .masthead-right b { color: var(--ink); font-weight: 500; }

  /* ── Hero ── */
  .hero {
    padding: var(--s-7) 0 var(--s-5);
    display: grid;
    grid-template-columns: 1fr auto;
    gap: var(--s-7);
    align-items: start;
  }
  .hero-text { min-width: 0; }
  .hero-aside { grid-row: span 3; align-self: start; }

  /* ── Subscribe / QR panel ── */
  .subscribe {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    gap: var(--s-3);
    padding: var(--s-4);
    background: var(--paper-dim);
    border: 1px solid var(--rule);
    max-width: 200px;
    position: relative;
  }
  .subscribe::before {
    content: "Subscribe · 订阅";
    position: absolute;
    top: -8px;
    left: var(--s-3);
    background: var(--paper);
    padding: 0 var(--s-2);
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }
  .subscribe img {
    display: block;
    width: 168px;
    height: 168px;
    image-rendering: -webkit-optimize-contrast;
    image-rendering: crisp-edges;
  }
  .subscribe-caption {
    font-family: var(--serif-cn);
    font-weight: 500;
    font-size: 14px;
    color: var(--ink);
    text-align: center;
    line-height: 1.4;
    padding-top: var(--s-1);
    border-top: 1px solid var(--rule);
    width: 100%;
  }
  .subscribe-caption em {
    display: block;
    font-family: var(--serif-en);
    font-style: italic;
    font-weight: 400;
    font-size: 11px;
    color: var(--ink-faint);
    margin-top: 2px;
  }

  h1.title {
    font-family: var(--serif-cn);
    font-weight: 600;
    font-size: clamp(54px, 11vw, 108px);
    line-height: 0.92;
    letter-spacing: -0.02em;
    color: var(--ink);
  }
  h1.title .en {
    display: block;
    font-family: var(--serif-en);
    font-weight: 400;
    font-size: clamp(18px, 2.4vw, 26px);
    letter-spacing: 0;
    color: var(--ink-soft);
    margin-top: var(--s-4);
    font-style: italic;
  }
  .deck {
    font-family: var(--serif-en);
    font-style: italic;
    font-size: clamp(16px, 2vw, 20px);
    line-height: 1.5;
    color: var(--ink-soft);
    max-width: 52ch;
    margin-top: var(--s-5);
  }
  .byline {
    margin-top: var(--s-5);
    padding-top: var(--s-3);
    border-top: 1px solid var(--rule);
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-faint);
    display: flex;
    gap: var(--s-5);
    flex-wrap: wrap;
  }
  .byline b { color: var(--ink-soft); font-weight: 500; }

  /* ── Controls ── */
  .controls {
    margin-top: var(--s-6);
    padding: var(--s-5) 0;
    border-top: 1px solid var(--rule);
    border-bottom: 1px solid var(--rule);
    display: flex;
    gap: var(--s-5);
    align-items: flex-end;
    flex-wrap: wrap;
  }
  .field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .field label {
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }
  .field input, .field select {
    font-family: var(--mono);
    font-size: 13.5px;
    color: var(--ink);
    background: transparent;
    border: 0;
    border-bottom: 1px solid var(--ink);
    padding: 5px 0;
    outline: none;
    min-width: 140px;
    appearance: none;
    -webkit-appearance: none;
  }
  .field input[type="date"] { min-width: 150px; font-variant-numeric: tabular-nums; }
  .field input:focus, .field select:focus { border-bottom-color: var(--accent); }
  .field select {
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path d='M0 0l5 6 5-6z' fill='%23000'/></svg>");
    background-repeat: no-repeat;
    background-position: right 4px center;
    padding-right: 18px;
  }

  .go-btn {
    font-family: var(--sans);
    font-size: 12.5px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--paper);
    background: var(--ink);
    border: 0;
    padding: 10px 22px;
    cursor: pointer;
    transition: background 0.2s;
  }
  .go-btn:hover { background: var(--accent); }
  .go-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  .presets {
    margin-left: auto;
    display: flex;
    gap: var(--s-4);
    flex-wrap: wrap;
    align-items: flex-end;
    padding-bottom: 5px;
  }
  .preset {
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-soft);
    background: transparent;
    border: 0;
    padding: 4px 0;
    cursor: pointer;
    border-bottom: 1px solid transparent;
    transition: color 0.15s, border-color 0.15s;
  }
  .preset:hover { color: var(--ink); }
  .preset.on { color: var(--accent); border-bottom-color: var(--accent); }

  /* ── Market block ── */
  .results { margin-top: var(--s-6); }
  .period-stamp {
    font-family: var(--mono);
    font-size: 10.5px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin-bottom: var(--s-7);
  }
  .period-stamp b { color: var(--ink); font-weight: 500; }

  .market { margin-top: var(--s-8); }
  .market:first-of-type { margin-top: 0; }

  .market-head {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: baseline;
    gap: var(--s-4);
    padding-bottom: var(--s-3);
    border-bottom: 2px solid var(--ink);
  }
  .market-flag {
    font-size: 24px;
    line-height: 1;
  }
  .market-name {
    font-family: var(--serif-cn);
    font-weight: 600;
    font-size: 26px;
    letter-spacing: -0.01em;
  }
  .market-name .en {
    font-family: var(--serif-en);
    font-style: italic;
    font-weight: 400;
    font-size: 14px;
    letter-spacing: 0;
    color: var(--ink-soft);
    margin-left: var(--s-2);
  }
  .market-net {
    font-family: var(--mono);
    font-size: 15px;
    font-weight: 500;
    letter-spacing: -0.02em;
  }
  .market-net.gain { color: var(--gain); }
  .market-net.loss { color: var(--loss); }
  .market-net .lbl {
    font-family: var(--mono);
    font-size: 9.5px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin-right: var(--s-2);
    font-weight: 400;
  }

  /* ── Section header ── */
  .section-label {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: var(--s-6) 0 var(--s-3);
  }
  .section-label h3 {
    font-family: var(--serif-en);
    font-style: italic;
    font-weight: 400;
    font-size: 20px;
    color: var(--ink);
  }
  .section-label h3 .zh {
    font-family: var(--serif-cn);
    font-style: normal;
    font-weight: 500;
    margin-right: var(--s-2);
  }
  .section-label .count {
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }

  /* ── Row (no cards, no stripes, no shadows) ── */
  .row {
    display: grid;
    grid-template-columns: 32px 1fr auto;
    gap: var(--s-4);
    padding: var(--s-4) 0;
    border-bottom: 1px solid var(--rule);
    align-items: baseline;
  }
  .row:last-child { border-bottom: 0; }
  .row-num {
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.1em;
    color: var(--ink-faint);
    padding-top: 3px;
    font-variant-numeric: tabular-nums;
  }
  .row-main { min-width: 0; }
  .row-head {
    display: flex;
    align-items: baseline;
    gap: var(--s-3);
    flex-wrap: wrap;
  }
  .row-ticker {
    font-family: var(--sans);
    font-weight: 700;
    font-size: 19px;
    letter-spacing: -0.01em;
    color: var(--ink);
  }
  .row-cn {
    font-family: var(--sans);
    font-weight: 500;
    font-size: 14px;
    color: var(--ink-soft);
  }
  .row-name {
    font-family: var(--sans);
    font-weight: 400;
    font-size: 11.5px;
    color: var(--ink-faint);
    margin-top: 4px;
    letter-spacing: 0.01em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 48ch;
  }

  .row-right { text-align: right; }
  .row-net {
    font-family: var(--mono);
    font-weight: 500;
    font-size: 17px;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
  }
  .row-net.gain { color: var(--gain); }
  .row-net.loss { color: var(--loss); }
  .row-detail {
    font-family: var(--mono);
    font-size: 10.5px;
    color: var(--ink-faint);
    margin-top: 4px;
    letter-spacing: 0.02em;
    font-variant-numeric: tabular-nums;
  }

  /* ── States ── */
  .loading {
    text-align: center;
    padding: var(--s-9) var(--s-4);
    color: var(--ink-soft);
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.26em;
    text-transform: uppercase;
  }
  .loading::after {
    content: "";
    display: inline-block;
    animation: dots 1.3s infinite steps(4, jump-none);
    margin-left: 6px;
    width: 24px;
    text-align: left;
  }
  @keyframes dots {
    0%    { content: ""; }
    25%   { content: "·"; }
    50%   { content: "· ·"; }
    75%   { content: "· · ·"; }
    100%  { content: "· · · ·"; }
  }
  .empty {
    padding: var(--s-8) var(--s-4);
    text-align: center;
    font-family: var(--serif-en);
    font-style: italic;
    color: var(--ink-soft);
    font-size: 18px;
  }
  .no-data {
    padding: var(--s-5) 0;
    font-family: var(--serif-en);
    font-style: italic;
    color: var(--ink-faint);
    font-size: 15px;
  }

  /* ── Footer ── */
  .colophon {
    margin-top: var(--s-9);
    padding-top: var(--s-4);
    border-top: 1px solid var(--rule);
    display: grid;
    grid-template-columns: 1fr auto;
    gap: var(--s-4);
    font-family: var(--mono);
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-faint);
  }

  @media (max-width: 820px) {
    .hero {
      grid-template-columns: 1fr;
      gap: var(--s-6);
    }
    .hero-aside { grid-row: auto; justify-self: start; }
  }
  @media (max-width: 640px) {
    .page { padding: var(--s-5) var(--s-4) var(--s-7); }
    .masthead-right { display: none; }
    .controls { flex-direction: column; align-items: stretch; gap: var(--s-4); }
    .presets { margin-left: 0; padding-bottom: 0; gap: var(--s-3); }
    .field input, .field select { min-width: 0; width: 100%; }
    .row { grid-template-columns: 28px 1fr auto; gap: var(--s-3); }
    .row-ticker { font-size: 17px; }
    .row-name { display: none; }
    .market-name .en { display: none; }
    .subscribe img { width: 144px; height: 144px; }
  }
</style>
</head>
<body>
<div class="page">

  <header class="masthead">
    <div class="kicker">서학개미 레이더 · Seohak Gaemi Radar</div>
    <div class="masthead-right">Vol. Ⅰ · <b id="today">—</b></div>
  </header>

  <section class="hero">
    <div class="hero-text">
      <h1 class="title">
        韩国人买什么
        <span class="en">What Korea's retail investors are really buying</span>
      </h1>
      <p class="deck">Settlement data straight from Korea Securities Depository, read against five foreign markets — the unglamorous record of where South Korean individual money actually flows each week.</p>
      <div class="byline">
        <span>Markets · <b>US · HK · CN · JP · VN</b></span>
        <span>Source · <b>KSD SEIBro</b></span>
        <span>Refreshed each session</span>
      </div>
    </div>
    <aside class="hero-aside">
      <div class="subscribe">
        <img src="/qrcode.png" alt="大佬持仓雷达 WeChat QR"/>
        <div class="subscribe-caption">
          欢迎关注 · 大佬持仓雷达
          <em>Scan to follow on WeChat</em>
        </div>
      </div>
    </aside>
  </section>

  <div class="controls">
    <div class="field">
      <label>From</label>
      <input type="date" id="sd"/>
    </div>
    <div class="field">
      <label>Through</label>
      <input type="date" id="ed"/>
    </div>
    <div class="field">
      <label>Market</label>
      <select id="mk">
        <option value="">All five</option>
        <option value="US">🇺🇸 United States</option>
        <option value="HK">🇭🇰 Hong Kong</option>
        <option value="CN">🇨🇳 China A</option>
        <option value="JP">🇯🇵 Japan</option>
        <option value="VN">🇻🇳 Vietnam</option>
      </select>
    </div>
    <button class="go-btn" id="lb" onclick="go()">Read</button>
    <div class="presets" id="ps"></div>
  </div>

  <section class="results" id="ct">
    <div class="empty">Choose a period to read the week's ledger.</div>
  </section>

  <footer class="colophon">
    <span>Korea Securities Depository · 한국예탁결제원</span>
    <span>Not investment advice</span>
  </footer>

</div>

<script>
  // ── Flag map ──
  var FLAGS = {
    US: '\u{1F1FA}\u{1F1F8}', HK: '\u{1F1ED}\u{1F1F0}',
    CN: '\u{1F1E8}\u{1F1F3}', JP: '\u{1F1EF}\u{1F1F5}',
    VN: '\u{1F1FB}\u{1F1F3}'
  };

  // ── Date helpers ──
  function D(d) { return d.toISOString().slice(0,10); }

  // Calendar-week range, Mon–Fri. weeksAgo=0 → current calendar week.
  function weekRange(weeksAgo) {
    var t = new Date();
    var day = t.getDay();
    var daysToMon = day === 0 ? 6 : day - 1;
    var mon = new Date(t);
    mon.setDate(t.getDate() - daysToMon - 7 * weeksAgo);
    var fri = new Date(mon);
    fri.setDate(mon.getDate() + 4);
    return { s: mon, e: fri };
  }

  // ── Issue date in masthead ──
  (function initToday() {
    var t = new Date();
    var mm = String(t.getMonth()+1).padStart(2,'0');
    var dd = String(t.getDate()).padStart(2,'0');
    document.getElementById('today').textContent = t.getFullYear() + '.' + mm + '.' + dd;
  })();

  // ── Presets ──
  (function initPresets() {
    var ps = document.getElementById('ps');
    var labels = [
      { zh: 'This Week', key: 0 },
      { zh: 'Last Week', key: 1 },
      { zh: '2W Ago',    key: 2 },
      { zh: '3W Ago',    key: 3 }
    ];
    labels.forEach(function(item, i) {
      var r = weekRange(item.key);
      var b = document.createElement('button');
      b.className = 'preset';
      b.textContent = item.zh;
      b.dataset.s = D(r.s);
      b.dataset.e = D(r.e);
      b.onclick = (function(b){ return function(){
        document.getElementById('sd').value = b.dataset.s;
        document.getElementById('ed').value = b.dataset.e;
        document.querySelectorAll('.preset').forEach(function(p){ p.classList.remove('on'); });
        b.classList.add('on');
        go();
      }})(b);
      ps.appendChild(b);
      // Default: last week
      if (i === 1) {
        document.getElementById('sd').value = D(r.s);
        document.getElementById('ed').value = D(r.e);
        b.classList.add('on');
      }
    });
  })();

  // ── Formatters ──
  function usd(v) {
    var a = Math.abs(v);
    if (a >= 1e9)  return '$' + (a/1e9).toFixed(2) + 'B';
    if (a >= 1e6)  return '$' + (a/1e6).toFixed(1) + 'M';
    if (a >= 1e3)  return '$' + (a/1e3).toFixed(0) + 'K';
    return '$' + a.toFixed(0);
  }
  function signed(v) { return (v >= 0 ? '+' : '−') + usd(v); }
  function esc(s) { return String(s||'').replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }

  // ── Render ──
  function renderRows(items, isBuy) {
    if (!items || !items.length) return '<div class="no-data">No material activity recorded.</div>';
    return items.map(function(it, i) {
      var net  = isBuy ? it.net : -it.net;
      var cls  = isBuy ? 'gain' : 'loss';
      var cn   = it.cn_name ? '<span class="row-cn">' + esc(it.cn_name) + '</span>' : '';
      return '<div class="row">'
        + '<div class="row-num">' + String(i+1).padStart(2,'0') + '</div>'
        + '<div class="row-main">'
          + '<div class="row-head"><span class="row-ticker">' + esc(it.ticker) + '</span>' + cn + '</div>'
          + '<div class="row-name">' + esc(it.name) + '</div>'
        + '</div>'
        + '<div class="row-right">'
          + '<div class="row-net ' + cls + '">' + signed(net) + '</div>'
          + '<div class="row-detail">BUY ' + usd(it.buy) + ' · SELL ' + usd(it.sell) + '</div>'
        + '</div>'
      + '</div>';
    }).join('');
  }

  function renderMarket(m) {
    var fl = FLAGS[m.code] || '';
    if (!m.top_buy) {
      return '<section class="market">'
        + '<div class="market-head">'
          + '<span class="market-flag">' + fl + '</span>'
          + '<h2 class="market-name">' + esc(m.market) + ' <span class="en">' + esc(m.market_en||'') + '</span></h2>'
          + '<span class="market-net"><span class="lbl">Net</span>—</span>'
        + '</div>'
        + '<div class="no-data">No settlement data recorded for this period.</div>'
      + '</section>';
    }
    var netCls = m.weekly_net >= 0 ? 'gain' : 'loss';
    return '<section class="market">'
      + '<div class="market-head">'
        + '<span class="market-flag">' + fl + '</span>'
        + '<h2 class="market-name">' + esc(m.market) + ' <span class="en">' + esc(m.market_en||'') + '</span></h2>'
        + '<span class="market-net ' + netCls + '"><span class="lbl">Week net</span>' + signed(m.weekly_net) + '</span>'
      + '</div>'
      + '<div class="section-label">'
        + '<h3><span class="zh">净买入</span><em>Gaining favor</em></h3>'
        + '<span class="count">Top 5</span>'
      + '</div>'
      + renderRows(m.top_buy, true)
      + '<div class="section-label">'
        + '<h3><span class="zh">净卖出</span><em>Falling out</em></h3>'
        + '<span class="count">Top 5</span>'
      + '</div>'
      + renderRows(m.top_sell, false)
    + '</section>';
  }

  // ── Fetch ──
  async function go() {
    var sv = document.getElementById('sd').value;
    var ev = document.getElementById('ed').value;
    if (!sv || !ev) return;
    var s = sv.replace(/-/g,'');
    var e = ev.replace(/-/g,'');
    var mk = document.getElementById('mk').value;
    var ct = document.getElementById('ct');
    var btn = document.getElementById('lb');

    ct.innerHTML = '<div class="loading">Reading from KSD</div>';
    btn.disabled = true;
    var originalLabel = btn.textContent;
    btn.textContent = '…';

    try {
      var url = '/api?start=' + s + '&end=' + e + (mk ? '&market=' + mk : '');
      var r = await fetch(url);
      var d = await r.json();
      if (!d.markets || d.markets.length === 0) {
        ct.innerHTML = '<div class="empty">Nothing on file for this week.</div>';
      } else {
        ct.innerHTML = '<div class="period-stamp">Settlement <b>' + d.period + '</b> · Source <b>' + d.source + '</b></div>'
          + d.markets.map(renderMarket).join('');
      }
    } catch (ex) {
      ct.innerHTML = '<div class="empty" style="color:var(--accent)">Couldn\u2019t load: ' + ex.message + '</div>';
    } finally {
      btn.disabled = false;
      btn.textContent = originalLabel;
    }
  }

  // Auto-load last week on first paint
  go();
</script>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        start = params.get("start", [None])[0]
        end = params.get("end", [None])[0]

        if start and end:
            market = params.get("market", [None])[0]
            try:
                data = generate_report(start, end, market)
                body = json.dumps(data, ensure_ascii=False, indent=2).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "s-maxage=3600, stale-while-revalidate=600")
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                err = json.dumps({"error": str(e)}, ensure_ascii=False).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(err)
        else:
            body = PAGE_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "s-maxage=86400, stale-while-revalidate=3600")
            self.end_headers()
            self.wfile.write(body)
