"""
每周推送韩国投资者海外股票 TOP5 报告到飞书
用法:
  python notify_feishu.py                           # 使用默认 webhook
  FEISHU_WEBHOOK=https://... python notify_feishu.py  # 自定义 webhook
"""

import json
import os
import requests
from main import fetch_week, last_week_range

FEISHU_WEBHOOK = os.environ.get(
    "FEISHU_WEBHOOK",
    "https://open.feishu.cn/open-apis/bot/v2/hook/053e6906-8d74-4330-a7b4-aa481ab51db6",
)

MARKETS = [("US", "美股"), ("HK", "港股")]


def fmt(usd):
    return f"${abs(usd) / 1e6:,.1f}M"


def build_message():
    """构建飞书 post 富文本消息"""
    start, end = last_week_range()
    start_fmt = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_fmt = f"{end[:4]}-{end[4:6]}-{end[6:]}"

    lines = []  # 飞书 post content 行

    # 标题行
    lines.append([{"tag": "text", "text": f"结算日: {start_fmt} ~ {end_fmt}\n"}])

    for country, label in MARKETS:
        df = fetch_week(country, start, end)
        if df.empty:
            lines.append([{"tag": "text", "text": f"\n【{label}】暂无数据\n"}])
            continue

        total_net = df["net"].sum()
        sign = "+" if total_net >= 0 else ""
        lines.append([
            {"tag": "text", "text": f"\n【{label}】周净买入: "},
            {"tag": "text", "text": f"{sign}{fmt(total_net)}"},
            {"tag": "text", "text": "\n"},
        ])

        # 净买入 TOP5
        top_buy = df.sort_values("net", ascending=False).head(5)
        lines.append([{"tag": "text", "text": "▲ 净买入 TOP5\n"}])
        for i, (_, r) in enumerate(top_buy.iterrows(), 1):
            name = r["KOR_SECN_NM"][:30]
            lines.append([{
                "tag": "text",
                "text": f"{i}. {name}  净买入 {fmt(r['net'])}\n",
            }])

        # 净卖出 TOP5
        top_sell = df.sort_values("net", ascending=True).head(5)
        lines.append([{"tag": "text", "text": "\n▼ 净卖出 TOP5\n"}])
        for i, (_, r) in enumerate(top_sell.iterrows(), 1):
            name = r["KOR_SECN_NM"][:30]
            lines.append([{
                "tag": "text",
                "text": f"{i}. {name}  净卖出 {fmt(-r['net'])}\n",
            }])

    lines.append([{"tag": "text", "text": "\n数据来源: 한국예탁결제원 (KSD) SEIBro"}])

    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "📊 韩国投资者 上周海外股票 TOP5",
                    "content": lines,
                }
            }
        },
    }


def send():
    payload = build_message()
    resp = requests.post(
        FEISHU_WEBHOOK,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=15,
    )
    result = resp.json()
    if result.get("code") == 0:
        print(f"飞书推送成功")
    else:
        print(f"飞书推送失败: {result}")
        raise SystemExit(1)


if __name__ == "__main__":
    send()
