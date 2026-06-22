"""
每周推送韩国投资者海外股票 TOP5 到飞书。
对每个市场（美股/港股）推送两条消息：
  1) 海报 PNG （treemap 图，720×1080）
  2) 社交网络风格的文字版（按 social_copy.build_social_text 格式）

支持的环境变量：
  FEISHU_WEBHOOK / FEISHU_APP_ID / FEISHU_APP_SECRET
  SKIP_SOCIAL=1   仅推海报，不推文字
  SKIP_IMAGE=1    仅推文字，不渲染/上传海报
"""

import os
import time
import requests
from pathlib import Path
from main import fetch_week, last_week_range
from poster import build_poster_html, render_html_to_image
from stock_names import format_display
from social_copy import build_social_text

# 配置改为强制走环境变量（避免 secret 入库）。本地开发可写入 .env 或 shell rc：
#   export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/..."
#   export FEISHU_APP_ID="cli_..."
#   export FEISHU_APP_SECRET="..."
FEISHU_WEBHOOK = os.environ["FEISHU_WEBHOOK"]
FEISHU_APP_ID = os.environ["FEISHU_APP_ID"]
FEISHU_APP_SECRET = os.environ["FEISHU_APP_SECRET"]

MARKETS = [("US", "美股"), ("HK", "港股")]
OUTPUT_DIR = Path(__file__).resolve().parent


# ── Feishu helpers ──────────────────────────────────────────────────────────

def _request_with_retry(method, url, *, retries=3, backoff=2.0, **kwargs):
    """对飞书 API 的瞬时网络/SSL 故障做指数退避重试。"""
    last_exc = None
    for attempt in range(retries):
        try:
            return requests.request(method, url, **kwargs)
        except (requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff ** attempt)
    raise last_exc


def get_tenant_token() -> str:
    resp = _request_with_retry(
        "POST",
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
        resp = _request_with_retry(
            "POST",
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
    resp = _request_with_retry(
        "POST",
        FEISHU_WEBHOOK,
        json={"msg_type": "image", "content": {"image_key": image_key}},
        timeout=10,
    )
    result = resp.json()
    if result.get("code") != 0:
        print(f"  图片发送失败: {result}")
    else:
        print(f"  图片发送成功")


def send_text(text: str):
    """推送纯文本消息到飞书 webhook 群。"""
    resp = _request_with_retry(
        "POST",
        FEISHU_WEBHOOK,
        json={"msg_type": "text", "content": {"text": text}},
        timeout=10,
    )
    result = resp.json()
    code = result.get("code", result.get("StatusCode", -1))
    if code != 0:
        print(f"  文字发送失败: {result}")
    else:
        print(f"  文字发送成功")


# ── Pipeline ────────────────────────────────────────────────────────────────

def build_rows(df, country: str):
    """SEIBro DataFrame → top_buys / top_sells (5 each)。"""
    def _make(r):
        ticker, cn_name = format_display(
            r["KOR_SECN_NM"],
            isin=r.get("ISIN", ""),
            is_hk=(country == "HK"),
        )
        return {
            "ticker": ticker, "cn_name": cn_name, "name": r["KOR_SECN_NM"],
            "buy": r["buy"], "sell": r["sell"], "net": r["net"],
        }

    top_buys = df.sort_values("net", ascending=False).head(5).apply(_make, axis=1).tolist()
    top_sells = df.sort_values("net", ascending=True).head(5).apply(_make, axis=1).tolist()
    return top_buys, top_sells


def push_market(country: str, label: str, start: str, end: str, period_str: str):
    """单个市场：抓数据 → 渲染海报 → 推文字 + 图片。"""
    print(f"[{label}] 获取数据...", flush=True)
    df = fetch_week(country, start, end)
    if df.empty:
        print(f"  {label}: 暂无数据，跳过\n")
        return

    weekly_net = df["net"].sum()
    top_buys, top_sells = build_rows(df, country)

    # ── 海报 ──
    if not os.environ.get("SKIP_IMAGE"):
        html = build_poster_html(
            market_label=label, market_code=country,
            period_str=period_str, weekly_net=weekly_net,
            top_buys=top_buys, top_sells=top_sells,
        )
        png_path = OUTPUT_DIR / f"poster_{country.lower()}.png"
        print(f"  渲染海报 → {png_path.name}...", flush=True)
        render_html_to_image(html, png_path)
        print(f"  上传 + 推送海报到飞书...", flush=True)
        send_image(upload_image(png_path))

    # ── 社交文案 ──
    if not os.environ.get("SKIP_SOCIAL"):
        text = build_social_text(
            market_label=label, market_code=country,
            period_str=period_str, weekly_net=weekly_net,
            top_buys=top_buys, top_sells=top_sells,
        )
        print(f"  推送社交文案到飞书...", flush=True)
        send_text(text)

    print()


def generate_and_send(start: str = None, end: str = None):
    """主流程，默认上一交易周。"""
    if start is None or end is None:
        start, end = last_week_range()
    start_fmt = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_fmt = f"{end[:4]}-{end[4:6]}-{end[6:]}"
    period_str = f"{start_fmt} ~ {end_fmt}"

    print(f"结算周期: {period_str}\n")

    for country, label in MARKETS:
        push_market(country, label, start, end, period_str)


if __name__ == "__main__":
    import sys
    # 支持 CLI: python notify_feishu.py 20260608 20260612
    if len(sys.argv) == 3:
        generate_and_send(sys.argv[1], sys.argv[2])
    else:
        generate_and_send()
