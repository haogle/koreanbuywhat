"""
美股 / 港股 Ticker ↔ 中文名 映射 + SEIBro 英文名 → Ticker 转换

解析优先级：
  1. ISIN 直查  (resolve_by_isin)       — 最可靠，尤其覆盖开曼/百慕大注册的港股
  2. 名称关键词 (resolve_ticker)          — 次之，依赖 NAME_TO_TICKER
  3. 安全兜底  (format_display fallback) — 未识别时走占位符，不复用脏数据
未命中时通过 _log_missing 落盘到 _missing_names.log，方便后续补表。
"""

import datetime
import os
from pathlib import Path

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
    "EXXON MOBIL": "XOM",
    "APPLOVIN": "APP",
    "COREWEAVE": "CRWV",
    "MARVELL TECHNOLOGY": "MRVL",
    "TERADYNE": "TER",
    "TOWER SEMICONDUCTOR": "TSEM",
    "VIAVI SOLUTIONS": "VIAV", "VIAVI": "VIAV",
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
    "PROSHARES ULTRASHORT SILVER": "ZSL",
    "VANECK JP MORGAN EM LOCAL CURRENCY BOND": "EMLC", "VANECK JP MORGAN EM LOCAL": "EMLC",
    # ── 港股 (HK) ──
    # 科技 / 互联网
    "TENCENT HOLDINGS": "0700", "ALIBABA GROUP": "9988", "MEITUAN": "3690",
    "JD.COM": "9618", "BAIDU": "9888", "NETEASE": "9999",
    "KUAISHOU": "1024", "BILIBILI": "9626", "XIAOMI": "1810",
    "KINGDEE": "0268", "KINGSOFT CLOUD": "3896", "SENSETIME": "0020",
    "TRIP.COM": "9961", "WEIBO": "9898", "KE HOLDINGS": "2423",
    "GDS HOLDINGS": "9698", "POP MART": "9992",
    "PING AN HEALTHCARE": "1833", "JD HEALTH": "6618",
    "JD LOGISTICS": "2618", "XPENG": "9868", "NIO": "9866",
    "LI AUTO": "2015", "GEELY AUTOMOBILE": "0175",
    "BYD CO": "1211", "BYD ELECTRONIC": "0285",
    "LEAPMOTOR": "9863", "YADEA GROUP": "1585",
    "CHINA STAR ENTERTAINMENT": "0326",
    "AIA GROUP": "1299",
    "MANYCORE TECH": "0068",
    "GIGADEVICE": "3986",
    "HENGRUI PHARMA": "1276", "JIANGSU HENGRUI": "1276",
    "MONTAGE TECHNOLOGY": "6809",
    # AI 独角兽（港股 2026 IPO）
    "MINIMAX": "0100", "XIYU TECHNOLOGY": "0100",
    "ZHIPU": "2513", "ZHIPU AI": "2513",
    "CHINA ENERGY ENGINEERING": "3996",
    "SMART CITY DEVELOPMENT": "8268",
    # 半导体 / 硬件
    "SEMICONDUCTOR MANUFACTURING INTL": "0981", "HUA HONG SEMICONDUCTOR": "1347",
    "SUNNY OPTICAL": "2382", "FOXCONN INTERCONNECT": "6088",
    "ASM PACIFIC": "0522", "Q TECHNOLOGY": "1478",
    "LENOVO GROUP": "0992", "ZTE CORP": "0763",
    "COWELL E": "1415",
    # 新能源 / 电力
    "CATL ORD H": "3750", "GANFENGLITHIUM": "1772",
    "TIANQI LITHIUM": "9696", "XINYI SOLAR": "0968",
    "XINYI GLASS": "0868", "GCL TECHNOLOGY": "3800",
    "LONGI GREEN": "1289",
    "CHINA LONGYUAN": "0916", "CGN POWER": "1816",
    "CHINA SUNTIEN": "0956", "CHINA DATANG": "1798",
    "DONGFANG ELECTRIC": "1072", "HARBIN ELECTRIC": "1133",
    "XINJIANG GOLDWIND": "2208", "XINTE ENERGY": "1799",
    "CHINA RESOURCES POWER": "0836", "CHINA POWER INTL": "2380",
    "HUANENG POWER": "0902",
    # 金融 / 保险
    "PING AN INSURANCE": "2318", "CHINA LIFE INSURANCE": "2628",
    "AIA GROUP": "1299", "PICC PROPERTY": "2328",
    "CITIC SECURITIES": "6030", "HUATAI SECURITIES": "6886",
    "GUOTAI JUNAN": "2611", "CHINA GALAXY SECURITIES": "6881",
    "INDUSTRIAL AND COMMERCIAL BANK": "1398", "CHINA CONSTRUCTION BANK": "0939",
    # 资源 / 能源
    "PETROCHINA": "0857", "CHINA PETROLEUM AND CHEMICAL": "0386",
    "CNOOC": "0883", "CHINA SHENHUA": "1088",
    "CHINA COAL ENERGY": "1898", "ZIJIN MINING": "2899",
    "JIANGXI COPPER": "0358", "CMOC GROUP": "3993",
    "CHINA HONGQIAO": "1378", "ALUMINUM CORP": "2600",
    "YANCOAL AUSTRALIA": "3668", "YANKUANG ENERGY": "1171",
    "CHINA GOLD": "2099",
    # 消费 / 医药
    "WUXI BIOLOGICS": "2269", "WUXI APPTEC": "2359",
    "BEIGENE": "6160", "INNOVENT BIOLOGICS": "1801",
    "REMEGEN": "9995", "ZAI LAB": "9688",
    "AKESO": "9926", "GIANT BIOGENE": "2367",
    "ALPHAMAB": "9966",
    "PRADA": "1913", "ANTA SPORTS": "2020",
    "BUDWEISER BREWING": "1876", "FUFENG GROUP": "0546",
    "SAMSONITE": "1910", "MAN WAH": "1999",
    "MIXUE GROUP": "2097", "LAOPU GOLD": "6181",
    "CTG DUTY-FREE": "1880",
    # 地产 / 建筑
    "COUNTRY GARDEN": "2007", "CHINA VANKE": "2202",
    "LONGFOR GROUP": "0960", "SUNAC CHINA": "1918",
    "CHINA STATE CONSTRUCTION": "3311",
    "CHINA RAILWAY CONSTRUCTION": "1186",
    # 公用事业 / 基建
    "CHINA MOBILE": "0941", "CHINA TELECOM": "0728",
    "CHINA UNICOM": "0762", "CITIC TELECOM": "1883",
    "CHINA COMMUNICATIONS SERVICES": "0552",
    "ENN ENERGY": "2688", "CHINA GAS": "0384",
    "KUNLUN ENERGY": "0135",
    "COSCO SHIPPING HOLDINGS": "1919", "COSCO SHIPPING ENERGY": "1138",
    "ORIENT OVERSEAS": "0316",
    # 工业
    "GREAT WALL MOTOR": "2333", "WEICHAI POWER": "2338",
    "ZOOMLION HEAVY": "1157", "SHANGHAI ELECTRIC": "2727",
    "NINE DRAGONS PAPER": "2689", "DONGYUE GROUP": "0189",
    # 机器人 / AI
    "ROBOSENSE": "2498", "HORIZONROBOT": "9660",
    "UBTECH ROBOTICS": "9880",
    "GLOBAL X CHINA ROBOTICS": "2807",
    # ETF
    "GLOBAL X CHINA ELECTRIC VEHICLE": "2845",
    "GLOBAL X CHINA SEMICONDUCTOR": "3191",
    "GLOBAL X CHINA CLOUD": "2826",
    "GLOBAL X CHINA BIOTECH": "2820",
    "GLOBAL X CHINA CLEAN ENERGY": "2809",
    "GLOBAL X CHINA CONSUMER": "2806",
    "GLOBAL X HANG SENG TECH": "3088",
    "GLOBAL X HANG SENG HIGH DIVIDEND": "3110",
    "GLOBAL X MSCI CHINA": "3040",
    "GLOBAL X ASIA SEMICONDUCTOR": "3119",
    "GLOBAL X NASDAQ100 COV CALL": "3014",
    "CSOP HANG SENG TECH INDEX DAILY 2X": "7226",
    "CSOP HANG SENG TECH INDEX DAILY -2X": "7552",
    "CSOP HANG SENG TECH INDEX ETF": "3033",
    "CSOP FTSE CHINA A50": "2822",
    "CSOP TESLA 2X": "9160",
    "CSOP MICROSTRATEGY 2X": "9173",
    "CSOP GOLD FUTURES DAILY 2X": "7299",
    "CSOP SZSE CHINEXT": "3147",
    "HANG SENG TECH INDEX ETF": "3032",
    "TRACKER FUND OF HONG KONG": "2800",
    "ISHARES CORE CSI 300": "2846",
    "ISHARES CORE MSCI TAIWAN": "3174",
    "ISHARES CORE SP BSE SENSEX INDIA": "2836",
    "ISHARES HS TECH": "3067",
    "CHINAAMC CSI 300": "3188",
    "CHINAAMC HANG SENG HK BIOTECH": "3069",
    "XL2CSOPHYNIX": "7266", "XL2CSOPNVDA": "7247",
    "XL2CSOPSMSN": "7249",
    "SAMSUNG BITCOIN": "3135",
    "SAMSUNG SP GSCI CRUDE OIL": "3175",
    # Others
    "CAROTE": "2549", "BLOKS GROUP": "1850",
    "XUNCE": "2415", "BUSYMING": "2912",
    "WUXI LEAD INTELLIGENT": "0011", "SANHUA INTELLIGENT": "2541",
    "SUN.KING TECHNOLOGY": "1165",
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
    "XOM": "埃克森美孚",
    # AI / 基础设施 / 半导体设备
    "APP": "AppLovin", "CRWV": "CoreWeave",
    "TER": "泰瑞达", "TSEM": "Tower半导体",
    "VIAV": "Viavi光通信",
    # 债 / 杠杆 ETF
    "ZSL": "白银2倍做空", "EMLC": "新兴市场本币债ETF",
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
    "MRVL": "迈威尔科技",
    "LITE": "Lumentum光通信",
    # ── 港股 ──
    # 科技 / 互联网
    "0700": "腾讯", "9988": "阿里巴巴", "3690": "美团",
    "9618": "京东", "9888": "百度", "9999": "网易",
    "1024": "快手", "9626": "哔哩哔哩", "1810": "小米",
    "0268": "金蝶国际", "3896": "金山云", "0020": "商汤",
    "9961": "携程", "9898": "微博", "2423": "贝壳",
    "9698": "万国数据", "9992": "泡泡玛特",
    "1833": "平安好医生", "6618": "京东健康",
    "2618": "京东物流", "9868": "小鹏汽车", "9866": "蔚来",
    "2015": "理想汽车", "0175": "吉利汽车",
    "1211": "比亚迪", "0285": "比亚迪电子",
    "9863": "零跑汽车", "1585": "雅迪控股",
    "0326": "中国星集团", "1299": "友邦保险",
    "0068": "群核科技", "3986": "兆易创新",
    "1276": "恒瑞医药", "6809": "澜起科技",
    "0100": "MiniMax", "2513": "智谱科技",
    "3996": "中国能建", "8268": "智慧城市发展",
    # 半导体 / 硬件
    "0981": "中芯国际", "1347": "华虹半导体",
    "2382": "舜宇光学", "6088": "鸿腾精密",
    "0522": "ASM太平洋", "1478": "丘钛科技",
    "0992": "联想集团", "0763": "中兴通讯",
    "1415": "高伟电子",
    # 新能源
    "3750": "宁德时代H", "1772": "赣锋锂业",
    "9696": "天齐锂业", "0968": "信义光能",
    "0868": "信义玻璃", "3800": "协鑫科技",
    "0916": "龙源电力", "1816": "中广核电力",
    "0956": "中国新能源", "1798": "大唐新能源",
    "1072": "东方电气", "1133": "哈尔滨电气",
    "2208": "金风科技", "1799": "新特能源",
    "0836": "华润电力", "2380": "中国电力",
    "0902": "华能国际",
    # 金融
    "2318": "中国平安", "2628": "中国人寿",
    "1299": "友邦保险", "2328": "中国财险",
    "6030": "中信证券", "6886": "华泰证券",
    "2611": "国泰君安", "6881": "中国银河",
    "1398": "工商银行", "0939": "建设银行",
    # 资源
    "0857": "中国石油", "0386": "中国石化",
    "0883": "中海油", "1088": "中国神华",
    "1898": "中煤能源", "2899": "紫金矿业",
    "0358": "江西铜业", "3993": "洛阳钼业",
    "1378": "中国宏桥", "2600": "中铝",
    "3668": "兖煤澳大利亚", "1171": "兖矿能源",
    "2099": "中国黄金",
    # 消费 / 医药
    "2269": "药明生物", "2359": "药明康德",
    "6160": "百济神州", "1801": "信达生物",
    "9995": "荣昌生物", "9688": "再鼎医药",
    "9926": "康方生物", "2367": "巨子生物",
    "9966": "康宁杰瑞",
    "1913": "Prada", "2020": "安踏体育",
    "1876": "百威亚太", "0546": "阜丰集团",
    "1910": "新秀丽", "1999": "敏华控股",
    "2097": "蜜雪冰城", "6181": "老铺黄金",
    "1880": "中免国际",
    # 地产 / 建筑
    "2007": "碧桂园", "2202": "万科",
    "0960": "龙湖集团", "1918": "融创中国",
    "3311": "中国建筑国际", "1186": "中国铁建",
    # 电信 / 基建
    "0941": "中国移动", "0728": "中国电信",
    "0762": "中国联通", "1883": "中信国际电讯",
    "0552": "中国通信服务",
    "2688": "新奥能源", "0384": "中国燃气",
    "0135": "昆仑能源",
    "1919": "中远海控", "1138": "中远海能",
    "0316": "东方海外",
    # 工业
    "2333": "长城汽车", "2338": "潍柴动力",
    "1157": "中联重科", "2727": "上海电气",
    "2689": "玖龙纸业", "0189": "东岳集团",
    # 机器人 / AI
    "2498": "速腾聚创", "9660": "地平线机器人",
    "9880": "优必选",
    # ETF
    "2845": "中国电动车ETF", "3191": "中国半导体ETF",
    "2826": "中国云计算ETF", "2820": "中国生物科技ETF",
    "2809": "中国清洁能源ETF", "2806": "中国消费ETF",
    "3088": "恒生科技ETF", "3110": "恒生高股息ETF",
    "3040": "MSCI中国ETF", "3119": "亚洲半导体ETF",
    "3014": "纳指100备兑ETF",
    "7226": "恒生科技2倍做多", "7552": "恒生科技2倍做空",
    "3033": "恒生科技指数ETF", "2822": "A50 ETF",
    "9160": "特斯拉2倍做多", "9173": "MSTR 2倍做多",
    "7299": "黄金期货2倍", "3147": "创业板ETF",
    "3032": "恒生科技ETF", "2800": "盈富基金",
    "2846": "沪深300 ETF", "3174": "台湾ETF",
    "2836": "印度ETF", "3067": "恒生科技ETF",
    "3188": "华夏沪深300", "3069": "生物科技ETF",
    "7266": "舜宇光学2倍", "7247": "英伟达2倍",
    "7249": "三星2倍",
    "3135": "三星比特币ETF", "3175": "三星原油ETF",
    # Others
    "2549": "卡罗特", "1850": "布鲁可",
    "2415": "寻策", "2912": "忙忙科技",
    "2807": "中国机器人ETF",
    "0011": "无锡先导智能", "2541": "三花智控",
    "1165": "阳光电源",
}


# ── ISIN → 港股 ticker 映射 ──────────────────────────────────────────────────
# 开曼 / 百慕大 / 英属维尔京等离岸注册的港股，ISIN 不以 HK 开头，必须查表。
# 本港注册公司（ISIN 以 HK0000 开头）可通过 resolve_by_isin 中的规则自动还原。
# 缺失条目会自动记录到 _missing_names.log，按周补进即可。
ISIN_TO_HK = {
    # 科技 / 互联网（多为开曼注册）
    "KYG875721634": ("0700", "腾讯控股"),
    "KYG017191142": ("9988", "阿里巴巴"),
    "KYG596691041": ("3690", "美团"),
    "KYG8208B1014": ("9618", "京东集团"),
    "KYG9830T1067": ("1810", "小米集团"),
    "KYG1238E1070": ("9888", "百度集团"),
    "KYG6427A1022": ("9999", "网易"),
    "KYG5260B1098": ("1024", "快手"),
    "KYG1098L1081": ("9626", "哔哩哔哩"),
    "KYG2107Y1052": ("9961", "携程集团"),
    "KYG596651045": ("9992", "泡泡玛特"),
    "KYG211261020": ("9868", "小鹏汽车"),
    "KYG6625A1658": ("9866", "蔚来"),
    "KYG5002G1126": ("2015", "理想汽车"),
    "KYG2121W1039": ("9863", "零跑汽车"),

    # 半导体 / 硬件
    "CNE100007DX6": ("6809", "澜起科技"),   # MONTAGE TECHNOLOGY, H-share listed Feb 2026
    "CNE100007DJ5": ("3986", "兆易创新"),   # GigaDevice Semiconductor
    "KYG8020E1199": ("0981", "中芯国际"),
    "KYG4634J1013": ("1347", "华虹半导体"),
    "KYG8586D1097": ("2382", "舜宇光学"),
    "KYG5257Y1089": ("0992", "联想集团"),

    # 医药
    "CNE100006XS6": ("1276", "恒瑞医药"),   # Jiangsu Hengrui Pharmaceuticals

    # 新上市 / IPO (2026 AI 独角兽潮)
    "KYG5860M1024": ("0068", "群核科技"),   # Manycore Tech, IPO 2026-04-17
    "KYG6181S1093": ("0100", "MiniMax"),    # 稀宇科技 (SEIBro 常以 "00100" 占位)
    "CNE100007DH9": ("2513", "智谱科技"),   # Zhipu AI

    # 注：HK0000xxxxx 这类 ISIN 不在此直接映射，让它走名称关键词匹配 —
    # 大多数 HK0000xxx 条目的 SEIBro KOR_SECN_NM 都是可识别的英文全名。

    # 金融 / 保险
    "CNE1000003X6": ("2318", "中国平安"),
    "CNE1000002L3": ("1398", "工商银行"),
    "CNE1000002H1": ("0939", "建设银行"),
}


# ── Missing-mapping log（质量漏斗）─────────────────────────────────────────
_MISSING_LOG = Path(__file__).parent / "_missing_names.log"


def _log_missing(isin: str, secn_name: str, market: str = "HK") -> None:
    """未识别的标的落盘，运营可在下周海报前补表。环境变量 NO_MISSING_LOG=1 可关闭。"""
    if os.environ.get("NO_MISSING_LOG"):
        return
    try:
        line = f"{datetime.date.today().isoformat()}\t{market}\t{isin}\t{secn_name}\n"
        with open(_MISSING_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass  # 日志失败不阻断主流程


# ── 解析函数 ────────────────────────────────────────────────────────────────

def resolve_by_isin(isin: str) -> tuple:
    """
    ISIN → (ticker, cn_name)。命中返回具体值，未命中返回 (None, "")。
    只走显式映射表 —— 试图从 ISIN 中段反推 HK 代码会产生虚假匹配
    (e.g. HK0000218211 中段 21821 并不对应 HUA HONG 的 1347)。
    """
    if not isin:
        return (None, "")
    isin = isin.strip().upper()
    if isin in ISIN_TO_HK:
        return ISIN_TO_HK[isin]
    return (None, "")


def resolve_ticker(secn_name: str, is_hk: bool = False) -> str:
    """从 SEIBro 英文名解析出 Ticker（作为 ISIN 解析失败的 fallback）"""
    upper = secn_name.upper().strip()
    # 按关键词长度降序匹配，避免短关键词误匹配
    for keyword in sorted(NAME_TO_TICKER, key=len, reverse=True):
        if keyword.upper() in upper:
            return NAME_TO_TICKER[keyword]
    # fallback: 取第一个单词
    return upper.split()[0] if upper else secn_name


def resolve_cn_name(ticker: str) -> str:
    """Ticker → 中文名，找不到则返回空"""
    return TICKER_TO_CN.get(ticker, "") or TICKER_TO_CN.get(ticker.zfill(4), "")


def _fmt_hk_display(ticker: str) -> str:
    """港股代码统一成 '0700.HK' 格式（4 位数字 + .HK）"""
    if ticker.isdigit():
        return f"{ticker.zfill(4)}.HK"
    return ticker


def format_display(secn_name: str, isin: str = "", is_hk: bool = False) -> tuple:
    """
    SEIBro 行 → (display_ticker, chinese_name)
      美股: ("TSLA", "特斯拉")
      港股: ("0700.HK", "腾讯控股")
      未识别港股: ("HK:XXXXXX", "")  — XXXXXX 是 ISIN 尾 6 位，绝不会再出现"00068/00068"这种双重显示

    参数：
      secn_name: SEIBro 返回的 KOR_SECN_NM（英文或韩文名）
      isin:      SEIBro 返回的 ISIN（强烈建议传入，港股场景下是主键）
      is_hk:     是否港股市场
    """
    secn_name = (secn_name or "").strip()

    # ① ISIN 直查（最可靠）
    if isin:
        ticker, cn = resolve_by_isin(isin)
        if ticker:
            return (_fmt_hk_display(ticker) if is_hk else ticker), cn

    # ② 港股特例：SEIBro 偶尔直接返回 4-5 位纯数字（"00068"、"03986"），
    #    这本身就是 HK 代码。直接用，别再走兜底占位符。
    if is_hk and secn_name.isdigit() and 3 <= len(secn_name) <= 5:
        ticker = secn_name.lstrip("0") or "0"
        cn = resolve_cn_name(ticker)
        return _fmt_hk_display(ticker), cn

    # ③ 名称关键词匹配
    ticker = resolve_ticker(secn_name, is_hk)
    cn = resolve_cn_name(ticker)

    # 命中：走正常显示
    hit = bool(cn) or (ticker and ticker in TICKER_TO_CN) or (
        secn_name and ticker != secn_name.upper().split()[0] if secn_name else False
    )
    if hit:
        return (_fmt_hk_display(ticker) if is_hk else ticker), cn

    # ③ 兜底：标记未识别，落盘日志，显示干净占位符
    _log_missing(isin or "", secn_name, market="HK" if is_hk else "US")
    if is_hk:
        tail = (isin[-6:] if isin else ticker[:6]) or "??????"
        return f"HK:{tail}", ""
    # 美股未识别：保留解析出的第一个英文单词作 ticker，中文名留空（前端不会重复显示）
    return ticker or "—", ""
