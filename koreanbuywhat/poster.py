"""
poster.py -- 韩国投资者海外股票 TOP5 海报 HTML 生成 + Playwright 渲染 PNG
"""

import html as html_mod
from pathlib import Path


# ────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────

def render_highlight_codes(rows, side: str, n: int = 2) -> str:
    codes = [html_mod.escape(r.get("ticker", "")) for r in rows[:n] if r.get("ticker")]
    if not codes:
        return '<span style="color:#9ca3af">—</span>'
    parts = []
    for i, code in enumerate(codes):
        parts.append(f'<span>{code}</span>')
        if i != len(codes) - 1:
            sep_color = "#6ee7b7" if side == "buy" else "#fda4af"
            parts.append(f'<span style="color:{sep_color};margin:0 2px">/</span>')
    return "".join(parts)


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
    """
    生成韩国投资者海外股票 TOP5 海报 HTML。
    market_label: "美股" / "港股"
    top_buys / top_sells: [{"ticker", "name", "buy", "sell", "net"}, ...]
    """

    # 日期拆分
    parts = period_str.split(" ~ ")
    end_date = parts[-1] if parts else period_str
    try:
        y, m, d = end_date.split("-")
        year_display = y
        md_display = f"{m}.{d}"
    except Exception:
        year_display = end_date[:4]
        md_display = end_date[5:]

    # 头部胶囊
    buy_rows = [{"ticker": r.get("ticker", r.get("name", "")[:6])} for r in top_buys]
    sell_rows = [{"ticker": r.get("ticker", r.get("name", "")[:6])} for r in top_sells]
    highlight_buys = render_highlight_codes(buy_rows, "buy", 2)
    highlight_sells = render_highlight_codes(sell_rows, "sell", 2)

    # Flag emoji
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

            if is_buy:
                bar_class = "from-emerald-500 to-teal-400" if idx < 3 else "from-emerald-400 to-emerald-300"
                num_color = "text-emerald-600"
                net_display = f"+{fmt_usd(net)}"
            else:
                bar_class = "from-rose-500 to-orange-500" if idx < 3 else "from-rose-400 to-rose-300"
                num_color = "text-rose-600"
                net_display = f"-{fmt_usd(abs(net))}"

            detail = f"买入 {fmt_usd(buy_amt)} / 卖出 {fmt_usd(sell_amt)}"

            # 中文名标签
            cn_badge = ""
            if cn_name:
                cn_badge = f'<span class="text-[9px] text-gray-400 font-medium truncate leading-none pt-[1px]">{cn_name}</span>'

            html_rows.append(f"""
                <div class="flex items-center justify-between py-1">
                    <div class="flex items-center gap-3 flex-1 min-w-0 mr-2">
                        <div class="w-1 h-5 bg-gradient-to-br {bar_class} rounded-full flex-none shadow-sm"></div>
                        <div class="ticker-row">
                            <span class="text-lg font-bold text-gray-800 leading-none flex-none tracking-tight">{ticker}</span>
                            {cn_badge}
                        </div>
                    </div>
                    <div class="text-right flex-none">
                        <div class="text-[15px] font-bold {num_color} mono-nums leading-none">{net_display}</div>
                        <div class="text-[8px] text-gray-300 leading-none mt-[3px]">{detail}</div>
                    </div>
                </div>
            """)

        if not html_rows:
            tip = "本周暂无显著净买入" if is_buy else "本周暂无显著净卖出"
            html_rows.append(f'<div class="text-[10px] text-gray-400 px-1 py-2">{tip}</div>')
        return "\n".join(html_rows)

    buys_html = render_rows(top_buys, is_buy=True)
    sells_html = render_rows(top_sells, is_buy=False)

    # 周净买入
    net_sign = "+" if weekly_net >= 0 else ""
    net_color = "#059669" if weekly_net >= 0 else "#e11d48"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background-color: #ffffff;
            display: flex; justify-content: center; align-items: center;
            min-height: 100vh; margin: 0; padding: 20px;
        }}
        .poster-container {{ width: 100%; max-width: 420px; background: #ffffff;
            border-radius: 24px; overflow: hidden;
            box-shadow: 0 20px 50px -10px rgba(0,0,0,0.1);
            display: flex; flex-direction: column; }}
        .mono-nums {{ font-family: 'JetBrains Mono', monospace; letter-spacing: -0.5px; }}
        .highlight-wrap {{ margin-top: 4px; padding: 0 20px 6px 20px; }}
        .highlight-row {{ display: flex; gap: 8px; }}
        .highlight-card {{ flex: 1; border-radius: 12px; padding: 6px 10px;
            display: flex; align-items: center; gap: 8px;
            box-shadow: 0 2px 6px rgba(15,23,42,0.06); border: 1px solid transparent; }}
        .highlight-card-buy {{ background: #ecfdf3; border-color: #bbf7d0; }}
        .highlight-card-sell {{ background: #fef2f2; border-color: #fecaca; }}
        .highlight-tag {{ border-radius: 999px; padding: 2px 6px; font-size: 9px;
            font-weight: 700; line-height: 1; color: #ffffff; }}
        .highlight-tag-buy {{ background: #22c55e; }}
        .highlight-tag-sell {{ background: #f97373; }}
        .highlight-text {{ font-size: 12px; font-weight: 700; line-height: 1;
            padding-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .highlight-text-buy {{ color: #064e3b; }}
        .highlight-text-sell {{ color: #881337; }}
        .ticker-row {{ display: flex; align-items: center; gap: 0.35rem;
            min-width: 0; flex: 1; }}
    </style>
</head>
<body>
    <div class="poster-container page">
        <!-- Header -->
        <div class="px-5 pt-5 pb-1 bg-white border-b border-gray-50 flex-none">
            <div class="flex justify-between items-end">
                <div>
                    <div class="flex items-center gap-2 mb-1">
                        <span class="bg-gray-900 text-white text-[9px] font-bold px-1.5 py-[2px] rounded-sm uppercase tracking-wider leading-none">서학개미 레이더</span>
                    </div>
                    <h1 class="text-2xl font-extrabold text-gray-900 leading-none tracking-tight">
                        {flag} 韩国人买什么{market_label}
                    </h1>
                </div>
                <div class="text-right">
                    <div class="text-lg font-bold text-gray-400 mono-nums leading-none">{html_mod.escape(year_display)}</div>
                    <div class="text-xl font-bold text-gray-900 mono-nums leading-none">{html_mod.escape(md_display)}</div>
                </div>
            </div>
            <div class="highlight-wrap">
                <div class="highlight-row">
                    <div class="highlight-card highlight-card-buy">
                        <div class="highlight-tag highlight-tag-buy">买入</div>
                        <div class="highlight-text highlight-text-buy">{highlight_buys}</div>
                    </div>
                    <div class="highlight-card highlight-card-sell">
                        <div class="highlight-tag highlight-tag-sell">卖出</div>
                        <div class="highlight-text highlight-text-sell">{highlight_sells}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Summary -->
        <div class="px-5 py-1 bg-gray-50/50 flex items-center gap-2">
            <span class="text-[10px] text-gray-400">周结算净买入</span>
            <span class="text-[13px] font-bold mono-nums" style="color:{net_color}">{net_sign}{fmt_usd(abs(weekly_net))}</span>
        </div>

        <!-- Buy section -->
        <div class="flex flex-col border-b border-gray-100">
            <div class="px-5 py-2 flex items-center bg-emerald-50/50">
                <div class="flex items-center gap-1.5">
                    <div class="w-1.5 h-1.5 bg-emerald-500 rounded-full"></div>
                    <h2 class="text-[10px] font-bold text-emerald-800 uppercase tracking-wider">● TOP 周度净买入 (NET BUY)</h2>
                </div>
            </div>
            <div class="flex flex-col gap-[2px] px-4 py-1">
                {buys_html}
            </div>
        </div>

        <!-- Sell section -->
        <div class="flex flex-col bg-gray-50/60">
            <div class="px-5 py-2 flex items-center bg-rose-50/50 border-t border-rose-100/50">
                <div class="flex items-center gap-1.5">
                    <div class="w-1.5 h-1.5 bg-rose-500 rounded-full"></div>
                    <h2 class="text-[10px] font-bold text-rose-800 uppercase tracking-wider">● TOP 周度净卖出 (NET SELL)</h2>
                </div>
            </div>
            <div class="flex flex-col gap-[2px] px-4 py-1 pb-2">
                {sells_html}
            </div>
        </div>

        <!-- Footer -->
        <div class="px-4 py-1 bg-white border-t border-gray-50 flex-none">
            <p class="text-[7px] text-gray-300 text-center leading-tight">
                来自한국예탁결제원(KSD)官方数据，仅供参考，不构成任何投资建议。
            </p>
        </div>
    </div>
</body>
</html>""".strip()
