"""
social_copy.py — 生成社交网络（小红书 / 朋友圈 / 微博）风格的周报文案

用法:
    from social_copy import build_social_text
    text = build_social_text(
        market_label="美股", market_code="US",
        period_str="2026-06-08 ~ 2026-06-12",
        weekly_net=2352000000,    # raw USD
        top_buys=[{ticker, cn_name, name, net, buy, sell}, ...],
        top_sells=[...],
    )

设计要点（基于 2026-06 被小红书风控后的调整）：
- 风险提示前置（在数据前），降低被判为"投资建议"的风险
- 不含「信号阅读」段（结论分析容易触发风控）
- 每行: `代码 名称 +金额`，最多一句中性参考（如"连续第N周入选"）
- 末尾 hashtag 串，美股用小写 ticker，港股用中文名
- 无站外链接、无 CTA、无导流文案
"""

from datetime import datetime
from typing import List, Dict, Optional


RISK_NOTICE = (
    "⚠️ 风险提示\n"
    "本内容仅基于公开披露数据整理，不构成任何投资建议或交易邀约，"
    "亦不代表本账号立场。所涉标的因数据来源限制存在延迟或疏漏可能；"
    "历史资金流向不代表未来价格走势。投资有风险，入市需谨慎，"
    "请根据自身风险承受能力自主决策并自担风险。"
)

SOURCE_LINE = "数据来源 · 韩国预托结济院（KSD）官方结算口径"


# ── Format helpers ──────────────────────────────────────────────────────────

def _fmt_signed_m(usd: float) -> str:
    """+$1,757.4M / −$166.4M （U+2212 负号）"""
    v = abs(usd) / 1e6
    if v >= 1000:
        body = f"${v / 1000:.2f}B"
    else:
        body = f"${v:,.1f}M"
    if usd > 0:
        return f"+{body}"
    if usd < 0:
        return f"−{body}"
    return body


def _iso_week_of(date_str: str) -> int:
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return dt.isocalendar().week
    except Exception:
        return 0


def _period_short(period_str: str) -> str:
    """'2026-06-08 ~ 2026-06-12' → '6/8-6/12'"""
    parts = [p.strip() for p in period_str.split("~")]
    if len(parts) != 2:
        return period_str
    try:
        s = datetime.strptime(parts[0], "%Y-%m-%d")
        e = datetime.strptime(parts[1], "%Y-%m-%d")
        return f"{s.month}/{s.day}-{e.month}/{e.day}"
    except Exception:
        return period_str


def _row_line(item: Dict, is_buy: bool, market_code: str) -> str:
    """单行: 'SOXL 半导体 3x 做多 +$1,757.4M（commentary）'"""
    ticker = item.get("ticker", "").strip()
    cn = (item.get("cn_name") or "").strip()
    name = (item.get("name") or "").strip()

    # 显示标签：港股 ticker 已含 .HK，美股直接 ticker
    label = ticker if (market_code == "HK" or ticker.endswith(".HK")) else ticker

    # 副标题：优先中文名，否则英文截短
    if cn:
        subtitle = cn
    elif name and not name.isdigit():
        subtitle = name[:24]
    else:
        subtitle = ""

    amount = _fmt_signed_m(-abs(item["net"]) if not is_buy else abs(item["net"]))
    base = f"{label} {subtitle} {amount}".strip()

    commentary = (item.get("commentary") or "").strip()
    if commentary:
        return f"{base}（{commentary}）"
    return base


def _hashtags(items: List[Dict], market_code: str, limit: int = 10) -> str:
    """
    生成 hashtag 串。
      US: #ticker 小写，无空格分隔
      HK: #中文名（无则 fallback ticker 数字部分），无空格分隔
    """
    tags = []
    seen = set()
    for item in items[:limit]:
        if market_code == "US":
            t = (item.get("ticker") or "").strip().lower()
            if t and t not in seen:
                seen.add(t)
                tags.append(f"#{t}")
        else:  # HK
            cn = (item.get("cn_name") or "").strip()
            if cn and cn not in seen:
                seen.add(cn)
                # 去掉中文名里的空格便于做 hashtag
                tags.append(f"#{cn.replace(' ', '')}")
            else:
                # 没有中文名的：用 ticker 数字部分
                t = (item.get("ticker") or "").replace(".HK", "").lstrip("0")
                if t and t not in seen:
                    seen.add(t)
                    tags.append(f"#{t}")
    return "".join(tags)


# ── Main builder ────────────────────────────────────────────────────────────

def build_social_text(
    market_label: str,
    market_code: str,
    period_str: str,
    weekly_net: float,
    top_buys: List[Dict],
    top_sells: List[Dict],
    lead_extra: Optional[str] = None,
) -> str:
    """
    生成社交网络风格的周报文案。

    market_label: "美股" / "港股"
    market_code:  "US" / "HK"
    period_str:   "2026-06-08 ~ 2026-06-12"
    weekly_net:   本周净买入总额 (raw USD, 未除 1e6)
    top_buys/top_sells: 每条 {ticker, cn_name, name, buy, sell, net, commentary?}
                       commentary 字段可选，用于补充一句中性说明
    lead_extra:   可选补充句（接在数据流量后面），如"创近半年最高单周流入纪录。"
    """
    parts = [p.strip() for p in period_str.split("~")]
    end_date = parts[-1] if len(parts) == 2 else period_str
    wk = _iso_week_of(end_date)
    short = _period_short(period_str)

    # ── 标题 ──
    title = f"韩国人本周买什么{market_label} · Week {wk:02d} ({short})"

    # ── 主述句 ──
    parts_short = period_str.split(" ~ ")
    try:
        s_dt = datetime.strptime(parts_short[0], "%Y-%m-%d")
        e_dt = datetime.strptime(parts_short[1], "%Y-%m-%d")
        date_zh = f"{s_dt.month} 月 {s_dt.day} 日至 {e_dt.day} 日"
    except Exception:
        date_zh = period_str

    direction_word = "净买入" if weekly_net >= 0 else "净流出"
    amount_str = _fmt_signed_m(weekly_net)
    lead = (
        f"据韩国预托结济院（KSD）{date_zh}结算数据，"
        f"韩国个人投资者单周{market_label}{direction_word} {amount_str}。"
    )
    if lead_extra:
        lead = lead + lead_extra if lead.endswith("。") else lead + "。" + lead_extra

    # ── 买卖明细 ──
    buy_lines = "\n".join(_row_line(it, True, market_code) for it in top_buys[:5])
    sell_lines = "\n".join(_row_line(it, False, market_code) for it in top_sells[:5])

    # ── Hashtags（买入 + 卖出 合并去重）──
    tags = _hashtags(top_buys + top_sells, market_code, limit=10)

    return "\n\n".join([
        title,
        lead,
        SOURCE_LINE,
        RISK_NOTICE,
        "主要买入方向\n" + buy_lines,
        "主要卖出方向\n" + sell_lines,
        tags,
    ])
