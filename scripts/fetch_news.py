#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日财经新闻收集脚本
用法:
    pip install -r requirements.txt
    python scripts/fetch_news.py

功能:
- 从多个 RSS 源抓取财经新闻(中文+英文)
- 自动分类、去重、清洗
- 生成 data/news.json (最新) + data/history/YYYY-MM-DD.json (归档)
- 可配合 GitHub Actions 每天定时运行,实现"每天自动收集"
"""
import json
import re
import os
import sys
import html
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import feedparser
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("请先安装依赖: pip install -r requirements.txt")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
HISTORY_DIR = DATA_DIR / "history"
DATA_DIR.mkdir(exist_ok=True)
HISTORY_DIR.mkdir(exist_ok=True)

BEIJING = timezone(timedelta(hours=8))

# ---------- RSS 数据源(稳定可用,可自行增删) ----------
# limit: 每个源最多取用条数(太多源时防止某一源淹没首页)
SOURCES = [
    # ---- 中国市场(中文) ----
    {"name": "人民币汇率", "url": "https://news.google.com/rss/search?q=%E4%BA%BA%E6%B0%91%E5%B8%81+%E6%B1%87%E7%8E%87&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans", "lang": "zh", "limit": 10},
    {"name": "新能源汽车", "url": "https://news.google.com/rss/search?q=%E6%96%B0%E8%83%BD%E6%BA%90%E6%B1%BD%E8%BD%A6&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans", "lang": "zh", "limit": 10},
    {"name": "FT中文网", "url": "https://www.ftchinese.com/rss/news", "lang": "zh", "limit": 20},
    {"name": "上证指数", "url": "https://news.google.com/rss/search?q=%E4%B8%8A%E8%AF%81%E6%8C%87%E6%95%B0&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans", "lang": "zh", "limit": 12},
    {"name": "港股", "url": "https://news.google.com/rss/search?q=%E6%B8%AF%E8%82%A1&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans", "lang": "zh", "limit": 12},
    {"name": "央行货币", "url": "https://news.google.com/rss/search?q=%E5%A4%AE%E8%A1%8C%20%E9%99%8D%E5%87%86&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans", "lang": "zh", "limit": 10},
    {"name": "楼市地产", "url": "https://news.google.com/rss/search?q=%E6%88%BF%E5%9C%B0%E4%BA%A7%20%E6%94%BF%E7%AD%96&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans", "lang": "zh", "limit": 10},
    {"name": "中国科技股", "url": "https://news.google.com/rss/search?q=%E7%A7%91%E6%8A%80%E8%82%A1&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans", "lang": "zh", "limit": 12},
    {"name": "黄金", "url": "https://news.google.com/rss/search?q=%E9%BB%84%E9%87%91%E4%BB%B7%E6%A0%BC&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans", "lang": "zh", "limit": 12},
    {"name": "医药股", "url": "https://news.google.com/rss/search?q=%E5%8C%BB%E8%8D%AF+%E8%82%A1&hl=zh-CN&gl=CN&ceid=CN%3Azh-Hans", "lang": "zh", "limit": 10},
    {"name": "SCMP中国", "url": "https://www.scmp.com/rss/4/feed", "lang": "en", "limit": 15},
    # ---- 全球市场 ----
    {"name": "CNBC 财经", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", "lang": "en", "limit": 25},
    {"name": "CNBC 头条", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "lang": "en", "limit": 25},
    {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories/", "lang": "en", "limit": 10},
    {"name": "BBC 商业", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "lang": "en", "limit": 25},
    {"name": "Yahoo 财经", "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US", "lang": "en", "limit": 20},
    {"name": "SCMP环球", "url": "https://www.scmp.com/rss/12/feed", "lang": "en", "limit": 10},
]

MAX_ITEMS = 200  # 首页最多保留条数

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FinanceNewsBot/1.0"}

# ---------- 非财经内容黑名单(标题命中任一即剔除,每天自动过滤) ----------
# 覆盖:娱乐八卦 / 生活方式 / 纯科技玩机 / 交通出行 / 家庭情感问答 / 战争灾难直击(无市场角度)等
EXCLUDE_KEYWORDS = [
    # 娱乐八卦
    "james bond", "pattinson", "oscars", "grammy", "taylor swift", "box office", "票房",
    "明星", "绯闻", "恋情", "离婚", "出轨",  # 注意:仅标题含这些词且无财经上下文时才剔除,见 is_valid()
    # 生活方式 / 玩机 / 健康
    "advent calendar", "haunted", "housefishing", "heat pump", "video game remake",
    "remakes tap", "stealthier drones", "cold cases", "for translation", "living with a stink",
    "grads ditching", "managing ai - but", "indian workers filming", "engine parts that",
    "ghost", "horoscope", "recipe", "食谱", " haunted", "闹鬼", "星座运势",
    # 交通出行(无市场角度)
    "flight delays linger", "we slept here", "flight delays", "航班延误", "system outage that delayed flights",
    "resolves system outage", "ground stop", "afford a house alone", "black friday scam",
    "kremlin", "南方财经全媒体集团",
    # 家庭情感问答(非新闻)
    "is he being fair", "should i be worried", "sour taste", "calls my plans a fantasy",
    # 战争灾难直击(无市场角度)
    "空袭加沙医院", "airstrike on gaza hospital", "airstrike hospital",
    # 天气奇观 / 工具页(非新闻)
    "极地涡旋", "polar vortex", "use our look-up", "look-up to find out",
    # 纯政治(无财经角度)
    "奥卡西奥", "ocasio-cortez", "印尼副总统", "burnham says", "win-win' deal can be agreed",
    "挑选一名代表参与", "星盾限速", "starshield", "mine hunting", "robot vessels",
]

# 标题含这些词时,即使命中上面个别词也不剔除(财经上下文优先)
FINANCE_KEEP_KEYWORDS = [
    "stock", "market", "ipo", "earnings", "investor", "fund", "bank", "fed", "rate",
    "inflation", "gdp", "trade", "tariff", "oil", "gold", "bond", "etf", "crypto",
    "股市", "股价", "财报", "美联储", "央行", "通胀", "加息", "降息", "基金", "银行",
    "石油", "黄金", "债券", "上市", "并购", "财报", "关税", "贸易", "经济",
]

# ---------- 分类纠偏(优先于通用关键词,解决错分类) ----------
# 格式: (分类, [关键词])
CATEGORY_OVERRIDES = [
    ("外汇黄金", ["hormuz", "霍尔木兹", "strait", "海峡", "crude oil", "原油", "oil price", "油价", "opec",
                "jackdaw", "gas starts flowing", "oil prices rise", "石油产量", "天然气"]),
    ("宏观政策", ["slowdown deepens", "industrial output", "retail sales", "investment miss",
                "中国经济放缓", "national insurance", "job support", "milburn", "job support for young",
                "离岸信托", "偷逃税", "申报缴税", "增税", "property tax revolt", "property tax",
                "october 2027 meeting", "no vote on interest rates", "october session"]),
    ("基金理财", ["nft", "lesson for investors", "boom and bust", "risky investments",
                "retirement", "pension", "退休", "养老", "coreweave", "bond yield", "credit stress",
                "credit card", "yield tops"]),
    ("股市", ["review & preview", "premarket", "chart resistance", "correction territory",
            "takeover approach", "telecom map", "proxy play", "premarket"]),
    ("综合", ["banking", "consumer banking", "software bug", "service outages at major us banks",
            "goldman", "ai financing", "nike and lululemon", "china connection",
            "toys find their way", "christmas rush", "china-made toys"]),
]

# ---------- 一级:地区(中国 / 全球) ----------
CHINA_MARKERS = [
    "中国", "华尔街见闻", "A股", "港股", "恒指", "恒生", "沪指", "深成", "创业板", "科创板",
    "北交所", "上证", "深证", "人民币", "港元", "港币", "香港", "上海", "深圳", "北京",
    "广州", "杭州", "中央", "国务院", "发改委", "人民银行", "证监会", "银保监", "金融监管",
    "国常会", "两会", "楼市", "内地", "中概", "中资", "沪深", "北向资金", "南向资金",
    "台股", "台积电", "台湾", "澳门", "海南", "粤港澳", "长三角", "京津冀",
    "china", "chinese", "beijing", "shanghai", "shenzhen", "hong kong", "hongkong",
    "taiwan", "tsmc", "yuan", "renminbi", "alibaba", "tencent", "byd", "baidu", "xiaomi",
    "a-share", "hang seng", "mainland", "xi jinping", "huawei",
]
GLOBAL_MARKERS = [
    "美国", "美联储", "欧洲", "欧盟", "英国", "日本", "德国", "法国", "意大利", "印度",
    "韩国", "新加坡", "澳洲", "澳大利亚", "加拿大", "巴西", "俄罗斯", "中东", "白宫",
    "华尔街", "道琼斯", "纳斯达克", "标普", "欧股", "日经",
    "u.s.", "america", "white house", "wall street", "europe", "britain", "germany",
    "france", "japan", "india", "korea", "singapore", "australia", "canada", "fed",
    "ecb", "boj", "bank of england", "nasdaq", "dow jones", "s&p", "ftse", "nikkei",
]

# ---------- 二级:板块(顺序即优先级,专指板块先于综合板块) ----------
# 每个板块: (板块名, [关键词])
SECTORS = [
    ("贵金属", ["黄金", "白银", "铂金", "钯金", "金价", "银价", "金饰", "现货黄金", "伦敦金",
               "gold", "silver", "platinum", "palladium", "bullion"]),
    ("能源", ["原油", "石油", "天然气", "页岩油", "汽油", "柴油", "煤炭", "opec", "欧佩克",
             "oil", "crude", "natural gas", "gasoline", "diesel", "coal", "shale",
             "光伏", "solar", "风电", "wind power", "储能", "锂矿", "lithium",
             "矿产", "稀土", "铜", "mineral", "rare earth", "copper"]),
    ("房地产", ["房地产", "楼市", "房价", "购房", "首付", "房贷", "按揭", "物业", "恒大", "碧桂园",
               "万科", "保利", "融创", "property", "real estate", "housing", "homeowner",
               "mortgage", "evergrande", "country garden"]),
    ("汽车出行", ["汽车", "新能源车", "电动车", "比亚迪", "蔚来", "理想", "小鹏", "小米汽车",
                 "宁德时代", "动力电池", "tesla", "byd", "nio", "xpeng", "catl", "electric vehicle",
             "上汽", "广汽", "吉利", "长城", "奇瑞", "新能源"]),
    ("医疗健康", ["医药", "医疗", "生物", "疫苗", "制药", "药企", "医院", "医保", "集采", "创新药",
                 "减肥药", "pharma", "biotech", "healthcare", "vaccine", "drug", "fda", "lilly", "novo"]),
    ("科技", ["科技", "科网", "tech", "AI", "人工智能", "芯片", "半导体", "英伟达", "苹果", "微软", "谷歌", "亚马逊",
             "特斯拉", "Meta", "OpenAI", "Anthropic", "华为", "小米", "中芯", "寒武纪",
             "机器人", "互联网", "电商", "阿里", "百度", "腾讯", "京东", "拼多多",
             "apple", "nvidia", "microsoft", "google", "amazon", "openai", "anthropic",
             "chip", "semiconductor", "startup", "cloud", "软件", "software",
             "huawei", "xiaomi", "alibaba", "tencent", "baidu"]),
    ("股市", ["A股", "港股", "股市", "指数", "收盘", "收评", "开盘", "涨停", "跌停", "牛市", "熊市",
             "熔断", "上市", "IPO", "退市", "券商", "北向", "南向", "恒指", "沪指", "深成",
             "创业板", "科创板", "stock", "shares", "nasdaq", "dow", "s&p", "ipo", "listing",
             "premarket", "correction", "rally", "sell-off"]),
    ("基金理财", ["基金", "ETF", "公募", "私募", "理财", "养老", "退休", "年金", "信托", "资管",
                 "QDII", "REITs", "fund", "etf", "pension", "retirement", "bond", "债券",
                 "国债", "yield", "收益率", "分红", "回购", "buyback"]),
    ("宏观政策", ["央行", "美联储", "降息", "加息", "降准", "通胀", "GDP", "CPI", "PPI", "PMI",
                 "货币", "财政", "关税", "贸易", "政策", "逆回购", "MLF", "LPR", "社融", "信贷",
                 "fed", "inflation", "rate", "central bank", "tariff", "trade", "gdp", "stimulus",
                 "easing", "tightening", "hike", "cut", "fomc", "forex", "汇率", "中间价",
                 "summit", "apec", "峰会", "会晤", "会谈", "关税战", "贸易战"]),
]


_SHORT_WORD_RE = {}


def kw_hit(kw: str, text: str) -> bool:
    """短英文词(如 AI/Fed/UK/oil/gas)用单词边界匹配,防止 said/chair/soil 误命中."""
    kl = kw.lower()
    if len(kl) <= 4 and kl.isascii() and kl.isalpha():
        pat = _SHORT_WORD_RE.get(kl)
        if pat is None:
            pat = re.compile(r"\b" + re.escape(kl) + r"\b")
            _SHORT_WORD_RE[kl] = pat
        return bool(pat.search(text))
    return kl in text


def detect_region(title: str, summary: str, lang: str) -> str:
    text = f"{title} {summary}".lower()
    for kw in CHINA_MARKERS:
        if kw_hit(kw, text):
            return "中国"
    for kw in GLOBAL_MARKERS:
        if kw_hit(kw, text):
            return "全球"
    return "中国" if lang == "zh" else "全球"


def detect_sector(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    # 1)纠偏规则优先
    for cat, keywords in CATEGORY_OVERRIDES:
        for kw in keywords:
            if kw_hit(kw, text):
                # 兼容旧纠偏表:映射到新板块
                return _map_old_category(cat)
    # 2)板块关键词按优先级匹配
    for sector, keywords in SECTORS:
        for kw in keywords:
            if kw_hit(kw, text):
                return sector
    return "综合"


def _map_old_category(old: str) -> str:
    return {"外汇黄金": "贵金属", "股市": "股市", "基金理财": "基金理财",
            "宏观政策": "宏观政策", "科技公司": "科技", "综合": "综合",
            "美股全球": "股市"}.get(old, "综合")


def classify(title: str, summary: str, lang: str = "en") -> tuple:
    """返回 (地区, 板块).兼容旧调用:classify(t, s) 仍可用,默认英文."""
    region = detect_region(title, summary, lang)
    sector = detect_sector(title, summary)
    return region, sector

def clean_html(raw: str) -> str:
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(" ", strip=True)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]

def is_valid(title: str, summary: str) -> bool:
    """黑名单过滤:命中非财经词且无财经上下文 -> 剔除."""
    text = f"{title} {summary}".lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in text:
            # 有明确财经上下文则保留(如"股价因绯闻下跌"不算纯八卦)
            keep = any(k.lower() in text for k in FINANCE_KEEP_KEYWORDS)
            if not keep:
                return False
    return True


def norm_title(t: str) -> str:
    t = t.lower()
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff ]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def is_duplicate(a: str, b: str) -> bool:
    """跨源同一事件去重:标题相似度>0.82 视为重复."""
    if not a or not b:
        return False
    if a == b:
        return True
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return False
    jaccard = len(sa & sb) / max(1, len(sa | sb))
    if max(len(a), len(b)) < 60:
        return jaccard > 0.75
    return jaccard > 0.62

def parse_time(entry) -> str:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                dt = datetime(*t[:6], tzinfo=timezone.utc).astimezone(BEIJING)
                return dt.isoformat()
            except Exception:
                pass
    return datetime.now(BEIJING).isoformat()

def fetch_source(src):
    print(f"抓取 {src['name']} ...")
    try:
        r = requests.get(src["url"], headers=HEADERS, timeout=20)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
    except Exception as e:
        print(f"  失败: {e}")
        return []
    items = []
    limit = src.get("limit", 30)
    for e in feed.entries[:limit]:
        title = html.unescape((e.get("title") or "").strip())
        if not title:
            continue
        link = (e.get("link") or "").strip()
        summary = clean_html(e.get("summary") or e.get("description") or "")
        # Google 新闻条目自带来源后缀" - XX网",拆出来更干净
        if " - " in title and ("google" in src["url"]):
            title, _, outlet = title.rpartition(" - ")
            if outlet:
                summary = f"（来源：{outlet.strip()}）" + (f" {summary}" if summary else "")
        pub = parse_time(e)
        image = ""
        try:
            media = e.get("media_thumbnail") or e.get("media_content")
            if media and isinstance(media, list) and media[0].get("url"):
                image = media[0]["url"]
        except Exception:
            pass
        region, sector = classify(title, summary, src["lang"])
        items.append({
            "title": title,
            "link": link,
            "summary": summary,
            "source": src["name"],
            "lang": src["lang"],
            "region": region,
            "sector": sector,
            "category": f"{region}·{sector}",
            "published_at": pub,
            "image": image,
        })
    print(f"  获得 {len(items)} 条")
    return items

def main():
    all_items = []
    for src in SOURCES:
        all_items.extend(fetch_source(src))

    # 质量过滤:先剔除非财经内容
    valid_items = [it for it in all_items if is_valid(it["title"], it.get("summary", ""))]
    print(f"质量过滤: {len(all_items)} -> {len(valid_items)} (剔除 {len(all_items) - len(valid_items)} 条非财经/低质)")
    all_items = valid_items

    # 去重(按链接 + 标题相似度跨源去重)
    seen_links = set()
    seen_titles = []
    unique = []
    for it in all_items:
        if not it["link"]:
            continue
        lk = it["link"].lower()
        if lk in seen_links:
            continue
        nt = norm_title(it["title"])
        if any(is_duplicate(nt, t) for t in seen_titles):
            print(f"  去重: {it['title'][:60]}...")
            continue
        seen_links.add(lk)
        seen_titles.append(nt)
        unique.append(it)

    # 按时间倒序
    unique.sort(key=lambda x: x["published_at"], reverse=True)
    unique = unique[:MAX_ITEMS]

    now = datetime.now(BEIJING)
    payload = {
        "updated_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "count": len(unique),
        "sources": [s["name"] for s in SOURCES],
        "items": unique,
    }

    # 合并历史(保留当天已有的、防止覆盖丢失;旧分类迁移到新体系)
    out_latest = DATA_DIR / "news.json"
    if out_latest.exists():
        try:
            old = json.loads(out_latest.read_text(encoding="utf-8"))
            old_links = {i.get("link") for i in unique}
            for i in old.get("items", []):
                if i.get("link") not in old_links and i.get("published_at", "")[:10] == now.strftime("%Y-%m-%d"):
                    if "region" not in i or "sector" not in i:
                        r, s = classify(i.get("title", ""), i.get("summary", ""), i.get("lang", "en"))
                        i["region"], i["sector"], i["category"] = r, s, f"{r}·{s}"
                    unique.append(i)
            unique.sort(key=lambda x: x["published_at"], reverse=True)
            payload["items"] = unique[:MAX_ITEMS]
            payload["count"] = len(payload["items"])
        except Exception as e:
            print("合并历史失败:", e)

    out_latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    date_file = HISTORY_DIR / f"{now.strftime('%Y-%m-%d')}.json"
    date_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 清理 60 天前的归档
    for f in HISTORY_DIR.glob("*.json"):
        try:
            d = datetime.strptime(f.stem, "%Y-%m-%d")
            if (now.replace(tzinfo=None) - d).days > 60:
                f.unlink()
        except Exception:
            pass

    print(f"\n完成!共 {payload['count']} 条,已写入 {out_latest} 和 {date_file}")

if __name__ == "__main__":
    main()
