#!/usr/bin/env python3
"""
全球风险日报 - 数据抓取脚本（中文版）
每天定时运行，聚合6大类风险数据，输出中文 JSON
"""

import json
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone
import os
import re

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
os.makedirs(OUTPUT_DIR, exist_ok=True)

ctx = ssl.create_default_context()
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
now_utc = datetime.now(timezone.utc).isoformat()

results = {
    "date": today,
    "updated_at": now_utc,
    "categories": {}
}

def safe_fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RiskDashboard/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return json.dumps({"error": str(e)})

# ============================================================
# 🌍 国家/地区名称中文化映射
# ============================================================
COUNTRY_ZH = {
    # 常见国家
    "Philippines": "菲律宾", "Indonesia": "印度尼西亚", "Japan": "日本",
    "Taiwan": "台湾", "China": "中国",
    "Chile": "智利", "Peru": "秘鲁", "Mexico": "墨西哥",
    "United States": "美国", "USA": "美国", "US": "美国",
    "Canada": "加拿大",
    "Russia": "俄罗斯", "Russian Federation": "俄罗斯",
    "Turkey": "土耳其", "Türkiye": "土耳其",
    "Ukraine": "乌克兰",
    "India": "印度", "Nepal": "尼泊尔",
    "Tonga": "汤加", "Fiji": "斐济", "Fiji Islands": "斐济",
    "New Zealand": "新西兰",
    "Papua New Guinea": "巴布亚新几内亚",
    "Cuba": "古巴",
    "Guinea": "几内亚",
    "Honduras": "洪都拉斯", "El Salvador": "萨尔瓦多",
    "Nicaragua": "尼加拉瓜",
    "Australia": "澳大利亚",
    "Brazil": "巴西",
    "South Korea": "韩国", "Korea": "韩国",
    "Vietnam": "越南", "Thailand": "泰国", "Myanmar": "缅甸",
    "Argentina": "阿根廷",
    "Iceland": "冰岛",
    "Germany": "德国", "France": "法国", "UK": "英国",
    "Italy": "意大利", "Spain": "西班牙",
    "South Africa": "南非",
    # 海洋/区域
    "Atlantic": "大西洋", "Pacific": "太平洋",
    "Mid-Atlantic Ridge": "中大西洋海岭",
    "Southern Mid-Atlantic Ridge": "南大西洋中脊",
    "Auckland Islands": "奥克兰群岛",
    "region": "区域",
    "Zone": "区域",
}

# 灾害中文化
DISASTER_ZH = {
    "flood": "洪水", "Flood": "洪水",
    "earthquake": "地震", "Earthquake": "地震",
    "forest fire": "森林火灾", "Forest fire": "森林火灾",
    "tropical cyclone": "热带气旋", "cyclone": "气旋",
    "typhoon": "台风", "Typhoon": "台风",
    "hurricane": "飓风", "Hurricane": "飓风",
    "volcano": "火山", "Volcano": "火山",
    "tsunami": "海啸",
    "Green": "绿色（低）",
    "Orange": "橙色（中）",
    "Red": "红色（高）",
}

SEVERITY_ZH = {"Green": "低", "Orange": "中", "Red": "高"}

def zh_place(place):
    """将地震地点描述中文化"""
    if not place:
        return place
    # 先处理方向词 of -> 空格
    place = place.replace(" of ", " ")
    # 方向映射（需要替换完整单词避免误伤城市名里的字母）
    dir_map = {
        r'\bNW\b': '西北', r'\bSE\b': '东南',
        r'\bSW\b': '西南', r'\bNE\b': '东北',
        r'\bNNW\b': '北西北', r'\bSSE\b': '南东南',
        r'\bSSW\b': '西南偏南', r'\bESE\b': '东南偏东',
        r'\bWNW\b': '西北偏西', r'\bENE\b': '东北偏东',
        r'\bN\b(?!(?:\w|orth))': '北',
        r'\bS\b(?!(?:\w|outh))': '南',
        r'\bE\b(?!(?:\w|ast))': '东',
        r'\bW\b(?!(?:\w|est))': '西',
    }
    # 国家/城市
    for en, zh in sorted(COUNTRY_ZH.items(), key=lambda x: -len(x[0])):
        if en in place:
            place = place.replace(en, zh)
    # 方向（用正则避免误改城市名片段）
    for pat, zh in dir_map.items():
        place = re.sub(pat, zh, place)
    # 单位
    place = re.sub(r'(\d+)\s*km', r'\1公里', place)
    # 清理
    place = re.sub(r'[,，]+', ' ', place)
    place = re.sub(r'\s+', ' ', place).strip()
    # 去掉末尾多余的方向词
    place = re.sub(r'(北|南|东|西|西北|东南|西南|东北|北西北|南东南|西南偏南|东南偏东|西北偏西|东北偏东)\s*$', '', place)
    place = re.sub(r'\s+', ' ', place).strip()
    return place

def zh_gdacs_title(title):
    """中文化GDACS标题"""
    if not title:
        return title
    # 灾害类型
    for en, zh in sorted(DISASTER_ZH.items(), key=lambda x: -len(x[0])):
        title = title.replace(en, zh)
    # 国家
    for en, zh in sorted(COUNTRY_ZH.items(), key=lambda x: -len(x[0])):
        title = title.replace(en, zh)
    # 单位
    title = re.sub(r'Magnitude\s*([\d.]+)M', r'震级\1级', title)
    title = re.sub(r'Depth:([\d.]+)km', r'深度:\1公里', title)
    title = re.sub(r'(\d+)\s*thousand', r'\1千', title)
    title = re.sub(r'MMI>=(\w+)', r'烈度≥\1级', title)
    title = title.replace("km/h", "公里/小时")
    title = title.replace("notification", "警报").replace("alert", "警报")
    title = title.replace("Population affected by Category", "受影响人口（等级")
    title = title.replace("wind speeds or higher is", "及以上风速）")
    title = title.replace("[unknown]", "未知")
    title = title.replace("Category", "等级")
    # 去掉 in 和 UTC
    title = re.sub(r'\bin\b', '', title)
    title = re.sub(r'\bUTC\b', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    # 去掉末尾逗号和多余空格
    title = title.rstrip(',;')
    return title.strip()

def time_cn(utc_str):
    """UTC时间转中文"""
    if not utc_str:
        return ""
    try:
        dt = datetime.strptime(utc_str, "%a, %d %b %Y %H:%M:%S %Z")
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return utc_str

# ============================================================
# 1. 🌍 自然灾害 - USGS 地震
# ============================================================
def fetch_earthquakes():
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
    data = json.loads(safe_fetch(url))
    items = []
    for f in data.get("features", [])[:20]:
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [])
        place_cn = zh_place(props.get("place", ""))
        items.append({
            "magnitude": props.get("mag"),
            "place": place_cn,
            "time": datetime.fromtimestamp(props.get("time", 0)/1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "depth_km": round(coords[2], 1) if len(coords) > 2 else None,
            "url": props.get("url"),
            "tsunami": props.get("tsunami", 0)
        })
    return items

# ============================================================
# 1. 🌍 自然灾害 - GDACS 全球灾害
# ============================================================
def fetch_gdacs():
    url = "https://www.gdacs.org/xml/rss.xml"
    raw = safe_fetch(url)
    items = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(raw)
        for item in root.findall(".//item")[:15]:
            title = zh_gdacs_title(item.findtext("title", ""))
            desc = item.findtext("description", "")
            items.append({
                "title": title.strip(),
                "description": desc.strip(),
                "link": item.findtext("link", "").strip(),
                "pubDate": time_cn(item.findtext("pubDate", "")),
            })
    except:
        items.append({"error": "GDACS 解析失败"})
    return items

# ============================================================
# 1. 🌍 自然灾害 - 台风/热带气旋
# ============================================================
def fetch_typhoon():
    url = "https://www.nhc.noaa.gov/rss/atpac.xml"
    raw = safe_fetch(url)
    items = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(raw)
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title", "")
            title = zh_place(title)
            title = title.replace("Hurricane", "飓风").replace("Tropical Storm", "热带风暴")
            title = re.sub(r'(\d+) mph', r'\1 英里/时', title)
            title = re.sub(r'Winds (\d+)', r'风速 \1', title)
            items.append({
                "title": title.strip(),
                "description": item.findtext("description", "").strip(),
                "link": item.findtext("link", "").strip(),
                "pubDate": time_cn(item.findtext("pubDate", "")),
            })
    except:
        pass
    return items

# ============================================================
# 2. 🦠 疫情 - WHO 新闻RSS
# ============================================================
def fetch_disease():
    """WHO疾病爆发新闻"""
    url = "https://www.who.int/rss/feature/disease-outbreak-news.xml"
    raw = safe_fetch(url)
    items = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(raw)
        for entry in root.findall(".//item")[:20]:
            title = entry.findtext("title", "")
            link = entry.findtext("link", "")
            pubdate = entry.findtext("pubDate", "")
            items.append({
                "title": title.strip(),
                "link": link.strip(),
                "published": time_cn(pubdate),
            })
    except:
        items.append({"error": "WHO 疫情源解析失败"})
    return items

# ============================================================
# 3. 📊 市场行情 - 汇率
# ============================================================
FX_LABELS = {
    "USD/CNY": "美元/人民币",
    "EUR/USD": "欧元/美元",
    "USD/JPY": "美元/日元",
    "EUR/CNY": "欧元/人民币",
    "GBP/USD": "英镑/美元",
}

def fetch_forex():
    """ExchangeRate-API 免费汇率（无需key，每日1500次免费）"""
    items = []
    # 以USD为基础货币，一次性获取所有需要的汇率
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    data = json.loads(safe_fetch(url))
    rates = data.get("rates", {})
    usd_cny = rates.get("CNY")
    usd_jpy = rates.get("JPY")
    usd_gbp = rates.get("GBP")
    usd_eur = rates.get("EUR")
    
    # USD/CNY
    items.append({"pair": "美元/人民币", "rate": round(usd_cny, 4) if usd_cny else None, "date": data.get("date", "")})
    # EUR/USD = 1 / (USD/EUR)
    if usd_eur:
        items.append({"pair": "欧元/美元", "rate": round(1.0/usd_eur, 4), "date": data.get("date", "")})
    else:
        items.append({"pair": "欧元/美元", "rate": None, "date": data.get("date", "")})
    # USD/JPY
    items.append({"pair": "美元/日元", "rate": round(usd_jpy, 2) if usd_jpy else None, "date": data.get("date", "")})
    # EUR/CNY
    if usd_eur and usd_cny:
        items.append({"pair": "欧元/人民币", "rate": round(usd_cny/usd_eur, 4), "date": data.get("date", "")})
    else:
        items.append({"pair": "欧元/人民币", "rate": None, "date": data.get("date", "")})
    # GBP/USD = 1 / (USD/GBP)
    if usd_gbp:
        items.append({"pair": "英镑/美元", "rate": round(1.0/usd_gbp, 4), "date": data.get("date", "")})
    else:
        items.append({"pair": "英镑/美元", "rate": None, "date": data.get("date", "")})
    return items

# ============================================================
# 3. 📊 市场行情 - 国债收益率
# ============================================================
def fetch_bond_yields():
    url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv"
    raw = safe_fetch(url)
    items = []
    try:
        lines = raw.strip().split("\n")
        if len(lines) > 1:
            headers = lines[0].split(",")
            data = lines[-1].split(",")
            item = {}
            label_map = {
                "Date": "日期",
                "2 Yr": "2年期",
                "3 Yr": "3年期",
                "5 Yr": "5年期",
                "7 Yr": "7年期",
                "10 Yr": "10年期",
                "20 Yr": "20年期",
                "30 Yr": "30年期"
            }
            for i, h in enumerate(headers):
                if i < len(data):
                    key = label_map.get(h.strip(), h.strip())
                    item[key] = data[i].strip()
            items.append(item)
    except:
        items.append({"error": "国债数据解析失败"})
    return items

# ============================================================
# 4. 📰 行业新闻 - 半导体 + 中文RSS
# ============================================================
def fetch_semiconductor_news():
    # 中文半导体新闻源
    sources = [
        ("电子工程专辑", "https://www.eet-china.com/rss.xml"),
        ("EET Asia", "https://www.eetasia.com/feed"),
        ("SemiWiki", "https://semiwiki.com/feed/"),
    ]
    items = []
    for name, feed_url in sources:
        raw = safe_fetch(feed_url)
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(raw)
            for entry in root.findall(".//item")[:5]:
                title = entry.findtext("title", "")
                link = entry.findtext("link", "")
                pubdate = entry.findtext("pubDate", "")
                items.append({
                    "source": name,
                    "title": title.strip(),
                    "link": link.strip(),
                    "pubDate": time_cn(pubdate),
                })
        except:
            continue
    return items

# ============================================================
# 5. 📰 中国政策 - 工信部
# ============================================================
def fetch_china_policy():
    """工信部RSS + 决策杂志"""
    sources = [
        ("工信部", "https://www.miit.gov.cn/rss/gyhxxh.xml"),
    ]
    items = []
    for name, url in sources:
        raw = safe_fetch(url)
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(raw)
            for item in root.findall(".//item")[:10]:
                items.append({
                    "source": name,
                    "title": item.findtext("title", "").strip(),
                    "link": item.findtext("link", "").strip(),
                    "pubDate": time_cn(item.findtext("pubDate", "")),
                })
        except:
            continue
    # 如果工信部挂了，给个替代提示
    if not items:
        items = [{"error": "工信部RSS暂不可用"}]
    return items

# ============================================================
# 6. 🏭 竞品动态 - 用中文搜索
# ============================================================
COMPETITOR_ZH = {
    "Texas Instruments": "德州仪器(TI)",
    "NXP": "恩智浦(NXP)",
    "Infineon": "英飞凌",
    "STMicroelectronics": "意法半导体(ST)",
    "Analog Devices": "亚德诺(ADI)",
    "Renesas": "瑞萨",
    "Microchip": "微芯科技(Microchip)",
}

def fetch_competitor_news():
    """Google News RSS 中文搜索"""
    competitors = [
        ("Texas Instruments", "Texas+Instruments"),
        ("NXP", "NXP+semiconductor"),
        ("Infineon", "Infineon"),
        ("STMicroelectronics", "STMicroelectronics"),
        ("Analog Devices", "Analog+Devices"),
        ("Renesas", "Renesas"),
        ("Microchip", "Microchip+Technology"),
    ]
    items = []
    for name, q in competitors:
        zh_name = COMPETITOR_ZH.get(name, name)
        # 用中文搜索
        url = f"https://news.google.com/rss/search?q={q}+semiconductor&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        raw = safe_fetch(url)
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(raw)
            for entry in root.findall(".//item")[:3]:
                title = entry.findtext("title", "")
                link = entry.findtext("link", "")
                pubdate = entry.findtext("pubDate", "")
                items.append({
                    "keyword": zh_name,
                    "title": title.strip(),
                    "link": link.strip(),
                    "pubDate": time_cn(pubdate),
                })
        except:
            continue
    return items

# ============================================================
# 主函数
# ============================================================
def main():
    print(f"🔄 [{today}] 开始抓取风险日报数据（中文版）...")

    results["categories"]["earthquake"] = fetch_earthquakes()
    print(f"  ✅ 地震: {len(results['categories']['earthquake'])} 条")

    results["categories"]["gdacs"] = fetch_gdacs()
    print(f"  ✅ 全球灾害: {len(results['categories']['gdacs'])} 条")

    results["categories"]["typhoon"] = fetch_typhoon()
    print(f"  ✅ 热带气旋: {len(results['categories']['typhoon'])} 条")

    results["categories"]["disease"] = fetch_disease()
    print(f"  ✅ 疫情: {len(results['categories']['disease'])} 条")

    results["categories"]["forex"] = fetch_forex()
    print(f"  ✅ 汇率: {len(results['categories']['forex'])} 条")

    results["categories"]["bond_yields"] = fetch_bond_yields()
    print(f"  ✅ 国债收益率: {len(results['categories']['bond_yields'])} 条")

    results["categories"]["semiconductor_news"] = fetch_semiconductor_news()
    print(f"  ✅ 半导体新闻: {len(results['categories']['semiconductor_news'])} 条")

    results["categories"]["china_policy"] = fetch_china_policy()
    print(f"  ✅ 中国政策: {len(results['categories']['china_policy'])} 条")

    results["categories"]["competitor_news"] = fetch_competitor_news()
    print(f"  ✅ 竞品动态: {len(results['categories']['competitor_news'])} 条")

    outpath = os.path.join(OUTPUT_DIR, "data.json")
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 数据已写入: {outpath}")
    print(f"📊 共 {sum(len(v) for v in results['categories'].values())} 条记录")

if __name__ == "__main__":
    main()
