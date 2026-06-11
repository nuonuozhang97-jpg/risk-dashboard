#!/usr/bin/env python3
"""
全球风险日报数据抓取脚本
每天定时运行，聚合6大类风险数据输出为JSON
输出: /site/data.json
"""

import json
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timezone, timedelta
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")
os.makedirs(OUTPUT_DIR, exist_ok=True)

ctx = ssl.create_default_context()
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

results = {
    "date": today,
    "updated_at": datetime.now(timezone.utc).isoformat(),
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
# 1. 🌍 自然灾害 - USGS 地震 (过去24小时 M4.5+)
# ============================================================
def fetch_earthquakes():
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
    data = json.loads(safe_fetch(url))
    items = []
    for f in data.get("features", [])[:20]:
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [])
        items.append({
            "magnitude": props.get("mag"),
            "place": props.get("place"),
            "time": datetime.fromtimestamp(props.get("time", 0)/1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "depth_km": round(coords[2], 1) if len(coords) > 2 else None,
            "url": props.get("url"),
            "tsunami": props.get("tsunami", 0)
        })
    return items

# ============================================================
# 1. 🌍 自然灾害 - GDACS 全球灾害预警 (火山/洪水/台风)
# ============================================================
def fetch_gdacs():
    """GDACS RSS feed 解析"""
    url = "https://www.gdacs.org/xml/rss.xml"
    raw = safe_fetch(url)
    items = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(raw)
        for item in root.findall(".//item")[:15]:
            title = item.findtext("title", "")
            desc = item.findtext("description", "")
            link = item.findtext("link", "")
            pubdate = item.findtext("pubDate", "")
            items.append({
                "title": title.strip(),
                "description": desc.strip(),
                "link": link.strip(),
                "pubDate": pubdate.strip()
            })
    except:
        items.append({"error": "GDACS RSS parse failed"})
    return items

# ============================================================
# 1. 🌍 自然灾害 - 台风 (JTWC / 日本气象厅)
# ============================================================
def fetch_typhoon():
    """从 Digital Typhoon 或 JTWC 获取"""
    # 使用 NOAA 热带气旋 RSS
    url = "https://www.nhc.noaa.gov/rss/atpac.xml"
    raw = safe_fetch(url)
    items = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(raw)
        for item in root.findall(".//item")[:10]:
            items.append({
                "title": item.findtext("title", "").strip(),
                "description": item.findtext("description", "").strip(),
                "link": item.findtext("link", "").strip(),
                "pubDate": item.findtext("pubDate", "").strip()
            })
    except:
        pass
    return items

# ============================================================
# 2. 🦠 疫情 - ProMED 疫情通报
# ============================================================
def fetch_promed():
    """ProMED mail RSS feed"""
    url = "https://www.promedmail.org/feed/atom/"
    raw = safe_fetch(url)
    items = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(raw)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//atom:entry", ns)[:20]:
            title = entry.findtext("atom:title", "", ns)
            link_el = entry.find("atom:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            published = entry.findtext("atom:published", "", ns)
            items.append({
                "title": title.strip(),
                "link": link.strip(),
                "published": published.strip()
            })
    except:
        items.append({"error": "ProMED parse failed"})
    return items

# ============================================================
# 3. 📊 市场行情 - 汇率
# ============================================================
def fetch_forex():
    """Frankfurter API 免费汇率"""
    pairs = ["USD/CNY", "EUR/USD", "USD/JPY", "EUR/CNY", "GBP/USD"]
    items = []
    for pair in pairs:
        from_c, to_c = pair.split("/")
        url = f"https://api.frankfurter.dev/v2/latest?base={from_c}&symbols={to_c}"
        data = json.loads(safe_fetch(url))
        rates = data.get("rates", {})
        items.append({
            "pair": pair,
            "rate": rates.get(to_c),
            "date": data.get("date", "")
        })
    return items

# ============================================================
# 3. 📊 市场行情 - 大宗商品 (IMF数据)
# ============================================================
def fetch_commodities():
    """IMF commodity price RSS/news"""
    # 主要金属和能源价格
    url = "https://www.imf.org/en/research/commodity-prices"
    raw = safe_fetch(url)
    items = []
    # IMF 页面抓取比较复杂，先放新闻聚合作为替代
    return items

# ============================================================
# 3. 📊 市场行情 - 债券收益率
# ============================================================
def fetch_bond_yields():
    """美国10年期国债收益率"""
    # 从 Treasury API 获取
    url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv"
    raw = safe_fetch(url)
    items = []
    try:
        lines = raw.strip().split("\n")
        if len(lines) > 1:
            headers = lines[0].split(",")
            data = lines[-1].split(",")
            item = {}
            for i, h in enumerate(headers):
                if i < len(data):
                    item[h.strip()] = data[i].strip()
            items.append(item)
    except:
        items.append({"error": "Treasury parse failed"})
    return items

# ============================================================
# 5. 📰 行业新闻 - 半导体行业
# ============================================================
def fetch_semiconductor_news():
    sources = [
        ("EET Asia", "https://www.eetasia.com/feed"),
        ("Semiconductor Engineering", "https://semiconductorengineering.com/feed/"),
        ("SemiWiki", "https://semiwiki.com/feed/"),
        ("AnandTech", "https://www.anandtech.com/rss"),
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
                    "pubDate": pubdate.strip()
                })
        except:
            continue
    return items

# ============================================================
# 5. 📰 行业新闻 - 中国半导体政策
# ============================================================
def fetch_china_policy():
    url = "https://www.miit.gov.cn/rss/gyhxxh.xml"
    raw = safe_fetch(url)
    items = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(raw)
        for item in root.findall(".//item")[:10]:
            items.append({
                "title": item.findtext("title", "").strip(),
                "link": item.findtext("link", "").strip(),
                "pubDate": item.findtext("pubDate", "").strip()
            })
    except:
        items.append({"error": "MIIT feed unavailable"})
    return items

# ============================================================
# 6. 🏭 竞品动态 - 新闻搜索聚合 (通过RSS)
# ============================================================
def fetch_competitor_news():
    """竞品关键词新闻抓取 - 通过Google News RSS"""
    competitors = [
        "Texas Instruments semiconductor",
        "NXP semiconductor",
        "Infineon",
        "STMicroelectronics",
        "ADI Analog Devices",
        "Renesas",
        "Microchip Technology"
    ]
    items = []
    for comp in competitors:
        q = comp.replace(" ", "%20")
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        raw = safe_fetch(url)
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(raw)
            for entry in root.findall(".//item")[:3]:
                items.append({
                    "keyword": comp,
                    "title": entry.findtext("title", "").strip(),
                    "link": entry.findtext("link", "").strip(),
                    "pubDate": entry.findtext("pubDate", "").strip()
                })
        except:
            continue
    return items

# ============================================================
# 主函数
# ============================================================
def main():
    print(f"🔄 开始抓取 {today} 风险日报数据...")

    results["categories"]["earthquake"] = fetch_earthquakes()
    print(f"  ✅ 地震: {len(results['categories']['earthquake'])} 条")

    results["categories"]["gdacs"] = fetch_gdacs()
    print(f"  ✅ 全球灾害: {len(results['categories']['gdacs'])} 条")

    results["categories"]["typhoon"] = fetch_typhoon()
    print(f"  ✅ 台风/飓风: {len(results['categories']['typhoon'])} 条")

    results["categories"]["disease"] = fetch_promed()
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

    # 输出
    outpath = os.path.join(OUTPUT_DIR, "data.json")
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 数据已写入: {outpath}")
    print(f"📊 共 {sum(len(v) for v in results['categories'].values())} 条记录")

if __name__ == "__main__":
    main()
