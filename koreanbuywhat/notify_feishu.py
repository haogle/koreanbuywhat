"""
每周推送韩国投资者海外股票 TOP5 海报图片到飞书
生成两张海报: 美股 + 港股
"""

import json
import os
import requests
from pathlib import Path
from main import fetch_week, last_week_range
from poster import build_poster_html, render_html_to_image

FEISHU_WEBHOOK = os.environ.get(
    "FEISHU_WEBHOOK",
    "https://open.feishu.cn/open-apis/bot/v2/hook/053e6906-8d74-4330-a7b4-aa481ab51db6",
)
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "cli_a99f669817291013")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "2NhLMbL0ZvkydsxXovkT7entpln0Hryl")

MARKETS = [("US", "美股"), ("HK", "港股")]
OUTPUT_DIR = Path(__file__).resolve().parent


# ── Feishu image upload & send ──────────────────────────────────────────────

def get_tenant_token() -> str:
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"get tenant_access_token failed: {data}")
    return data["tenant_access_token"]


def upload_image(image_path: Path) -> str:
    token = get_tenant_token()
    with open(image_path, "rb") as f:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/images",
            headers={"Authorization": f"Bearer {token}"},
            files={"image": f},
            data={"image_type": "message"},
            timeout=30,
        )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"upload image failed: {data}")
    return data["data"]["image_key"]


def send_image(image_key: str):
    resp = requests.post(
        FEISHU_WEBHOOK,
        json={"msg_type": "image", "content": {"image_key": image_key}},
        timeout=10,
    )
    result = resp.json()
    if result.get("code") != 0:
        print(f"  发送失败: {result}")
    else:
        print(f"  发送成功")


# ── Main pipeline ──────────────────────────────────────────────────────────

def generate_and_send():
    start, end = last_week_range()
    start_fmt = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_fmt = f"{end[:4]}-{end[4:6]}-{end[6:]}"
    period_str = f"{start_fmt} ~ {end_fmt}"

    print(f"结算周期: {period_str}\n")

    for country, label in MARKETS:
        print(f"[{label}] 获取数据...", flush=True)
        df = fetch_week(country, start, end)
        if df.empty:
            print(f"  {label}: 暂无数据，跳过\n")
            continue

        weekly_net = df["net"].sum()

        top_buys = (
            df.sort_values("net", ascending=False).head(5)
            .apply(lambda r: {
                "ticker": r["KOR_SECN_NM"][:8].split(" ")[0],
                "name": r["KOR_SECN_NM"],
                "buy": r["buy"], "sell": r["sell"], "net": r["net"],
            }, axis=1).tolist()
        )
        top_sells = (
            df.sort_values("net", ascending=True).head(5)
            .apply(lambda r: {
                "ticker": r["KOR_SECN_NM"][:8].split(" ")[0],
                "name": r["KOR_SECN_NM"],
                "buy": r["buy"], "sell": r["sell"], "net": r["net"],
            }, axis=1).tolist()
        )

        # 生成 HTML
        html = build_poster_html(
            market_label=label,
            market_code=country,
            period_str=period_str,
            weekly_net=weekly_net,
            top_buys=top_buys,
            top_sells=top_sells,
        )

        # 渲染 PNG
        png_path = OUTPUT_DIR / f"poster_{country.lower()}.png"
        print(f"  渲染海报 → {png_path.name}...", flush=True)
        render_html_to_image(html, png_path)

        # 上传 + 发送
        print(f"  上传到飞书...", flush=True)
        image_key = upload_image(png_path)
        print(f"  发送到飞书群...", flush=True)
        send_image(image_key)
        print()


if __name__ == "__main__":
    generate_and_send()
