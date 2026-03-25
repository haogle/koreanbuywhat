"""
美股 Ticker ↔ 中文名 映射 + SEIBro 英文名 → Ticker 转换
"""

# SEIBro KOR_SECN_NM (英文全名) → Ticker
# 用名称关键词匹配，覆盖 SEIBro 常见的命名方式
NAME_TO_TICKER = {
    "TESLA": "TSLA",
    "NVIDIA": "NVDA",
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "ALPHABET": "GOOGL",
    "AMAZON": "AMZN",
    "META PLATFORMS": "META",
    "BROADCOM": "AVGO",
    "MICRON TECHNOLOGY": "MU",
    "ADVANCED MICRO DEVICES": "AMD",
    "INTEL": "INTC",
    "PALANTIR": "PLTR",
    "IONQ": "IONQ",
    "ORACLE": "ORCL",
    "NETFLIX": "NFLX",
    "TAIWAN SEMICONDUCTOR": "TSM",
    "BERKSHIRE HATHAWAY": "BRK.B",
    "UNITEDHEALTH": "UNH",
    "REALTY INCOME": "O",
    "MICROSTRATEGY": "MSTR",
    "ROCKET LAB": "RKLB",
    "JOBY AVIATION": "JOBY",
    "NUSCALE POWER": "SMR",
    "ASML": "ASML",
    "LUMENTUM": "LITE",
    "IRIS ENERGY": "IREN",
    "OCCIDENTAL PETROLEUM": "OXY",
    "PLANET LABS": "PL",
    "DIGITALOCEAN": "DOCN",
    "APPLIED OPTOELECTRONICS": "AAOI",
    "YANDEX": "YNDX",
    "CIRCLE INTERNET": "CIRC",
    "BITMINE": "BIMI",
    "MEIWU TECHNOLOGY": "MEIWU",
    "COINBASE": "COIN",
    "SNAP": "SNAP",
    "UBER": "UBER",
    "SHOPIFY": "SHOP",
    "SNOWFLAKE": "SNOW",
    "DATADOG": "DDOG",
    "CROWDSTRIKE": "CRWD",
    "SOFI TECHNOLOGIES": "SOFI",
    "RIVIAN": "RIVN",
    "LUCID": "LCID",
    "SNDSK CRP": "WDC",
    # ETF
    "INVESCO QQQ": "QQQ",
    "INVESCO NASDAQ 100": "QQQM",
    "PROSHARES ULTRAPRO QQQ": "TQQQ",
    "PROSHARES ULTRA QQQ": "QLD",
    "PROSHARES ULTRAPRO SHORT QQ": "SQQQ",
    "DIREXION DAILY SEMICONDUCTORS BULL": "SOXL",
    "DIREXION DAILY SEMICOND": "SOXL",
    "DIREXION SHARES ETF TRUST DAILY SEMICONDUCTOR BEAR": "SOXS",
    "DIREXION DAILY TSLA BULL": "TSLL",
    "DIREXION SHARES ETF TRUST DAILY MSCI SOUTH KOREA BULL": "KORU",
    "DIREXION DAILY 20 YEAR": "TMF",
    "DXN MU BUL2X": "MULL",
    "VANGUARD SP 500 ETF": "VOO",
    "SPDR SP 500 ETF": "SPY",
    "SPDR PORTFOLIO SP 500": "SPLG",
    "SPDR PORTFOLIO SHORT TERM CORPORATE BOND": "SPSB",
    "SPDR PORTFOLIO INTERMEDIATE TERM CORPORATE": "SPIB",
    "ISHARES 0-3 MONTH TREASURY": "SGOV",
    "ISHARES 7-10 YEAR TREASURY": "IEF",
    "ISHARES 20+ YEAR TREASURY": "TLT",
    "ISHARES SEMICONDUCTOR": "SOXX",
    "ISHARES SILVER TRUST": "SLV",
    "ISHARES CORE SP 500": "IVV",
    "SCHWAB US DIVIDEND EQUITY": "SCHD",
    "J.P. MORGAN NASDAQ EQUITY": "JEPQ",
    "JP MORGAN EQUITY PREMIUM": "JEPI",
    "VANECK SEMICONDUCTOR": "SMH",
    "SPDR GOLD SHARES": "GLD",
    "UNITED STATES OIL FUND": "USO",
    "MICROSECTORS GOLD MINERS 3X": "GDXU",
    "GRANITESHARES 2X LONG MRVL": "MRVL",
    "GRANITESHARES 2.0X LONG NVDA": "NVDL",
    "PROSHARES ULTRA SILVER": "AGQ",
    "PROSHARES ULTRASHORT BLOOMBERG CRUDE OIL": "SCO",
    "PROSHARES ULTRA BLOOMBERG CRUDE OIL": "UCO",
    "DEFIANCE DAILY TARGET 2X LONG RKLB": "RKLB.2X",
    "DEFIANCE DAILY TARGET 2X LONG IONQ": "IONQ.2X",
    "DEFIANCE DAILY TARGET 2X SHORT RGTI": "RGTI.S2X",
    "VOLATILITY SHARES TRUST 2X ETHER": "ETHU",
    "VS TRUST 2X LONG VIX": "UVIX",
    "NEOS NASDAQ 100 HIGH INCOME": "QQQI",
    "T-REX 2X LONG MSTR": "MSTU",
    # 港股
    "GLOBAL X CHINA ELECTRIC VEHICLE": "2845.HK",
    "CATL ORD H": "3750.HK",
    "SEMICONDUCTOR MANUFACTURING INTL": "0981.HK",
    "BAIDU": "9888.HK",
    "TENCENT HOLDINGS": "0700.HK",
    "XIAOMI": "1810.HK",
    "CHINA RESOURCES POWER": "0836.HK",
    "ALIBABA": "9988.HK",
    "BYD": "1211.HK",
    "MEITUAN": "3690.HK",
    "JD.COM": "9618.HK",
    "NETEASE": "9999.HK",
    "LI AUTO": "2015.HK",
    "NIO": "9866.HK",
    "XPENG": "9868.HK",
    "KUAISHOU": "1024.HK",
    "BILIBILI": "9626.HK",
    "LENOVO": "0992.HK",
    "CHINA MERCHANT": "3968.HK",
}

# Ticker → 中文名
TICKER_TO_CN = {
    # 科技
    "TSLA": "特斯拉", "NVDA": "英伟达", "AAPL": "苹果", "MSFT": "微软",
    "GOOGL": "谷歌", "AMZN": "亚马逊", "META": "Meta", "AVGO": "博通",
    "MU": "美光科技", "AMD": "AMD", "INTC": "英特尔", "ORCL": "甲骨文",
    "NFLX": "奈飞", "TSM": "台积电", "ASML": "阿斯麦", "PLTR": "Palantir",
    "COIN": "Coinbase", "SNAP": "Snap", "UBER": "Uber", "SHOP": "Shopify",
    "SNOW": "Snowflake", "DDOG": "Datadog", "CRWD": "CrowdStrike",
    "SOFI": "SoFi", "DOCN": "DigitalOcean", "AAOI": "应用光电",
    # AI / 量子 / 新兴
    "IONQ": "IonQ量子", "RKLB": "火箭实验室", "JOBY": "Joby航空",
    "SMR": "NuScale核电", "PL": "Planet卫星", "CIRC": "Circle稳定币",
    "BIMI": "BitMine矿业", "IREN": "Iris能源", "MSTR": "MicroStrategy",
    "YNDX": "Yandex",
    # 传统
    "BRK.B": "伯克希尔", "UNH": "联合健康", "O": "Realty房产",
    "OXY": "西方石油", "WDC": "西部数据",
    # 汽车
    "RIVN": "Rivian", "LCID": "Lucid",
    # ETF
    "QQQ": "纳指100ETF", "QQQM": "纳指100ETF", "TQQQ": "纳指3倍做多",
    "QLD": "纳指2倍做多", "SQQQ": "纳指3倍做空",
    "SOXL": "半导体3倍做多", "SOXS": "半导体3倍做空",
    "TSLL": "特斯拉2倍做多", "KORU": "韩国3倍做多",
    "TMF": "20年国债3倍做多",
    "VOO": "标普500ETF", "SPY": "标普500ETF", "SPLG": "标普500ETF",
    "IVV": "标普500ETF",
    "SPSB": "短期公司债ETF", "SPIB": "中期公司债ETF",
    "SGOV": "0-3月国债ETF", "IEF": "7-10年国债ETF", "TLT": "20+年国债ETF",
    "SOXX": "半导体ETF", "SMH": "半导体ETF",
    "SLV": "白银ETF", "GLD": "黄金ETF",
    "SCHD": "美股红利ETF", "JEPQ": "纳指高收益ETF", "JEPI": "标普高收益ETF",
    "USO": "原油ETF", "GDXU": "金矿3倍做多",
    "NVDL": "英伟达2倍做多", "AGQ": "白银2倍做多",
    "SCO": "原油2倍做空", "UCO": "原油2倍做多",
    "MULL": "美光2倍做多",
    "RKLB.2X": "火箭实验室2倍", "IONQ.2X": "IonQ量子2倍",
    "RGTI.S2X": "Rigetti做空2倍",
    "ETHU": "以太坊2倍做多", "UVIX": "VIX 2倍做多",
    "QQQI": "纳指高收益ETF", "MSTU": "MSTR 2倍做多",
    "MRVL": "Marvell 2倍",
    "LITE": "Lumentum光通信",
    # 港股
    "2845.HK": "中国电动车电池ETF", "3750.HK": "宁德时代H",
    "0981.HK": "中芯国际", "9888.HK": "百度",
    "0700.HK": "腾讯", "1810.HK": "小米",
    "0836.HK": "华润电力", "9988.HK": "阿里巴巴",
    "1211.HK": "比亚迪", "3690.HK": "美团",
    "9618.HK": "京东", "9999.HK": "网易",
    "2015.HK": "理想汽车", "9866.HK": "蔚来",
    "9868.HK": "小鹏汽车", "1024.HK": "快手",
    "9626.HK": "哔哩哔哩", "0992.HK": "联想",
}


def resolve_ticker(secn_name: str) -> str:
    """从 SEIBro 英文名解析出 Ticker"""
    upper = secn_name.upper().strip()
    # 按关键词长度降序匹配，避免短关键词误匹配
    for keyword in sorted(NAME_TO_TICKER, key=len, reverse=True):
        if keyword.upper() in upper:
            return NAME_TO_TICKER[keyword]
    # fallback: 取第一个单词
    return upper.split()[0] if upper else secn_name


def resolve_cn_name(ticker: str) -> str:
    """Ticker → 中文名，找不到则返回空"""
    return TICKER_TO_CN.get(ticker, "")


def format_display(secn_name: str) -> tuple:
    """
    SEIBro 英文名 → (ticker, chinese_name)
    返回: ("TSLA", "特斯拉") 或 ("MICRON", "")
    """
    ticker = resolve_ticker(secn_name)
    cn = resolve_cn_name(ticker)
    return ticker, cn
