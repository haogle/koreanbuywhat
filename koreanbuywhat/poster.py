"""
poster.py -- 大佬持仓雷达 · 周度海报生成器
------------------------------------------
严格按 DESIGN_SPEC.md 实现：720×1080 treemap 竖版，方块大小 = 金额大小。

Render pipeline:
  notify_feishu.py
    → build_poster_html(...)
    → render_html_to_image(html, path)   (Playwright, 720×1080 @2x)
    → PNG (1440×2160)
"""

import html as html_mod
from datetime import datetime
from pathlib import Path


# ── Format helpers ──────────────────────────────────────────────────────────

def fmt_m_abs(usd: float) -> str:
    """以 $M 显示（绝对值）。≥1000M 显示 $xB"""
    v = abs(usd) / 1e6
    if v >= 1000:
        return f"${v / 1000:.2f}B"
    return f"${v:.1f}M"


def fmt_signed(usd: float) -> str:
    """+$105.1M / −$123.4M （U+2212 负号，视觉平衡）"""
    if usd > 0:
        return f"+{fmt_m_abs(usd)}"
    if usd < 0:
        return f"\u2212{fmt_m_abs(usd)}"
    return "$0.0M"


def tile_color(sign: int, flex: float) -> str:
    """alpha 随 flex 加深: 0.55 + flex*0.85, clamped to 0.98"""
    alpha = min(0.98, 0.55 + flex * 0.85)
    if sign > 0:
        return f"rgba(13, 136, 60, {alpha:.3f})"
    return f"rgba(202, 30, 30, {alpha:.3f})"


def split_tiles(items, sign: int):
    """按 flex (金额占比) 分流：big(≥0.12) 进 treemap，tail(<0.12) 走整行"""
    vals = [abs(x.get("net", 0)) for x in items]
    total = sum(vals) or 1
    tiles = []
    for x in items:
        flex = abs(x.get("net", 0)) / total
        tiles.append({**x, "sign": sign, "flex": flex})
    big = [t for t in tiles if t["flex"] >= 0.12]
    tail = [t for t in tiles if t["flex"] < 0.12]
    # 重新归一化 big 让其填满 100%
    big_total = sum(t["flex"] for t in big) or 1
    for t in big:
        t["_flex_norm"] = t["flex"] / big_total
    return big, tail


def iso_week_of(date_str: str) -> int:
    """从 'YYYY-MM-DD' 取 ISO 周号"""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.isocalendar().week
    except Exception:
        return 0


# ── Playwright rendering (720×1080 canvas) ──────────────────────────────────

def render_html_to_image(html_content: str, output_path) -> None:
    """Playwright 渲染 → PNG. 720×1080 @ 2x = 1440×2160"""
    from playwright.sync_api import sync_playwright

    # 注入本地 NotoSansSC 字体作为 Chinese fallback（Helvetica 不含中文）
    font_path = Path(__file__).parent / "fonts" / "NotoSansSC-VariableFont_wght.ttf"
    if font_path.exists():
        font_url = font_path.resolve().as_uri()
        font_css = (
            f"<style>@font-face{{font-family:'NotoSansSC';"
            f"src:url('{font_url}') format('truetype');"
            f"font-weight:100 900;}}</style>"
        )
        html_content = html_content.replace("</head>", f"{font_css}</head>", 1)

    output_path = Path(output_path)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parent / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 720, "height": 1080},
            device_scale_factor=2,
        )
        page.set_content(html_content, wait_until="networkidle")
        page.wait_for_timeout(800)
        page.screenshot(
            path=str(output_path),
            clip={"x": 0, "y": 0, "width": 720, "height": 1080},
            type="png",
        )
        browser.close()


# ── HTML fragment builders ──────────────────────────────────────────────────

def _esc(s) -> str:
    return html_mod.escape(str(s or ""))


def _display_name(tile: dict, max_len: int = 20) -> str:
    """
    选择 tile 下方要显示的副标题，保证 **永远不会** 与 ticker 重复：
      1) 中文名存在 → 用中文名
      2) SEIBro 英文名存在且不是 ticker 的复读 → 用英文名
      3) 其它 → "未识别" 占位
    """
    cn = (tile.get("cn_name") or "").strip()
    if cn:
        return cn[:max_len]

    raw = (tile.get("name") or "").strip()
    if not raw:
        return "未识别"

    ticker = (tile.get("ticker") or "").strip()
    raw_norm = raw.upper().replace(".HK", "").lstrip("0")
    ticker_norm = ticker.upper().replace(".HK", "").lstrip("0")
    # raw 是纯数字（SEIBro 偶尔返回 "00068" 这种），或与 ticker 同源 → 视为重复
    if raw.isdigit() or raw_norm == ticker_norm:
        return "未识别"
    return raw[:max_len]


def _tile_html(tile: dict) -> str:
    """Treemap tile. Hero 阈值 flex > 0.35 触发更大字号。"""
    ticker = _esc(tile.get("ticker", ""))
    name = _esc(_display_name(tile))
    amount = fmt_signed(tile["net"])
    bg = tile_color(tile["sign"], tile["flex"])
    flex_norm = tile.get("_flex_norm", tile["flex"])
    is_hero = tile["flex"] > 0.35
    hero_cls = " tile-hero" if is_hero else ""
    return (
        f'<div class="tile{hero_cls}" style="flex:{flex_norm:.4f};background:{bg}">'
        f'<div class="tile-top">'
        f'<div class="tile-ticker">{ticker}</div>'
        f'<div class="tile-name">{name}</div>'
        f'</div>'
        f'<div class="tile-amount">{amount}</div>'
        f'</div>'
    )


def _tail_html(tail_items: list, sign: int) -> str:
    if not tail_items:
        return ""
    color = "#0d883c" if sign > 0 else "#ca1e1e"
    rows = []
    for t in tail_items:
        ticker = _esc(t.get("ticker", ""))
        name = _esc(_display_name(t, max_len=24))
        amount = fmt_signed(t["net"])
        rows.append(
            f'<div class="tail-row" style="border-left:4px solid {color}">'
            f'<div class="tail-left">'
            f'<span class="tail-ticker">{ticker}</span>'
            f'<span class="tail-name">{name}</span>'
            f'</div>'
            f'<div class="tail-amount">{amount}</div>'
            f'</div>'
        )
    cols = 2 if len(tail_items) >= 2 else 1
    return (
        f'<div class="tail" style="grid-template-columns:repeat({cols},1fr)">'
        f'{"".join(rows)}</div>'
    )


# ── Main builder ────────────────────────────────────────────────────────────

def build_poster_html(
    market_label: str,
    market_code: str,
    period_str: str,
    weekly_net: float,
    top_buys: list,
    top_sells: list,
    edition: str = None,
) -> str:
    """
    生成 720×1080 海报 HTML。

    参数（与 notify_feishu.py 现有调用签名兼容）:
      market_label: "美股" / "港股" / "A股" / "日股" / "越股"
      market_code:  "US" / "HK" / "CN" / "JP" / "VN"
      period_str:   "2026-03-14 ~ 2026-03-20"
      weekly_net:   本周全市场净买入总额 (raw USD, 未除 1e6)
      top_buys / top_sells: 每个 item:
          { ticker, cn_name, name, buy, sell, net }  金额单位 raw USD
      edition:      顶部期次标签。默认据 ISO 周自动生成 "WEEKLY · VOL.xx"
    """
    # ── 日期 ──
    parts = period_str.split(" ~ ")
    end_date = parts[-1].strip() if parts else period_str
    try:
        y, m, d = end_date.split("-")
        date_display = f"{y}·{m}.{d}"
    except Exception:
        date_display = end_date

    if edition is None:
        wk = iso_week_of(end_date)
        edition = f"WEEKLY · VOL.{wk:02d}" if wk else "WEEKLY"

    # ── 分流 ──
    big_buys, tail_buys = split_tiles(top_buys or [], +1)
    big_sells, tail_sells = split_tiles(top_sells or [], -1)

    buy_tiles_html = "".join(_tile_html(t) for t in big_buys)
    sell_tiles_html = "".join(_tile_html(t) for t in big_sells)
    buy_tail_html = _tail_html(tail_buys, +1)
    sell_tail_html = _tail_html(tail_sells, -1)

    def _section_body(tiles_html, tail_html, direction_cn):
        if tiles_html:
            return f'<div class="treemap">{tiles_html}</div>{tail_html}'
        if tail_html:
            # 只有小额 → 不渲染 treemap 空框，tail 顶到上方填充
            return f'{tail_html}<div class="treemap empty-fill"></div>'
        return f'<div class="treemap empty-state">本周暂无显著净{direction_cn}</div>'

    buy_body = _section_body(buy_tiles_html, buy_tail_html, "买入")
    sell_body = _section_body(sell_tiles_html, sell_tail_html, "卖出")

    # ── 统计数字 ──
    net_display = fmt_signed(weekly_net)
    net_color_class = "green" if weekly_net >= 0 else "red"
    total_items = len([x for x in (top_buys or []) if x.get("net", 0) != 0]) \
                + len([x for x in (top_sells or []) if x.get("net", 0) != 0])

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:720px; height:1080px; background:#f4f2ed; }}
  body {{
    font-family: Helvetica, "Helvetica Neue",
                 "PingFang SC", "Hiragino Sans GB",
                 "NotoSansSC", Arial, sans-serif;
    color:#0a0a0a;
    font-variant-numeric: tabular-nums;
    -webkit-font-smoothing: antialiased;
  }}

  .poster {{
    width:720px; height:1080px;
    padding:28px 26px 22px;
    display:flex; flex-direction:column;
  }}

  /* ── Top Strip ───────────────────────── */
  .top-strip {{
    display:flex; align-items:center; gap:14px;
    margin-bottom:18px;
  }}
  .top-strip .edition {{
    font-size:11px; font-weight:700; letter-spacing:2px; opacity:0.55;
  }}
  .top-strip .rule {{ flex:1; height:1px; background:#0a0a0a; opacity:0.2; }}
  .top-strip .date {{
    font-size:12px; font-weight:700; letter-spacing:0.5px;
  }}

  /* ── Headline + Brand ───────────────── */
  .headline-row {{
    display:flex; justify-content:space-between; align-items:flex-end; gap:16px;
  }}
  .headline {{ flex:1; min-width:0; }}
  .headline h1 {{
    font-size:46px; font-weight:900; letter-spacing:-2px; line-height:0.95;
  }}
  .headline .deck {{
    margin-top:12px; font-size:14px; font-weight:500; line-height:1.35;
    opacity:0.7; max-width:380px;
  }}

  .brand {{
    background:#0a0a0a; color:#fff;
    padding:12px 14px; flex:none;
  }}
  .brand-tag {{
    font-size:11px; font-weight:800; letter-spacing:3px;
    opacity:0.75; margin-bottom:6px;
  }}
  .brand-main {{
    font-size:22px; font-weight:900; letter-spacing:-0.6px; line-height:1;
  }}
  .brand-main .yellow {{ color:#ffcc00; }}

  /* ── Stat Bar ───────────────────────── */
  .statbar {{
    margin-top:16px;
    border-top:2px solid #0a0a0a;
    border-bottom:2px solid #0a0a0a;
    padding:10px 2px;
    display:flex; align-items:flex-end; justify-content:space-between;
  }}
  .statbar .block {{ display:flex; flex-direction:column; gap:4px; }}
  .statbar .right {{ text-align:right; }}
  .statbar .label {{
    font-size:11px; font-weight:700; letter-spacing:1.5px; opacity:0.55;
  }}
  .statbar .value {{
    font-size:40px; font-weight:900; letter-spacing:-1.5px; line-height:1;
  }}
  .statbar .value.green {{ color:#0d883c; }}
  .statbar .value.red   {{ color:#ca1e1e; }}
  .statbar .value .unit {{
    font-size:18px; font-weight:800; margin-left:4px; opacity:0.5;
  }}

  /* ── Section ────────────────────────── */
  .section {{
    margin-top:16px;
    display:flex; flex-direction:column;
    flex:1; min-height:0;
  }}
  .section-header {{
    display:flex; align-items:center; gap:10px;
    margin-bottom:8px; flex:none;
  }}
  .badge {{
    font-size:13px; font-weight:900; letter-spacing:1.5px;
    color:#fff; padding:4px 10px; line-height:1;
  }}
  .badge.buy  {{ background:#0d883c; }}
  .badge.sell {{ background:#ca1e1e; }}
  .section-header .rule {{ flex:1; height:1px; }}
  .section-header .rule.buy  {{ background:#0d883c; opacity:0.4; }}
  .section-header .rule.sell {{ background:#ca1e1e; opacity:0.4; }}

  /* ── Treemap ────────────────────────── */
  .treemap {{
    display:flex; flex-direction:row; gap:3px;
    flex:1; min-height:0;
  }}
  .treemap.empty-state {{
    background:#ffffff; align-items:center; justify-content:center;
    font-size:13px; opacity:0.45; font-weight:500;
  }}
  .treemap.empty-fill {{ flex:0.4; background:transparent; }}

  .tile {{
    display:flex; flex-direction:column; justify-content:space-between;
    padding:12px; color:#fff; min-width:0; overflow:hidden;
  }}
  .tile-top {{ display:flex; flex-direction:column; gap:4px; min-width:0; }}
  .tile-ticker {{
    font-size:22px; font-weight:900; letter-spacing:-0.8px; line-height:0.95;
  }}
  .tile-name {{
    font-size:12px; font-weight:600; line-height:1.2; opacity:0.92;
    display:-webkit-box; -webkit-line-clamp:2;
    -webkit-box-orient:vertical; overflow:hidden;
  }}
  .tile-amount {{
    font-size:18px; font-weight:800; letter-spacing:-0.4px; line-height:1;
  }}

  /* Hero tile (flex > 0.35) */
  .tile.tile-hero {{ padding:16px; }}
  .tile.tile-hero .tile-ticker {{ font-size:32px; }}
  .tile.tile-hero .tile-name {{ font-size:15px; }}
  .tile.tile-hero .tile-amount {{ font-size:26px; }}

  /* ── Tail Row ───────────────────────── */
  .tail {{
    display:grid; gap:3px; margin-top:3px; flex:none;
  }}
  .tail-row {{
    background:#ffffff; padding:9px 12px;
    display:flex; justify-content:space-between; align-items:center;
    gap:8px; min-width:0;
  }}
  .tail-left {{
    display:flex; gap:8px; align-items:baseline;
    min-width:0; overflow:hidden;
  }}
  .tail-ticker {{
    font-size:16px; font-weight:800; letter-spacing:-0.2px; flex:none;
  }}
  .tail-name {{
    font-size:11px; opacity:0.6;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  }}
  .tail-amount {{
    font-size:15px; font-weight:800; letter-spacing:-0.2px; flex:none;
  }}

  /* ── Disclaimer ─────────────────────── */
  .disclaimer {{
    margin-top:14px;
    background:#ffffff; border:2px solid #0a0a0a;
    padding:12px 14px;
    display:flex; gap:10px; align-items:flex-start;
  }}
  .disclaimer .must {{
    background:#0a0a0a; color:#fff;
    font-size:11px; font-weight:900; letter-spacing:1.5px;
    padding:4px 8px; line-height:1; flex:none; align-self:flex-start;
  }}
  .disclaimer .text {{
    font-size:12px; font-weight:500; line-height:1.5; flex:1;
  }}
  .disclaimer .text u {{ text-decoration: underline; }}
  .disclaimer .text .red {{ color:#ca1e1e; font-weight:700; }}
</style>
</head>
<body>
<div class="poster page">

  <div class="top-strip">
    <span class="edition">{_esc(edition)}</span>
    <span class="rule"></span>
    <span class="date">{_esc(date_display)}</span>
  </div>

  <div class="headline-row">
    <div class="headline">
      <h1>韩国人<br/>本周买什么{_esc(market_label)}</h1>
      <p class="deck">周度净流入追踪 · 方块越大金额越重 · 数据源 KSD SEIBro</p>
    </div>
    <div class="brand">
      <div class="brand-tag">RADAR &#9656;</div>
      <div class="brand-main">大佬持仓<br/><span class="yellow">雷达</span></div>
    </div>
  </div>

  <div class="statbar">
    <div class="block">
      <div class="label">周结算净买入</div>
      <div class="value {net_color_class}">{net_display}</div>
    </div>
    <div class="block right">
      <div class="label">涉及标的</div>
      <div class="value">{total_items}<span class="unit">只</span></div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <div class="badge buy">&#9650; 净买入 BUY</div>
      <div class="rule buy"></div>
    </div>
    {buy_body}
  </div>

  <div class="section">
    <div class="section-header">
      <div class="badge sell">&#9660; 净卖出 SELL</div>
      <div class="rule sell"></div>
    </div>
    {sell_body}
  </div>

  <div class="disclaimer">
    <div class="must">必读</div>
    <div class="text">数据来自 <u>韩国预托结济院（KSD）</u> 官方数据，<span class="red">不构成任何投资建议</span>，投资有风险，入市需谨慎。</div>
  </div>

</div>
</body>
</html>""".strip()
