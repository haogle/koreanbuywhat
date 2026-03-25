"""
韩国投资者上周海外股票 净买入/净卖出 TOP5 报告
美股 + 港股 | 数据来源: 한국예탁결제원 (KSD) SEIBro
"""

import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ── SEIBro API ──────────────────────────────────────────────────────────────

ENDPOINT = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
HEADERS = {
    "Content-Type": "application/xml; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://seibro.or.kr/websquare/control.jsp"
             "?w2xPath=/IPORTAL/user/ovsSec/BIP_CNTS10013V.xml&menuNo=921",
    "Origin": "https://seibro.or.kr",
}
TASK = "ksd.safe.bip.cnts.OvsSec.process.OvsSecIsinPTask"


# ── helpers ─────────────────────────────────────────────────────────────────

def last_friday():
    """返回上一个周五的日期字符串 YYYYMMDD"""
    today = datetime.now()
    days_since_friday = (today.weekday() - 4) % 7 or 7
    fri = today - timedelta(days=days_since_friday)
    return fri.strftime("%Y%m%d")


def workdays(start, end):
    s = datetime.strptime(start, "%Y%m%d")
    e = datetime.strptime(end, "%Y%m%d")
    d, out = s, []
    while d <= e:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


def last_week_range():
    """返回上周一 ~ 上周五"""
    fri = last_friday()
    end = datetime.strptime(fri, "%Y%m%d")
    start = end - timedelta(days=4)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


# ── SEIBro fetch ────────────────────────────────────────────────────────────

def build_xml(date, country):
    return (
        f'<reqParam action="getImptFrcurStkSetlAmtList" task="{TASK}">'
        f'<PG_START value="1"/><PG_END value="50"/>'
        f'<START_DT value="{date}"/><END_DT value="{date}"/>'
        f'<S_TYPE value="2"/><S_COUNTRY value="{country}"/>'
        f'<D_TYPE value="1"/></reqParam>'
    )


def parse_xml(text):
    root = ET.fromstring(text)
    if int(root.attrib.get("result", 0)) == 0:
        return []
    rows = []
    for data_el in root.findall("data"):
        r = data_el.find("result") or data_el.find("r")
        if r is not None:
            rows.append({c.tag: c.attrib.get("value", "") for c in r})
    return rows


def fetch_day(date, country, session):
    xml = build_xml(date, country)
    resp = session.post(ENDPOINT, headers=HEADERS,
                        data=xml.encode("utf-8"), timeout=30)
    resp.raise_for_status()
    rows = parse_xml(resp.text)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def fetch_week(country, start, end):
    """拉取一周每天 settlement 数据，按股票汇总"""
    dates = workdays(start, end)
    session = requests.Session()
    dfs = []
    for d in dates:
        df = fetch_day(d, country, session)
        if not df.empty:
            dfs.append(df)
    if not dfs:
        return pd.DataFrame()

    raw = pd.concat(dfs, ignore_index=True)
    amt_cols = ["SUM_FRSEC_BUY_AMT", "SUM_FRSEC_SELL_AMT",
                "SUM_FRSEC_NET_BUY_AMT"]
    for c in amt_cols:
        if c in raw.columns:
            raw[c] = pd.to_numeric(raw[c], errors="coerce")

    return (
        raw.groupby(["ISIN", "KOR_SECN_NM"])
        .agg(buy=("SUM_FRSEC_BUY_AMT", "sum"),
             sell=("SUM_FRSEC_SELL_AMT", "sum"),
             net=("SUM_FRSEC_NET_BUY_AMT", "sum"))
        .reset_index()
    )


# ── display ─────────────────────────────────────────────────────────────────

def fmt(usd):
    return f"${usd / 1e6:>8,.1f}M"


def print_top5(df, direction):
    asc = direction == "sell"
    label = "净卖出" if asc else "净买入"
    top = df.sort_values("net", ascending=asc).head(5)
    if top.empty:
        print("  暂无数据\n")
        return

    print(f"  {'#':>2}  {'名称':<42} {'买入':>10} {'卖出':>10} {label:>10}")
    print(f"  {'─' * 2}  {'─' * 42} {'─' * 10} {'─' * 10} {'─' * 10}")
    for i, (_, r) in enumerate(top.iterrows(), 1):
        net_val = r["net"] if not asc else -r["net"]
        print(f"  {i:>2}  {r['KOR_SECN_NM'][:42]:<42} "
              f"{fmt(r['buy'])} {fmt(r['sell'])} {fmt(net_val)}")
    print()


def run_report():
    start, end = last_week_range()
    start_fmt = f"{start[:4]}-{start[4:6]}-{start[6:]}"
    end_fmt = f"{end[:4]}-{end[4:6]}-{end[6:]}"

    print()
    print("=" * 78)
    print("  韩国投资者 上周海外股票 净买入 / 净卖出 TOP 5")
    print(f"  结算日: {start_fmt} ~ {end_fmt}")
    print("  数据来源: 한국예탁결제원 (KSD) SEIBro")
    print("=" * 78)

    for country, label in [("US", "美股"), ("HK", "港股")]:
        print(f"\n  Fetching {label} ({country}) ...", flush=True)
        df = fetch_week(country, start, end)
        if df.empty:
            print(f"  {label}: 暂无数据\n")
            continue

        total_net = df["net"].sum()
        print(f"  [{label}] 周净买入合计: {fmt(total_net)}\n")

        print(f"  ▲ {label} 净买入 TOP 5")
        print(f"  {'─' * 74}")
        print_top5(df, "buy")

        print(f"  ▼ {label} 净卖出 TOP 5")
        print(f"  {'─' * 74}")
        print_top5(df, "sell")


if __name__ == "__main__":
    run_report()
