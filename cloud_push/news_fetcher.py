#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news_fetcher.py - 新闻采集模块
使用 RSS + 网页抓取，无需 Mac 本地工具
"""

import datetime
import json
import re
import time
import urllib.request
import urllib.error
from html.parser import HTMLParser

# ===== RSS 数据源 =====
RSS_FEEDS = [
    # CPSC 召回 RSS
    {"url": "https://www.cpsc.gov/Newsroom/RSS", "source": "CPSC", "type": "recall"},
    # FDA 食品安全 RSS
    {"url": "https://www.fda.gov/about-fda/contact-fda/feeds-rss", "source": "FDA", "type": "food_safety"},
    # 中国市场监管总局 - 通过网页抓取
    {"url": "https://www.samr.gov.cn/", "source": "SAMR", "type": "web"},
]

# ===== 关键词（中英文）=====
KEYWORDS_ZH = [
    "婴儿", "幼儿", "宝宝", "儿童", "新生儿",
    "奶瓶", "奶嘴", "餐具", "辅食", "奶粉", "食品",
    "纸尿裤", "尿布", "湿巾",
    "玩具", "文具", "童车", "推车",
    "服装", "童装", "睡袋",
    "婴儿床", "护栏", "家具",
    "安全座椅", " car seat",
    "召回", "污染", "安全", "警告", "隐患",
]

KEYWORDS_EN = [
    "infant", "baby", "toddler", "child", "newborn",
    "bottle", "nipple", "feeding", "formula", "food",
    "diaper", "wipe",
    "toy", "crib", "stroller", "car seat",
    "recall", "safety", "warning", "hazard", "contamination",
]


def fetch_url(url, timeout=15):
    """获取 URL 内容"""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; BabySafetyBot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = "utf-8"
            content_type = resp.headers.get("Content-Type", "")
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()
            return resp.read().decode(charset, errors="replace")
    except Exception as e:
        print(f"  ⚠️ 获取失败 {url[:50]}: {e}")
        return ""


def parse_rss(xml_content):
    """简单 RSS 解析（不依赖外部库）"""
    items = []
    # 匹配 <item>...</item> 或 <entry>...</entry>
    for match in re.finditer(r"<item[^>]*>(.*?)</item>", xml_content, re.DOTALL | re.IGNORECASE):
        item_xml = match.group(1)
        item = {}
        item["title"] = _extract_xml_tag(item_xml, "title")
        item["link"] = _extract_xml_tag(item_xml, "link")
        item["pub_date"] = _extract_xml_tag(item_xml, "pubDate") or _extract_xml_tag(item_xml, "published")
        item["description"] = _extract_xml_tag(item_xml, "description")
        if item["title"] or item["link"]:
            items.append(item)
    return items


def _extract_xml_tag(xml, tag):
    """从 XML 片段中提取标签内容"""
    pattern = rf"<{tag}[^>]*>(.*?)</{tag}>"
    m = re.search(pattern, xml, re.DOTALL | re.IGNORECASE)
    if m:
        content = m.group(1).strip()
        # 去除 CDATA
        content = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", content, flags=re.DOTALL)
        # 去除 HTML 标签
        content = re.sub(r"<[^>]+>", "", content)
        return content.strip()
    return ""


def is_baby_related(text):
    """判断文本是否与婴儿安全相关"""
    text_lower = text.lower()
    for kw in KEYWORDS_ZH + [k.lower() for k in KEYWORDS_EN]:
        if kw in text_lower:
            return True
    return False


def classify_severity(title, desc):
    """分类严重程度"""
    text = (title + " " + desc).lower()
    urgent_kw = ["death", "死亡", "injury", "受伤", "emergency", "immediate", "立即停止", "紧急召回"]
    for kw in urgent_kw:
        if kw in text:
            return "urgent"
    return "important"


def fetch_cpsc_recalls(days=3):
    """专门抓取 CPSC 召回（更直接的方式）"""
    items = []
    try:
        # CPSC 召回列表页面
        url = "https://www.cpsc.gov/Recalls"
        html = fetch_url(url)
        if not html:
            return items
        
        # 提取召回链接和标题
        for m in re.finditer(r'<a[^>]+href="(/Recalls/\d+/[^"]+)"[^>]*>([^<]+)</a>', html):
            link = "https://www.cpsc.gov" + m.group(1)
            title = m.group(2).strip()
            if is_baby_related(title):
                items.append({
                    "title": title,
                    "link": link,
                    "source": "CPSC",
                    "severity": classify_severity(title, ""),
                    "date": datetime.date.today().isoformat(),
                })
    except Exception as e:
        print(f"  ⚠️ CPSC 抓取失败: {e}")
    
    return items[:10]  # 最多10条


def fetch_fda_alerts():
    """抓取 FDA 安全警告"""
    items = []
    try:
        url = "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts"
        html = fetch_url(url)
        if not html:
            return items
        
        for m in re.finditer(r'<a[^>]+href="([^"]+recall[^"]*|[^"]*safety[^"]*)"[^>]*>([^<]+)</a>', html, re.IGNORECASE):
            link = m.group(1)
            if not link.startswith("http"):
                link = "https://www.fda.gov" + link
            title = m.group(2).strip()
            if is_baby_related(title):
                items.append({
                    "title": title,
                    "link": link,
                    "source": "FDA",
                    "severity": classify_severity(title, ""),
                    "date": datetime.date.today().isoformat(),
                })
    except Exception as e:
        print(f"  ⚠️ FDA 抓取失败: {e}")
    
    return items[:10]


def fetch_chinese_sources():
    """抓取中文来源（中国质量报、市场监管总局等）"""
    items = []
    
    # 尝试抓取中国质量报
    sources = [
        ("https://www.cqn.com.cn/", "中国质量报"),
        ("https://www.samr.gov.cn/xw/zj/", "市场监管总局"),
    ]
    
    for url, source_name in sources:
        try:
            html = fetch_url(url, timeout=10)
            if not html:
                continue
            # 简单提取链接
            for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*(?:婴儿|幼儿|儿童|召回|安全)[^<]*)</a>', html):
                link = m.group(1)
                title = m.group(2).strip()
                if len(title) > 10 and is_baby_related(title):
                    if not link.startswith("http"):
                        link = url.rstrip("/") + "/" + link.lstrip("/")
                    items.append({
                        "title": title,
                        "link": link,
                        "source": source_name,
                        "severity": classify_severity(title, ""),
                        "date": datetime.date.today().isoformat(),
                    })
        except Exception as e:
            print(f"  ⚠️ {source_name} 抓取失败: {e}")
    
    return items[:10]


def fetch_news(days_back=3, mode="morning"):
    """
    主函数：采集新闻
    mode: "morning" = 全天新闻, "evening" = 仅增量（与早间报告对比）
    """
    print(f"📰 开始采集新闻 (mode={mode})...")
    all_items = []
    
    # CPSC
    print("  → CPSC 召回...")
    all_items.extend(fetch_cpsc_recalls(days_back))
    
    # FDA
    print("  → FDA 安全警告...")
    all_items.extend(fetch_fda_alerts())
    
    # 中文来源
    print("  → 中文来源...")
    all_items.extend(fetch_chinese_sources())
    
    # 去重（按标题）
    seen_titles = set()
    unique_items = []
    for item in all_items:
        key = item["title"][:30]  # 前30字符作为去重key
        if key not in seen_titles:
            seen_titles.add(key)
            unique_items.append(item)
    
    print(f"  ✓ 共采集 {len(unique_items)} 条（去重后）")
    return unique_items


def format_for_report(news_items):
    """
    将采集结果格式化为报告数据结构
    返回与现有 feishu_card_v7.py URGENT_NEWS / IMPORTANT_NEWS 兼容的格式
    """
    urgent = []
    important = []
    
    for item in news_items:
        entry = {
            "title": item["title"],
            "desc": item.get("description", "")[:100] if item.get("description") else item["title"],
            "url": item["link"],
            "source": item["source"],
            "date": item.get("date", datetime.date.today().isoformat()),
            "severity": item.get("severity", "important"),
        }
        if entry["severity"] == "urgent":
            urgent.append(entry)
        else:
            important.append(entry)
    
    return urgent, important


if __name__ == "__main__":
    items = fetch_news()
    print(f"\n采集到 {len(items)} 条新闻：")
    for item in items[:5]:
        print(f"  [{item['severity']}] {item['title'][:50]} ({item['source']})")
        print(f"    {item['link']}")
