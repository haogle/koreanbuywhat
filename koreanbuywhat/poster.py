"""
poster.py -- 韩国投资者海外股票 TOP5 海报 HTML 生成 + Playwright 渲染 PNG
"""

import html as html_mod
from pathlib import Path


def fmt_usd(v):
    if abs(v) >= 1e9:
        return f"${v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:,.1f}M"
    if abs(v) >= 1e3:
        return f"${v / 1e3:,.0f}K"
    return f"${v:,.0f}"


# ────────────────────────────────────────────
# Playwright rendering
# ────────────────────────────────────────────

def render_html_to_image(html_content: str, output_path) -> None:
    from playwright.sync_api import sync_playwright

    font_path = Path(__file__).parent / "fonts" / "NotoSansSC-VariableFont_wght.ttf"
    font_url = font_path.resolve().as_uri()

    font_css = f"""
    <style>
    @font-face {{
        font-family: 'NotoSansSC';
        src: url('{font_url}') format('truetype');
        font-weight: 100 900;
        font-style: normal;
    }}
    </style>
    """
    html_content = html_content.replace("</head>", f"{font_css}</head>", 1)
    html_content = html_content.replace(
        "font-family: 'Inter', -apple-system, sans-serif;",
        "font-family: 'Inter', -apple-system, 'NotoSansSC', sans-serif;",
    )

    output_path = Path(output_path)
    if not output_path.is_absolute():
        output_path = Path(__file__).resolve().parent / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1440}, device_scale_factor=2)
        page.set_content(html_content, wait_until="networkidle")
        page.wait_for_timeout(1500)
        clip = page.evaluate("""() => {
            const el = document.querySelector('.page');
            const r = el.getBoundingClientRect();
            return { x: Math.floor(r.x), y: Math.floor(r.y),
                     width: Math.ceil(r.width), height: Math.ceil(r.height) + 40 };
        }""")
        page.screenshot(path=str(output_path), clip=clip, type="png")
        browser.close()


# ────────────────────────────────────────────
# HTML poster builder
# ────────────────────────────────────────────

def build_poster_html(
    market_label: str,
    market_code: str,
    period_str: str,
    weekly_net: float,
    top_buys: list,
    top_sells: list,
) -> str:
    # 日期拆分
    parts = period_str.split(" ~ ")
    start_date = parts[0] if parts else period_str
    end_date = parts[-1] if parts else period_str
    try:
        y, m, d = end_date.split("-")
        md_display = f"{m}.{d}"
    except Exception:
        md_display = end_date[5:]
    try:
        _, sm, sd = start_date.split("-")
        period_short = f"{sm}.{sd} – {md_display}"
    except Exception:
        period_short = period_str

    flag = "🇺🇸" if market_code == "US" else "🇭🇰"

    # 渲染行
    def render_rows(rows, is_buy):
        html_rows = []
        for idx, row in enumerate(rows[:5]):
            ticker = html_mod.escape(row.get("ticker", ""))
            cn_name = html_mod.escape(row.get("cn_name", ""))
            net = row.get("net", 0)
            buy_amt = row.get("buy", 0)
            sell_amt = row.get("sell", 0)
            rank = idx + 1

            if is_buy:
                accent = "#10b981"
                accent_bg = "rgba(16,185,129,0.08)"
                net_display = f"+{fmt_usd(net)}"
            else:
                accent = "#f43f5e"
                accent_bg = "rgba(244,63,94,0.08)"
                net_display = f"-{fmt_usd(abs(net))}"

            detail = f"买 {fmt_usd(buy_amt)} · 卖 {fmt_usd(sell_amt)}"

            label_html = f'<span style="color:#94a3b8;font-size:10px;margin-left:6px">{cn_name}</span>' if cn_name else ""

            html_rows.append(f"""
            <div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid rgba(241,245,249,0.8)">
                <div style="width:22px;height:22px;border-radius:6px;background:{accent_bg};color:{accent};font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0">{rank}</div>
                <div style="flex:1;min-width:0;margin-left:10px">
                    <div style="display:flex;align-items:baseline">
                        <span style="font-size:15px;font-weight:700;color:#0f172a;letter-spacing:-0.3px">{ticker}</span>
                        {label_html}
                    </div>
                    <div style="font-size:9px;color:#cbd5e1;margin-top:2px">{detail}</div>
                </div>
                <div style="text-align:right;flex-shrink:0;margin-left:8px">
                    <div class="mono-nums" style="font-size:16px;font-weight:700;color:{accent};letter-spacing:-0.5px">{net_display}</div>
                </div>
            </div>""")

        if not html_rows:
            html_rows.append('<div style="padding:12px 0;font-size:11px;color:#94a3b8">本周暂无数据</div>')
        return "\n".join(html_rows)

    buys_html = render_rows(top_buys, is_buy=True)
    sells_html = render_rows(top_sells, is_buy=False)

    net_sign = "+" if weekly_net >= 0 else ""
    net_color = "#10b981" if weekly_net >= 0 else "#f43f5e"

    # top 2 tickers for hero badges
    buy_tickers = [r.get("ticker", "") for r in top_buys[:2]]
    sell_tickers = [r.get("ticker", "") for r in top_sells[:2]]
    buy_hero = " / ".join(buy_tickers) if buy_tickers else "—"
    sell_hero = " / ".join(sell_tickers) if sell_tickers else "—"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: #0f172a;
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; padding: 20px;
        }}
        .poster {{
            width: 420px;
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 25px 60px rgba(0,0,0,0.5);
        }}
        .mono-nums {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body>
<div class="poster page">

    <!-- ===== HEADER ===== -->
    <div style="padding:24px 24px 16px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
                <div style="display:inline-block;background:rgba(99,102,241,0.15);color:#818cf8;font-size:9px;font-weight:700;padding:3px 8px;border-radius:4px;letter-spacing:0.5px;text-transform:uppercase">서학개미 레이더</div>
                <h1 style="font-size:24px;font-weight:800;color:#f8fafc;margin-top:8px;letter-spacing:-0.5px;line-height:1.1">
                    {flag} 韩国人买什么{html_mod.escape(market_label)}
                </h1>
            </div>
            <div style="text-align:right">
                <div class="mono-nums" style="font-size:28px;font-weight:800;color:#f8fafc;letter-spacing:-1px;line-height:1">{html_mod.escape(md_display)}</div>
                <div style="font-size:10px;color:#64748b;margin-top:2px">{html_mod.escape(period_short)}</div>
            </div>
        </div>

        <!-- Hero badges -->
        <div style="display:flex;gap:8px;margin-top:14px">
            <div style="flex:1;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.2);border-radius:10px;padding:8px 12px;display:flex;align-items:center;gap:8px">
                <div style="background:#10b981;color:#fff;font-size:9px;font-weight:700;padding:2px 7px;border-radius:20px">BUY</div>
                <div style="font-size:12px;font-weight:700;color:#6ee7b7;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{html_mod.escape(buy_hero)}</div>
            </div>
            <div style="flex:1;background:rgba(244,63,94,0.1);border:1px solid rgba(244,63,94,0.2);border-radius:10px;padding:8px 12px;display:flex;align-items:center;gap:8px">
                <div style="background:#f43f5e;color:#fff;font-size:9px;font-weight:700;padding:2px 7px;border-radius:20px">SELL</div>
                <div style="font-size:12px;font-weight:700;color:#fda4af;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{html_mod.escape(sell_hero)}</div>
            </div>
        </div>

        <!-- Net total -->
        <div style="margin-top:12px;display:flex;align-items:center;gap:8px">
            <span style="font-size:10px;color:#64748b">周结算净流入</span>
            <span class="mono-nums" style="font-size:18px;font-weight:800;color:{net_color}">{net_sign}{fmt_usd(abs(weekly_net))}</span>
        </div>
    </div>

    <!-- ===== CONTENT ===== -->
    <div style="background:#ffffff;border-radius:16px 16px 0 0;margin-top:4px">

        <!-- Buy section -->
        <div style="padding:14px 20px 4px">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
                <div style="width:6px;height:6px;border-radius:50%;background:#10b981"></div>
                <span style="font-size:10px;font-weight:700;color:#10b981;letter-spacing:0.5px;text-transform:uppercase">Top 净买入</span>
            </div>
            {buys_html}
        </div>

        <!-- Divider -->
        <div style="margin:0 20px;border-top:1px dashed #e2e8f0"></div>

        <!-- Sell section -->
        <div style="padding:14px 20px 4px">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
                <div style="width:6px;height:6px;border-radius:50%;background:#f43f5e"></div>
                <span style="font-size:10px;font-weight:700;color:#f43f5e;letter-spacing:0.5px;text-transform:uppercase">Top 净卖出</span>
            </div>
            {sells_html}
        </div>

        <!-- Footer -->
        <div style="padding:10px 20px 14px;text-align:center">
            <div style="font-size:8px;color:#cbd5e1">来自 한국예탁결제원 (KSD) 官方数据 · 仅供参考</div>
        </div>
    </div>
</div>
</body>
</html>""".strip()
