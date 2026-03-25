"""
Vercel Serverless Function — 韩国投资者上周海外股票 TOP5 报告
GET /api → JSON 报告
"""

import json
import sys
import os

# 让 Vercel 能找到项目根目录的模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import BaseHTTPRequestHandler
from main import fetch_week, last_week_range


def generate_report():
    start, end = last_week_range()
    start_fmt = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_fmt = f"{end[:4]}-{end[4:6]}-{end[6:]}"

    report = {
        "period": f"{start_fmt} ~ {end_fmt}",
        "source": "한국예탁결제원 (KSD) SEIBro",
        "markets": [],
    }

    for country, label in [("US", "美股"), ("HK", "港股")]:
        df = fetch_week(country, start, end)
        if df.empty:
            report["markets"].append({"market": label, "code": country, "data": None})
            continue

        top_buy = (
            df.sort_values("net", ascending=False)
            .head(5)
            .apply(lambda r: {
                "name": r["KOR_SECN_NM"],
                "buy": round(r["buy"]),
                "sell": round(r["sell"]),
                "net": round(r["net"]),
            }, axis=1)
            .tolist()
        )

        top_sell = (
            df.sort_values("net", ascending=True)
            .head(5)
            .apply(lambda r: {
                "name": r["KOR_SECN_NM"],
                "buy": round(r["buy"]),
                "sell": round(r["sell"]),
                "net": round(r["net"]),
            }, axis=1)
            .tolist()
        )

        report["markets"].append({
            "market": label,
            "code": country,
            "weekly_net": round(df["net"].sum()),
            "top_buy": top_buy,
            "top_sell": top_sell,
        })

    return report


def build_html(data):
    def fmt(v):
        sign = "" if v >= 0 else "-"
        return f"{sign}${abs(v)/1e6:,.1f}M"

    def row_html(items, direction):
        color = "#16a34a" if direction == "buy" else "#dc2626"
        label = "净买入" if direction == "buy" else "净卖出"
        key = "top_buy" if direction == "buy" else "top_sell"
        rows = ""
        for i, item in enumerate(items[key], 1):
            net_val = item["net"] if direction == "buy" else -item["net"]
            rows += f"""<tr>
              <td>{i}</td>
              <td class="name">{item['name'][:45]}</td>
              <td class="num">{fmt(item['buy'])}</td>
              <td class="num">{fmt(item['sell'])}</td>
              <td class="num" style="color:{color};font-weight:700">{fmt(net_val)}</td>
            </tr>"""
        return f"""
        <table>
          <thead><tr>
            <th width="30">#</th><th>名称</th>
            <th width="90">买入</th><th width="90">卖出</th>
            <th width="90">{label}</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    markets_html = ""
    for m in data["markets"]:
        if m.get("data") is None and "top_buy" not in m:
            markets_html += f'<h2>{m["market"]} ({m["code"]}) — 暂无数据</h2>'
            continue
        net = m["weekly_net"]
        net_color = "#16a34a" if net >= 0 else "#dc2626"
        markets_html += f"""
        <h2>{m['market']} ({m['code']})</h2>
        <p class="summary">周净买入合计:
          <span style="color:{net_color};font-weight:700">{fmt(net)}</span>
        </p>
        <h3>▲ 净买入 TOP 5</h3>
        {row_html(m, 'buy')}
        <h3>▼ 净卖出 TOP 5</h3>
        {row_html(m, 'sell')}
        """

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>韩国投资者上周海外股票 TOP5</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
         max-width:800px; margin:0 auto; padding:20px; background:#f8fafc; color:#1e293b; }}
  h1 {{ font-size:1.4em; margin-bottom:4px; }}
  .meta {{ color:#64748b; font-size:0.85em; margin-bottom:24px; }}
  h2 {{ font-size:1.15em; margin-top:28px; padding-bottom:6px;
       border-bottom:2px solid #e2e8f0; }}
  h3 {{ font-size:0.95em; margin:14px 0 6px; color:#475569; }}
  .summary {{ margin:8px 0; font-size:0.95em; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.85em; margin-bottom:12px; }}
  th {{ text-align:left; padding:6px 8px; background:#f1f5f9;
       border-bottom:2px solid #cbd5e1; font-weight:600; color:#475569; }}
  td {{ padding:5px 8px; border-bottom:1px solid #e2e8f0; }}
  .name {{ max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  @media(max-width:600px) {{
    .name {{ max-width:160px; }}
    table {{ font-size:0.78em; }}
  }}
</style>
</head>
<body>
  <h1>韩国投资者 上周海外股票 净买入/净卖出 TOP 5</h1>
  <p class="meta">结算日: {data['period']} &nbsp;|&nbsp; 数据来源: {data['source']}</p>
  {markets_html}
  <p class="meta" style="margin-top:32px;text-align:center">
    Powered by SEIBro (한국예탁결제원)</p>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = generate_report()

        accept = self.headers.get("Accept", "")
        if "application/json" in accept:
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            ctype = "application/json; charset=utf-8"
        else:
            body = build_html(data).encode()
            ctype = "text/html; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "s-maxage=3600, stale-while-revalidate=600")
        self.end_headers()
        self.wfile.write(body)
