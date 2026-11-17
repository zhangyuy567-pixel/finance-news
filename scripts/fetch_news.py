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
SOURCES = [
    {"name": "FT中文网", "url": "https://www.ftchinese.com/rss/news", "lang": "zh"},
    {"name": "CNBC 财经", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", "lang": "en"},
    {"name": "CNBC 头条", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "lang": "en"},
    {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories/", "lang": "en"},
    {"name": "BBC 商业", "url": "https://feeds.bbci.co.uk/news/business/rss.xml", "lang": "en"},
    {"name": "Yahoo 财经", "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US", "lang": "en"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FinanceNewsBot/1.0"}

# ---------- 分类关键词(中英双语) ----------
CATEGORIES = {
    "宏观政策": ["央行", "降息", "加息", "通胀", "GDP", "财政", "货币政策", "美联储", "fed", "inflation", "rate cut", "rate hike", "central bank", "fomc", "powell", "stimulus", "tariff", "关税", "发改委", "国常会", "政策"],
    "股市": ["A股", "沪指", "深成指", "创业板", "科创板", "北交所", "st股", "涨停", "券商", "stock market", "s&p", "nasdaq", "dow jones", "shares rally", "shares fall", "ipo", "上证", "深证", "恒生"],
    "美股全球": ["美股", "道琼斯", "纳斯达克", "标普", "欧股", "日经", "恒指", "wall street", "s&p 500", "nasdaq", "dow", "global market", "europe stocks", "asia stocks"],
    "基金理财": ["基金", "ETF", "公募", "私募", "理财", "养老金", "QDII", "fund", "etf", "pension", "wealth", "bond yield", "国债", "债券"],
    "外汇黄金": ["汇率", "人民币", "美元", "欧元", "日元", "黄金", "白银", "原油", "比特币", "dollar", "yuan", "euro", "gold", "silver", "oil price", "bitcoin", "crypto", "forex"],
    "科技公司": ["苹果", "英伟达", "特斯拉", "微软", "谷歌", "Meta", "AI", "芯片", "半导体", "apple", "nvidia", "tesla", "microsoft", "google", "openai", "anthropic", "chip", "semiconductor", "startup", "财报", "earnings"],
}

def clean_html(raw: str) -> str:
    if not raw:
        return ""
    soup = BeautifulSoup(raw, "html.parser")
    text = soup.get_text(" ", strip=True)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]

def classify(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in text:
                return cat
    return "综合"

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
    for e in feed.entries[:40]:
        title = html.unescape((e.get("title") or "").strip())
        if not title:
            continue
        link = (e.get("link") or "").strip()
        summary = clean_html(e.get("summary") or e.get("description") or "")
        pub = parse_time(e)
        image = ""
        try:
            media = e.get("media_thumbnail") or e.get("media_content")
            if media and isinstance(media, list) and media[0].get("url"):
                image = media[0]["url"]
        except Exception:
            pass
        items.append({
            "title": title,
            "link": link,
            "summary": summary,
            "source": src["name"],
            "lang": src["lang"],
            "category": classify(title, summary),
            "published_at": pub,
            "image": image,
        })
    print(f"  获得 {len(items)} 条")
    return items

def main():
    all_items = []
    for src in SOURCES:
        all_items.extend(fetch_source(src))

    # 去重(按链接和标题)
    seen = set()
    unique = []
    for it in all_items:
        key = (it["link"] or it["title"][:60]).lower()
        if key in seen or not it["link"]:
            continue
        seen.add(key)
        unique.append(it)

    # 按时间倒序
    unique.sort(key=lambda x: x["published_at"], reverse=True)
    unique = unique[:150]

    now = datetime.now(BEIJING)
    payload = {
        "updated_at": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "count": len(unique),
        "sources": [s["name"] for s in SOURCES],
        "items": unique,
    }

    # 合并历史(保留当天已有的、防止覆盖丢失)
    out_latest = DATA_DIR / "news.json"
    if out_latest.exists():
        try:
            old = json.loads(out_latest.read_text(encoding="utf-8"))
            old_links = {i.get("link") for i in unique}
            for i in old.get("items", []):
                if i.get("link") not in old_links and i.get("published_at", "")[:10] == now.strftime("%Y-%m-%d"):
                    unique.append(i)
            unique.sort(key=lambda x: x["published_at"], reverse=True)
            payload["items"] = unique[:150]
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
