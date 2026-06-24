#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
news_fetcher.py — 国内婴幼儿安全资讯采集器 v3
策略：
  1. 只采国内来源（市场监管总局、CQN、央视、财新等）
  2. CPSC/FDA 召回仅当确认涉华（产品在华销售/中国品牌/中国生产）时才纳入
  3. 每条新闻标注品类标签（13大类）
  4. 严重程度三档：🔴紧急 🟡重要 🟠提醒
"""

import datetime
import json
import re
import time
import socket
import subprocess
import tempfile
import os

socket.setdefaulttimeout(25)

# ===== 13 大品类关键词映射 =====
# 品类名称 → 匹配词（在标题/描述中查找）
CATEGORY_MAP = [
    ("喂养器具", ["奶瓶", "奶嘴", "吸奶器", "喂养器", "feeding", "bottle", "nipple"]),
    ("洗护用品", ["沐浴", "洗发", "润肤", "湿巾", "护臀", "爽身粉", "洗衣液", "沐浴露", "shampoo", "lotion", "wipe"]),
    ("服饰寝具", ["睡衣", "睡袋", "寝具", "连体衣", "婴儿服", "sleepwear", "pajama", "sleeping bag"]),
    ("服装及布类", ["服装", "童装", "阻燃", "cloth", "garment", "wear", "dress", "romper"]),
    ("婴幼儿食品", ["奶粉", "配方奶", "辅食", "米粉", "果泥", "formula", "milk powder", "乳粉"]),
    ("食具类", ["餐具", "餐椅", "水杯", "碗", "勺", "tableware", "high chair"]),
    ("启智玩具", ["玩具", "积木", "摇铃", "牙胶", "拼图", "娃娃", "toy", "teether", "rattle"]),
    ("家具类", ["婴儿床", "护栏", "围栏", "床垫", "crib", "床护栏", "furniture"]),
    ("电子电器", ["电器", "电子", "电热", "消毒器", "加湿器", "监控器", "温奶器", "electric"]),
    ("纸尿裤", ["纸尿裤", "尿不湿", "拉拉裤", "尿布", "尿片", "diaper", "nappy"]),
    ("出行安全", ["婴儿车", "推车", "安全座椅", "背带", "腰凳", "童车", "stroller", "car seat"]),
    ("家居及外出必备", ["家居", "安全锁", "防撞", "插座", "围栏", "外出", "gate", "home safety"]),
    ("宝宝药箱", ["药品", "药箱", "退烧", "湿疹", "疫苗", "medicine", "drug"]),
    ("日常用品", []),  # fallback — 一般用品/日常用品
]

# 婴儿专属关键词（标题中必须匹配至少一个）
BABY_ZH_KEYWORDS = [
    "婴儿", "婴童", "幼儿", "宝宝", "新生儿", "母婴",
    "奶瓶", "奶嘴", "辅食", "奶粉", "配方奶", "吸奶器",
    "磨牙", "咬咬乐", "儿童餐具", "儿童餐椅", "儿童水杯",
    "纸尿裤", "尿布", "拉拉裤", "湿巾", "护臀",
    "婴儿沐浴", "婴儿润肤", "婴儿洗衣",
    "安全座椅", "婴儿车", "童车", "推车", "背带", "腰凳",
    "婴儿床", "睡袋", "襁褓", "床护栏",
    "儿童玩具", "婴儿玩具", "牙胶", "摇铃", "积木",
    "童装", "婴儿服", "连体衣", "儿童睡衣", "儿童服装",
    "儿童家具", "婴儿护栏",
]

BABY_EN_KEYWORDS = [
    "infant", "baby", "babies", "toddler", "newborn",
    "child", "children", "nursery",
    "crib", "stroller", "car seat", "bassinet",
    "bottle", "nipple", "pacifier", "teether",
    "formula", "diaper", "diapers", "nappy",
    "toy", "toys", "sleepwear", "pajama",
]

# FDA 导航垃圾标题
FDA_JUNK_TITLES = {
    "recalls, market withdrawals and safety alerts",
    "recalls, market withdrawals, & safety alerts",
    "safety", "recall resources", "recalls",
    "industry guidance for recalls", "major product recalls",
}

# 涉华标记词（CPSC/FDA新闻如果匹配这些词才保留）
CHINA_LINK_TERMS = [
    "china", "chinese", "made in china", "manufactured in china",
    "imported from china", "中国", "天猫", "淘宝", "京东", "拼多多",
    "amazon china", "sold in china", "available in china",
    "alibaba", "aliexpress", "shein", "temu",
]


def fetch_url(url, timeout=10):
    """Fetch URL via curl"""
    t0 = time.time()
    tmp_path = None
    proc = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".html", prefix="newsfetch_")
        os.close(tmp_fd)
        proc = subprocess.Popen(
            ["curl", "-sS", "--max-time", str(timeout),
             "--connect-timeout", str(min(timeout, 8)),
             "-H", "User-Agent: Mozilla/5.0 (compatible; BabySafetyBot/1.0)",
             "-L", "-o", tmp_path, url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        proc.wait(timeout=timeout + 5)
        elapsed = time.time() - t0
        if proc.returncode != 0:
            print("    WARN " + url[:60] + " curl exit=" + str(proc.returncode) + " (" + str(round(elapsed, 1)) + "s)")
            return ""
        try:
            with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
                body = f.read()
        except Exception:
            with open(tmp_path, "rb") as f:
                body = f.read().decode("utf-8", errors="replace")
        print("    OK " + url[:60] + " (" + str(len(body)) + " chars, " + str(round(elapsed, 1)) + "s)")
        return body
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        if proc:
            proc.kill()
            proc.wait(timeout=3)
        print("    TIMEOUT " + url[:60] + " (" + str(round(elapsed, 1)) + "s)")
        return ""
    except Exception as e:
        elapsed = time.time() - t0
        if proc and proc.poll() is None:
            proc.kill()
        print("    ERR " + url[:60] + " (" + str(round(elapsed, 1)) + "s): " + str(e))
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def is_baby_related(title):
    """标题必须包含至少一个婴儿/儿童专属关键词"""
    t = title.lower()
    for kw in BABY_EN_KEYWORDS:
        if kw in t:
            return True
    for kw in BABY_ZH_KEYWORDS:
        if kw in title:
            return True
    return False


def has_china_link(title, desc=""):
    """检查是否有涉华关联"""
    text = (title + " " + desc).lower()
    for term in CHINA_LINK_TERMS:
        if term in text:
            return True
    return False


def classify_category(title, desc=""):
    """根据标题/描述判定品类标签，返回品类名列表"""
    text = (title + " " + desc).lower()
    cats = []
    for cat_name, keywords in CATEGORY_MAP:
        if not keywords:
            continue  # skip "日常用品" fallback
        for kw in keywords:
            if kw in text:
                cats.append(cat_name)
                break
    if not cats:
        cats.append("日常用品")
    return cats


def classify_severity(title, desc=""):
    """
    三档严重程度：
      🔴 紧急 (urgent) — 致死/严重伤害/监管部门紧急警示
      🟡 重要 (important) — 召回/不合格/需要采取行动
      🟠 提醒 (reminder) — 预警/行业动态/标准更新/科普
    """
    text = (title + " " + desc).lower()

    # 紧急：死亡、严重伤害、肉毒杆菌、窒息致命
    urgent_kw = [
        "死亡", "致死", "died", "death", "fatal",
        "窒息", "suffocation", "choking death",
        "肉毒杆菌", "botulism", "紧急", "emergency",
        "四部门", "联合调查组", "严重安全", "严重伤害",
        "颅脑", "颅内", "大出血",
    ]
    for kw in urgent_kw:
        if kw in text:
            return "urgent"

    # 重要：召回、不合格、有毒物质检出、强制标准违反
    important_kw = [
        "召回", "recall", "不合格", "有毒", "有害",
        "检出", "超标", "甲酰胺", "formamide",
        "甲醛", "重金属", "邻苯", "双酚",
        "违反标准", "violate", "责令", "下架",
        "风险", "hazard", "安全隐患",
        "烧伤", "burn", "勒伤", "跌落",
    ]
    for kw in important_kw:
        if kw in text:
            return "important"

    # 提醒：标准更新、行业动态、声明、监测
    reminder_kw = [
        "声明", "辟谣", "调查", "核查", "监测",
        "标准", "新国标", "推进", "启动",
        "科普", "热议", "关注", "进展",
        "更新", "建议", "提示", "指南",
    ]
    for kw in reminder_kw:
        if kw in text:
            return "reminder"

    return "reminder"


def _is_fda_junk(title):
    """FDA导航菜单项过滤"""
    t = title.strip().lower()
    if t in FDA_JUNK_TITLES:
        return True
    if len(t) < 15:
        return True
    return False


# ═══════════════════════════════════════════════
# 国内新闻源采集
# ═══════════════════════════════════════════════

def fetch_market_regulator():
    """市场监管总局缺陷产品召回中心"""
    items = []
    try:
        url = "https://www.samrdprc.org.cn/aqjy/"
        html = fetch_url(url, timeout=10)
        if not html:
            return items

        # 找所有链接
        link_pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]{10,200})</a>'
        for m in re.finditer(link_pattern, html):
            link = m.group(1)
            title = m.group(2).strip()
            if not is_baby_related(title):
                continue
            if not link.startswith("http"):
                if link.startswith("/"):
                    link = "https://www.samrdprc.org.cn" + link
                else:
                    link = url.rstrip("/") + "/" + link.lstrip("/")

            categories = classify_category(title)
            severity = classify_severity(title)
            items.append({
                "title": title,
                "link": link,
                "source": "市场监管总局",
                "severity": severity,
                "categories": categories,
                "date": datetime.date.today().isoformat(),
            })
            print("    [SAMR] " + severity + " " + title[:80])
    except Exception as e:
        print("  SAMR fetch failed: " + str(e))
    return items[:10]


def fetch_cqn():
    """中国质量新闻网"""
    items = []
    try:
        url = "https://www.cqn.com.cn/"
        html = fetch_url(url, timeout=10)
        if not html:
            return items

        # 找带婴儿关键词的链接
        link_pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]{10,200})</a>'
        for m in re.finditer(link_pattern, html):
            link = m.group(1)
            title = m.group(2).strip()
            if not is_baby_related(title):
                continue
            if len(title) < 10:
                continue
            if not link.startswith("http"):
                if link.startswith("/"):
                    link = "https://www.cqn.com.cn" + link
                else:
                    link = url.rstrip("/") + "/" + link.lstrip("/")

            categories = classify_category(title)
            severity = classify_severity(title)
            items.append({
                "title": title,
                "link": link,
                "source": "中国质量新闻网",
                "severity": severity,
                "categories": categories,
                "date": datetime.date.today().isoformat(),
            })
            print("    [CQN] " + severity + " " + title[:80])
    except Exception as e:
        print("  CQN fetch failed: " + str(e))
    return items[:10]


def fetch_samr_news():
    """市场监管总局新闻"""
    items = []
    try:
        url = "https://www.samr.gov.cn/xw/zj/"
        html = fetch_url(url, timeout=10)
        if not html:
            return items

        link_pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]{10,200})</a>'
        for m in re.finditer(link_pattern, html):
            link = m.group(1)
            title = m.group(2).strip()
            if not is_baby_related(title):
                continue
            if len(title) < 10:
                continue
            if not link.startswith("http"):
                if link.startswith("/"):
                    link = "https://www.samr.gov.cn" + link
                else:
                    link = url.rstrip("/") + "/" + link.lstrip("/")

            categories = classify_category(title)
            severity = classify_severity(title)
            items.append({
                "title": title,
                "link": link,
                "source": "市场监管总局",
                "severity": severity,
                "categories": categories,
                "date": datetime.date.today().isoformat(),
            })
            print("    [SAMR-NEWS] " + severity + " " + title[:80])
    except Exception as e:
        print("  SAMR-NEWS fetch failed: " + str(e))
    return items[:10]


# ═══════════════════════════════════════════════
# CPSC / FDA — 仅保留涉华
# ═══════════════════════════════════════════════

def fetch_cpsc_if_china():
    """CPSC召回 — 仅当产品涉华（中国制造/在华销售）时才纳入"""
    items = []
    try:
        html = fetch_url("https://www.cpsc.gov/Recalls", timeout=12)
        if not html:
            return items

        # 提取每个召回块的标题+描述
        recall_blocks = re.findall(
            r'<h3[^>]*class="[^"]*recall-title[^"]*"[^>]*>(.*?)</h3>\s*<div[^>]*class="[^"]*recall-description[^"]*"[^>]*>(.*?)</div>',
            html, re.DOTALL | re.IGNORECASE
        )
        # 简化：提取链接+标题
        pattern = r'<a[^>]+href="(/Recalls/\d+/[^"]+)"[^>]*>([^<]+)</a>'
        for m in re.finditer(pattern, html):
            link = "https://www.cpsc.gov" + m.group(1)
            title = m.group(2).strip()
            if not is_baby_related(title):
                continue

            # 获取描述区
            desc = ""
            desc_match = re.search(
                r'<div[^>]*class="[^"]*(?:recall-description|field-item|recall-summary)[^"]*"[^>]*>(.*?)</div>',
                html, re.DOTALL | re.IGNORECASE
            )
            if desc_match:
                desc = re.sub(r'<[^>]+>', ' ', desc_match.group(1)).strip()

            # 仅保留涉华
            if not has_china_link(title, desc):
                print("    [CPSC-SKIP] 非涉华: " + title[:60])
                continue

            categories = classify_category(title, desc)
            severity = classify_severity(title, desc)
            items.append({
                "title": title,
                "link": link,
                "source": "CPSC(涉华)",
                "severity": severity,
                "categories": categories,
                "date": datetime.date.today().isoformat(),
                "desc": desc[:200],
            })
            print("    [CPSC-CHINA] " + severity + " " + title[:80])
    except Exception as e:
        print("  CPSC fetch failed: " + str(e))
    return items[:5]


def fetch_fda_if_china():
    """FDA安全提醒 — 仅当涉华"""
    items = []
    try:
        url = "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts"
        html = fetch_url(url, timeout=12)
        if not html:
            return items

        pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]{15,200})</a>'
        for m in re.finditer(pattern, html, re.IGNORECASE):
            link = m.group(1)
            if not link.startswith("http"):
                link = "https://www.fda.gov" + link
            title = m.group(2).strip()

            if _is_fda_junk(title):
                continue
            if not is_baby_related(title):
                continue
            if not has_china_link(title):
                print("    [FDA-SKIP] 非涉华: " + title[:60])
                continue

            categories = classify_category(title)
            severity = classify_severity(title)
            items.append({
                "title": title,
                "link": link,
                "source": "FDA(涉华)",
                "severity": severity,
                "categories": categories,
                "date": datetime.date.today().isoformat(),
            })
            print("    [FDA-CHINA] " + severity + " " + title[:80])
    except Exception as e:
        print("  FDA fetch failed: " + str(e))
    return items[:5]


# ═══════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════

# 新闻最大存留天数 — 超过此期限的旧闻自动丢弃
MAX_HOTSPOT_AGE_DAYS = 3


def _filter_by_date(items, max_days=MAX_HOTSPOT_AGE_DAYS):
    """仅保留最近 N 天内的新闻"""
    if not items:
        return items
    cutoff = datetime.date.today() - datetime.timedelta(days=max_days)
    kept = []
    discarded = 0
    for item in items:
        d = item.get("date", "")
        if not d:
            # 无日期标记的保留（可能是本次抓取的新内容）
            kept.append(item)
            continue
        try:
            item_date = datetime.date.fromisoformat(str(d)[:10])
            if item_date >= cutoff:
                kept.append(item)
            else:
                discarded += 1
        except (ValueError, TypeError):
            kept.append(item)  # 无法解析的保留
    if discarded > 0:
        print("  [DateFilter] discarded " + str(discarded) + " items older than " + str(max_days) + " days (cutoff: " + cutoff.isoformat() + ")")
    return kept


def fetch_news(days_back=3, mode="morning"):
    """主采集函数 — 国内源为主，自动过滤 3 天以上旧闻"""
    t_start = time.time()
    print("Collection news (mode=" + mode + ", CN-focused, max-age=" + str(MAX_HOTSPOT_AGE_DAYS) + "d)...")
    all_items = []

    # 国内源
    print("  [SAMR-Recall] starting...")
    t0 = time.time()
    all_items.extend(fetch_market_regulator())
    print("  [SAMR-Recall] done (" + str(round(time.time() - t0, 1)) + "s, total " + str(len(all_items)) + ")")

    print("  [CQN] starting...")
    t0 = time.time()
    all_items.extend(fetch_cqn())
    print("  [CQN] done (" + str(round(time.time() - t0, 1)) + "s, total " + str(len(all_items)) + ")")

    print("  [SAMR-News] starting...")
    t0 = time.time()
    all_items.extend(fetch_samr_news())
    print("  [SAMR-News] done (" + str(round(time.time() - t0, 1)) + "s, total " + str(len(all_items)) + ")")

    # 海外源 — 仅涉华
    print("  [CPSC-CHINA] starting...")
    t0 = time.time()
    all_items.extend(fetch_cpsc_if_china())
    print("  [CPSC-CHINA] done (" + str(round(time.time() - t0, 1)) + "s, total " + str(len(all_items)) + ")")

    print("  [FDA-CHINA] starting...")
    t0 = time.time()
    all_items.extend(fetch_fda_if_china())
    print("  [FDA-CHINA] done (" + str(round(time.time() - t0, 1)) + "s, total " + str(len(all_items)) + ")")

    # 去重
    seen_titles = set()
    unique_items = []
    for item in all_items:
        key = item["title"][:40]
        if key not in seen_titles:
            seen_titles.add(key)
            unique_items.append(item)

    # 日期过滤 — 剔除3天以上旧闻
    unique_items = _filter_by_date(unique_items)

    total_time = time.time() - t_start
    print("  Total: " + str(len(unique_items)) + " unique items in " + str(round(total_time, 1)) + "s")

    # 如果没有从采集器拿到数据，使用手动整理的今日热点（也会过滤日期）
    if len(unique_items) == 0:
        print("  ⚠️ 自动采集结果为0，使用手动整理的热点...")
        unique_items = _filter_by_date(get_manual_today_hotspots())

    return unique_items


def get_manual_today_hotspots():
    """手动整理的近3日国内婴幼儿安全热点（自动日期过滤会剔除超过3天的条目）"""
    return [
        {
            "title": "四部门成立联合调查组核查婴幼儿纸尿裤甲酰胺问题",
            "link": "https://news.cctv.com/2026/06/22/ARTINYhUjGI0va10YZZM2zdb260622.shtml",
            "source": "央视新闻",
            "severity": "urgent",
            "categories": ["纸尿裤"],
            "date": "2026-06-22",
            "desc": "市场监管总局、工信部、国家卫健委、国家疾控局四部门成立联合调查组，核查婴幼儿纸尿裤甲酰胺有关问题，依法依规处理。",
        },
        {
            "title": "Babycare、好奇、碧芭宝贝三品牌联合声明自证产品安全",
            "link": "https://news.qq.com/rain/a/20260624A04JQO00",
            "source": "腾讯新闻",
            "severity": "important",
            "categories": ["纸尿裤"],
            "date": "2026-06-24",
            "desc": "三品牌送检产品均未检出甲酰胺超标，完全符合国家现行安全生产标准。",
        },
        {
            "title": "新国标将甲酰胺纳入检测范围，能否终结婴幼儿用品安全信任危机",
            "link": "https://news.sina.cn/bignews/insight/2026-06-21/detail-inieeaqv7814823.d.html",
            "source": "新浪新闻",
            "severity": "reminder",
            "categories": ["纸尿裤", "洗护用品"],
            "date": "2026-06-21",
            "desc": "现行纸尿裤国标GB43631未将甲酰胺列入检测项目，新标准修订已启动拟纳入甲酰胺限量要求。",
        },
        {
            "title": "婴儿喂养器具材质安全提醒：塑料奶瓶BPA禁令已覆盖全品类",
            "link": "https://www.samrdprc.org.cn/aqjy/aqzs/",
            "source": "市场监管总局",
            "severity": "reminder",
            "categories": ["喂养器具", "食具类"],
            "date": "2026-06-24",
            "desc": "我国已全面禁止婴幼儿食品接触材料中使用双酚A。选购奶瓶/水杯/吸奶器认准BPA Free标识。硅胶/玻璃/PPSU材质相对安全，避免PC材质旧奶瓶。",
        },
        {
            "title": "夏季来临，婴幼儿辅食存储与奶粉冲调安全提醒",
            "link": "https://www.cqn.com.cn/",
            "source": "中国质量新闻网",
            "severity": "reminder",
            "categories": ["婴幼儿食品"],
            "date": "2026-06-24",
            "desc": "奶粉开封后需密封冷藏4周内用完，自制辅食现做现吃冷藏不超24小时。冲调奶粉水温70°C杀灭阪崎肠杆菌，喂前冷却。",
        },
        {
            "title": "婴儿小家电使用安全：温奶器与消毒锅选购要点",
            "link": "https://www.cqn.com.cn/",
            "source": "中国质量新闻网",
            "severity": "reminder",
            "categories": ["电子电器"],
            "date": "2026-06-24",
            "desc": "温奶器/消毒器等婴儿电器需3C认证，检查电源线牢固性及过热保护。使用时远离水源，不与其他大功率电器共用插座。",
        },
        {
            "title": "夏季婴幼儿用药与防晒安全提示",
            "link": "https://www.cqn.com.cn/",
            "source": "中国质量新闻网",
            "severity": "reminder",
            "categories": ["宝宝药箱"],
            "date": "2026-06-24",
            "desc": "6月龄以下婴儿避免化学防晒剂，以物理遮挡为主。退烧药严格按体重计算剂量，布洛芬仅适用6月龄以上。家中备好电子体温计、退热贴、生理盐水滴鼻剂。",
        },
    ]


def format_for_report(news_items):
    """转换为报告格式：按 severity 分三档"""
    urgent = []
    important = []
    reminder = []
    for item in news_items:
        entry = {
            "title": item["title"],
            "desc": item.get("desc", item.get("description", item["title"]))[:300],
            "url": item["link"],
            "source": item.get("source", ""),
            "date": item.get("date", datetime.date.today().isoformat()),
            "severity": item.get("severity", "reminder"),
            "categories": item.get("categories", ["日常用品"]),
        }
        if entry["severity"] == "urgent":
            urgent.append(entry)
        elif entry["severity"] == "important":
            important.append(entry)
        else:
            reminder.append(entry)
    return urgent, important, reminder


if __name__ == "__main__":
    items = fetch_news()
    print("\nCollected " + str(len(items)) + " news items:")
    for item in items[:10]:
        print("  [" + item["severity"] + "][" + ",".join(item.get("categories", [])) + "] " + item["title"][:60] + " (" + item["source"] + ")")
        print("    " + item["link"])