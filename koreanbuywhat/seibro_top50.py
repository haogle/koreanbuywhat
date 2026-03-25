"""
SEIBro 韩国投资者海外股票持仓 TOP50 数据抓取工具
==============================================
数据来源: 韩国预托结算院 (KSD) SEIBro
接口: POST https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp
方式: 直接请求 WebSquare 后端接口，无需浏览器，纯 requests

用法:
  python seibro_top50.py                                    # 最新日期 全部国家
  python seibro_top50.py --date 20260310 --country US       # 指定日期 美国
  python seibro_top50.py --start 20260301 --end 20260310 --all-countries  # 批量
  python seibro_top50.py --type settlement --d-type 1       # 结算金额(买入)
"""

import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time
import argparse

ENDPOINT = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"

HEADERS = {
    "Content-Type": "application/xml; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://seibro.or.kr/websquare/control.jsp?w2xPath=/IPORTAL/user/ovsSec/BIP_CNTS10013V.xml&menuNo=921",
    "Origin": "https://seibro.or.kr",
}

COUNTRY_CODES = {"ALL": "全部", "US": "美国", "HK": "香港", "CN": "中国", "JP": "日本", "VN": "越南"}

SUBMISSIONS = {
    "custody": ("getImptFrcurStkCusRemaList", "1"),      # 보관금액
    "settlement": ("getImptFrcurStkSetlAmtList", "2"),    # 결제금액
}
TASK = "ksd.safe.bip.cnts.OvsSec.process.OvsSecIsinPTask"


def build_xml(action, s_type, date, country="ALL", d_type=None):
    d_type_tag = f'<D_TYPE value="{d_type}"/>' if d_type else ""
    return (
        f'<reqParam action="{action}" task="{TASK}">'
        f'<PG_START value="1"/><PG_END value="50"/>'
        f'<START_DT value="{date}"/><END_DT value="{date}"/>'
        f'<S_TYPE value="{s_type}"/><S_COUNTRY value="{country}"/>'
        f'{d_type_tag}</reqParam>'
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


def fetch(date, country="ALL", qtype="custody", d_type="1", session=None):
    s = session or requests.Session()
    action, s_type = SUBMISSIONS[qtype]
    xml = build_xml(action, s_type, date, country,
                    d_type=d_type if qtype == "settlement" else None)
    resp = s.post(ENDPOINT, headers=HEADERS, data=xml.encode("utf-8"), timeout=30)
    resp.raise_for_status()
    rows = parse_xml(resp.text)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["query_date"] = date
    df["country_filter"] = country
    df["query_type"] = qtype
    for col in ["SUM_FRSEC_AMT", "RNUM"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def latest_date(qtype="custody"):
    today = datetime.now()
    dt = today - timedelta(days=2 if qtype == "custody" else 1)
    while dt.weekday() >= 5:
        dt -= timedelta(days=1)
    return dt.strftime("%Y%m%d")


def workdays(start, end):
    s, e = datetime.strptime(start, "%Y%m%d"), datetime.strptime(end, "%Y%m%d")
    d, out = s, []
    while d <= e:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


def batch(dates, countries=None, qtype="custody", delay=0.5):
    countries = countries or ["ALL"]
    session = requests.Session()
    dfs = []
    for date in dates:
        for c in countries:
            print(f"  {qtype} | {date} | {c}...", end=" ")
            try:
                df = fetch(date, c, qtype, session=session)
                print(f"→ {len(df)} rows")
                if not df.empty:
                    dfs.append(df)
            except Exception as e:
                print(f"→ ERROR: {e}")
            time.sleep(delay)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="SEIBro TOP50")
    ap.add_argument("--date", type=str)
    ap.add_argument("--start", type=str)
    ap.add_argument("--end", type=str)
    ap.add_argument("--country", default="ALL")
    ap.add_argument("--type", default="custody", choices=["custody", "settlement"])
    ap.add_argument("--d-type", default="1")
    ap.add_argument("--output", default="seibro_top50.csv")
    ap.add_argument("--all-countries", action="store_true")
    a = ap.parse_args()

    cs = list(COUNTRY_CODES.keys()) if a.all_countries else [a.country.upper()]
    if a.start and a.end:
        dates = workdays(a.start, a.end)
        print(f"批量: {len(dates)} 工作日 × {len(cs)} 国家")
    else:
        dates = [a.date or latest_date(a.type)]
        print(f"单日: {dates[0]} | {cs} | {a.type}")

    df = batch(dates, cs, a.type)
    if df.empty:
        print("未获取到数据")
    else:
        df.to_csv(a.output, index=False, encoding="utf-8-sig")
        print(f"\n✅ {len(df)} 条 → {a.output}")
        print(df.head(10)[["RNUM","NATION_NM","ISIN","KOR_SECN_NM","SUM_FRSEC_AMT"]].to_string(index=False))
