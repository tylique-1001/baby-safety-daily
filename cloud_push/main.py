#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py - 云端推送主入口
GitHub Actions 调用此脚本完成完整推送流程
V5 完整版（进度条+sticky-header+hero动画+品类芯片+症状标签+source截断+tips-grid+FAB）

使用方式：
  python3 main.py --mode morning   # 早间版（全天报告）
  python3 main.py --mode evening    # 晚间版（增量更新）
"""

import sys
import os
import json
import time
import datetime
import argparse
import hashlib

# 添加当前目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news_fetcher import fetch_news, format_for_report
from feishu_sender import send_daily_report, send_daily_report_with_retry
from config import CLOUDSTUDIO_SUBDOMAIN

# ═══════════════════════════════════════════════
# 14品类 emoji 映射
# ═══════════════════════════════════════════════
CAT_EMOJI = {
    "喂养器具": "🍼", "洗护用品": "🧴", "服饰寝具": "👕", "服装及布类": "👕",
    "婴幼儿食品": "🍚", "食具类": "🥄", "启智玩具": "🧸", "家具类": "🛏️",
    "电子电器": "🔌", "纸尿裤": "🍑", "出行安全": "🚗",
    "家居及外出必备": "🛡️", "宝宝药箱": "💊", "日常用品": "📦",
}
ALL_CATEGORIES = [
    "喂养器具", "洗护用品", "服饰寝具", "服装及布类", "婴幼儿食品",
    "食具类", "启智玩具", "家具类", "电子电器", "纸尿裤",
    "出行安全", "家居及外出必备", "宝宝药箱", "日常用品",
]


def get_weekday_str(d):
    days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return days[d.weekday()]


def get_tips(date):
    """获取结构化安全贴士"""
    tips_pool = [
        {
            "title": "玩具选购：认准CCC",
            "desc": "购买儿童玩具务必查看CCC认证标识及完整标签，避开易脱落的小零件、锐利边缘和刺鼻气味。低龄幼儿玩玩具时家长全程看护，防止啃咬误食。"
        },
        {
            "title": "新衣物先洗再穿",
            "desc": "儿童及婴幼儿服装选购时重点检查绳带长度（领口/帽兜/腰部），新衣物务必先清洗再穿着，减少甲醛、pH值超标等化学物质对皮肤的刺激。"
        },
        {
            "title": "家具安全检查防倾倒",
            "desc": "检查家中梳妆柜、书架等家具是否固定在墙上。CPSC近期多次召回不合格防倾倒套件。家中如有幼儿，确保所有高于60cm的家具均已可靠固定，防止倾倒压伤。"
        },
        {
            "title": "纸尿裤勤换防红臀",
            "desc": "纸尿裤建议每3-4小时更换一次，更换时用温水清洗并晾干屁屁再穿新的。如出现反复红臀无法改善，排查纸尿裤品牌并更换。"
        },
        {
            "title": "婴儿床安全睡眠",
            "desc": "婴儿睡眠环境保持简洁——不用床围、枕头、厚重被子。婴儿床护栏间距不超过6cm，床垫与护栏间缝隙不超过2指宽。"
        },
        {
            "title": "食品安全：逐一引入新食材",
            "desc": "婴儿引入新食材时每次只引入一种，观察3-5天有无过敏反应。1岁前禁食蜂蜜（肉毒杆菌风险），3岁前禁食整颗坚果（窒息风险）。"
        },
        {
            "title": "出行必用安全座椅",
            "desc": "婴幼儿乘车必须使用符合国标的安全座椅，2岁前建议反向安装。定期检查安全座椅是否在召回名单中，过期/碰撞过的座椅应立即更换。"
        },
        {
            "title": "家中化学品上锁存放",
            "desc": "清洁剂、药品、化妆品等应存放在婴儿无法触及的高处或带锁柜中。不要在饮料瓶中分装清洁剂，避免婴幼儿误食。"
        },
    ]
    seed = date.isoformat().encode()
    indices = set()
    attempt = 0
    while len(indices) < 3:
        attempt += 1
        h = int(hashlib.md5(seed + str(attempt).encode()).hexdigest()[:2], 16)
        indices.add(h % len(tips_pool))
    return [tips_pool[i] for i in sorted(indices)]


def is_valid_url(url):
    """验证 URL 非首页（路径深度 >= 2）"""
    if not url:
        return False
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path_segments = [s for s in parsed.path.strip('/').split('/') if s]
    return len(path_segments) >= 2


def build_news_cards_html(news_list, n_urgent=0):
    """构建新闻卡片 HTML（V5 完整版：severity徽章+折叠+症状标签+source截断+品类过滤）"""
    cards_html = ""
    for idx, news in enumerate(news_list):
        is_urgent = news.get("severity") == "urgent"
        card_class = "urgent" if is_urgent else "warn"
        severity_text = "🔴 紧急" if is_urgent else ("🟡 重要" if news.get("severity") == "important" else "🟠 提醒")
        title = news.get("title", "")
        source_label = news.get("source", "")
        date_str = news.get("date", "")
        desc = news.get("desc", title)
        categories = news.get("categories", ["日常用品"])
        cat_data = ",".join(categories)
        symptom = news.get("symptom", "")
        prevent = news.get("prevent", "")
        action = news.get("action", "")

        # 多源链接
        urls = news.get("urls", [])
        single_url = news.get("url", "")
        existing_urls = set(link for _, link in urls)
        if single_url and is_valid_url(single_url) and single_url not in existing_urls:
            urls.append((source_label, single_url))
        if not urls:
            urls = [(source_label, single_url if single_url else "#")]

        # source-tag: flag style based on domain
        source_tags_html = ""
        for lbl, link in urls:
            link_lower = link.lower()
            if "cpsc.gov" in link_lower or "fda.gov" in link_lower or "cdc.gov" in link_lower:
                cls = "us"
            elif "samr" in link_lower or "cqn.com.cn" in link_lower or "cctv.com" in link_lower or "163.com" in link_lower or "qq.com" in link_lower:
                cls = "cn"
            else:
                cls = "intl"
            source_tags_html += (
                '<a href="' + link + '" class="source-tag ' + cls + '" target="_blank" rel="noopener">'
                + ('🇺🇸 ' if cls == 'us' else '🇨🇳 ' if cls == 'cn' else '🌐 ') + lbl +
                '</a>\n'
            )

        # 症状/预防/行动标签
        tag_row_html = ""
        if symptom or prevent or action:
            tag_row_html = '<div class="tag-row">\n'
            if symptom:
                tag_row_html += '<span class="nc-tag danger">🩺 症状：' + symptom + '</span>\n'
            if prevent:
                tag_row_html += '<span class="nc-tag prevent">🛡️ 预防：' + prevent + '</span>\n'
            if action:
                tag_row_html += '<span class="nc-tag action">✅ 行动：' + action + '</span>\n'
            tag_row_html += '</div>\n'

        card = (
            '<div class="news-card ' + card_class + '" data-index="' + str(idx) + '" data-categories="' + cat_data + '">\n'
            '  <div class="card-header">\n'
            '    <h3>' + title + '</h3>\n'
            '    <span class="severity">' + severity_text + '</span><span class="collapse-chevron">▼</span>\n'
            '  </div>\n'
            '  <div class="card-details">\n'
            '  <div class="card-body">\n'
            '    <p>' + desc + '</p>\n'
            '  </div>\n'
            + tag_row_html +
            '  <div class="source-row">\n'
            + source_tags_html +
            '    <span class="source-date">' + date_str + '</span>\n'
            '  </div>\n'
            '  </div><!-- /card-details -->\n'
            '</div>\n'
        )
        cards_html += card
    return cards_html


def build_category_chips(news_list):
    """生成品类芯片 HTML——含内容品类正常、无内容品类半透明"""
    content_cats = set()
    for news in news_list:
        for c in news.get("categories", []):
            content_cats.add(c)

    chips_html = '<span class="cat-chip cat-chip-all active" data-cat="all">📋 全部</span>\n'
    for cat in ALL_CATEGORIES:
        emoji = CAT_EMOJI.get(cat, "📦")
        if cat in content_cats:
            chips_html += '<span class="cat-chip" data-cat="' + cat + '">' + emoji + ' ' + cat + '</span>\n'
        else:
            # 无内容品类：半透明不可点击
            chips_html += '<span class="cat-chip" data-cat="' + cat + '" style="opacity:.4;cursor:default" title="今日暂无此品类资讯">' + emoji + ' ' + cat + '</span>\n'
    return chips_html


# ═══════════════════════════════════════════════
# CSS 模板 — V5 完整版（Lumin Design System v4.4）
# ═══════════════════════════════════════════════
CSS_TEMPLATE = r'''
/* ===== V4.4 Lumin Design System ===== */
:root {
  --coral: #FF5E62; --coral-d: #E0484D; --coral-l: #FF8A8E; --coral-bg: #FFF3F2;
  --red: #DC2626; --red-bg: #FEF2F2; --amber: #D97706; --amber-bg: #FFFBEB;
  --blue: #3B82F6; --blue-bg: #EFF6FF; --green: #059669; --green-bg: #ECFDF5;
  --text: #0F172A; --text-2: #475569; --text-3: #94A3B8;
  --card: #FFFFFF; --bg: #FAFAF9;
  --sans: "PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",-apple-system,BlinkMacSystemFont,sans-serif;
  --r-sm:8px; --r:14px; --r-lg:20px; --r-xl:28px; --r-full:9999px;
  --shadow-xs:0 1px 2px rgba(0,0,0,.025);
  --shadow-sm:0 1px 3px rgba(0,0,0,.04),0 1px 8px rgba(0,0,0,.025);
  --shadow-md:0 4px 16px rgba(0,0,0,.05),0 1px 4px rgba(0,0,0,.03);
  --shadow-lg:0 8px 30px rgba(0,0,0,.06),0 2px 8px rgba(0,0,0,.03);
  --ease-out:cubic-bezier(0.16,1,0.3,1);
  --ease-spring:cubic-bezier(0.34,1.56,0.64,1);
  --w:680px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth;-webkit-font-smoothing:antialiased}
html.scroll-restoring{visibility:hidden}
body{font-family:var(--sans);color:var(--text);background:var(--bg);line-height:1.7;font-size:15px;max-width:var(--w);margin:0 auto;padding:0 20px}

/* ===== Progress Bar ===== */
#progress-bar{position:fixed;top:0;left:0;width:0%;height:3px;background:linear-gradient(90deg,var(--coral),var(--coral-d));z-index:1000;transition:width .1s linear}

/* ===== Sticky Header ===== */
.sticky-header{position:sticky;top:0;z-index:100;background:rgba(250,250,249,.82);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);padding:12px 0;margin:0 -20px;padding-left:20px;padding-right:20px;border-bottom:1px solid transparent;transition:border-color .3s var(--ease-out),box-shadow .3s var(--ease-out)}
.sticky-header.scrolled{border-bottom:1px solid rgba(0,0,0,.06);box-shadow:0 1px 8px rgba(0,0,0,.04)}
.sticky-header-inner{display:flex;align-items:center;justify-content:space-between;max-width:var(--w);margin:0 auto}
.sticky-logo{display:flex;align-items:center;gap:8px;font-weight:700;font-size:14px;color:var(--coral-d);text-decoration:none}
.sticky-logo svg{width:22px;height:22px}
.sticky-nav{display:flex;gap:4px;align-items:center;list-style:none}
.sticky-nav a{text-decoration:none;font-size:12px;color:var(--text-2);padding:4px 10px;border-radius:8px;gap:4px;display:flex;align-items:center;transition:all .2s var(--ease-out)}
.sticky-nav a:hover{background:var(--coral-bg);color:var(--coral-d)}
.sticky-nav a.active{background:var(--coral-bg);color:var(--coral-d);font-weight:600}
.live-dot{width:7px;height:7px;border-radius:50%;background:var(--coral);animation:livePulse 2s ease-in-out infinite;display:inline-block}
@keyframes livePulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.4)}}

/* ===== Hero ===== */
.hero{position:relative;background:linear-gradient(150deg,#FF5E62 0%,#E0484D 25%,#FF6B7A 50%,#FF8A8E 75%,#FFB3A0 100%);border-radius:var(--r-xl);padding:48px 40px;margin:20px 0 32px;overflow:hidden;color:#fff}
.hero-dots{position:absolute;inset:0;pointer-events:none}
.hero-dots span{position:absolute;border-radius:50%;background:rgba(255,255,255,.12);animation:floatDot 8s ease-in-out infinite}
.hero-dots span:nth-child(1){width:60px;height:60px;top:15%;left:10%;animation-delay:0s}
.hero-dots span:nth-child(2){width:40px;height:40px;top:25%;right:15%;animation-delay:2s}
.hero-dots span:nth-child(3){width:80px;height:80px;bottom:10%;right:8%;animation-delay:4s}
.hero-dots span:nth-child(4){width:30px;height:30px;bottom:20%;left:20%;animation-delay:6s}
.hero-dots span:nth-child(5){width:50px;height:50px;top:50%;left:60%;animation-delay:3s}
@keyframes floatDot{0%,100%{transform:translateY(0) scale(1);opacity:.12}50%{transform:translateY(-20px) scale(1.1);opacity:.2}}
.hero-wave{position:absolute;bottom:-1px;left:0;right:0}
.hero-content{position:relative;z-index:2}
.hero-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.2);backdrop-filter:blur(8px);padding:6px 16px;border-radius:var(--r-full);font-size:13px;font-weight:600;margin-bottom:16px;letter-spacing:.02em}
.hero h1{font-size:32px;font-weight:800;line-height:1.3;margin:0 0 10px;letter-spacing:-.01em}
.hero p{font-size:16px;opacity:.9;margin:0;font-weight:400;max-width:460px;line-height:1.6}
.hero-meta{display:flex;gap:16px;margin-top:16px;font-size:13px;opacity:.8;flex-wrap:wrap}
.hero-meta span{display:flex;align-items:center;gap:4px}

/* ===== Stats Row ===== */
.stats-row{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:36px}
.stat-card{position:relative;background:var(--card);border-radius:var(--r-lg);padding:22px 20px;box-shadow:var(--shadow-sm);overflow:hidden;cursor:default;transition:transform .3s var(--ease-spring),box-shadow .3s var(--ease-out)}
.stat-card:hover{transform:translateY(-3px);box-shadow:0 6px 24px rgba(255,94,98,.06),0 2px 6px rgba(0,0,0,.03)}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.stat-card.urgent::before{background:linear-gradient(90deg,#DC2626,#EF4444,#DC2626)}
.stat-card.warn::before{background:linear-gradient(90deg,#D97706,#F59E0B,#D97706)}
.stat-card.tip::before{background:linear-gradient(90deg,#3B82F6,#60A5FA,#3B82F6)}
.stat-num{font-size:42px;font-weight:800;line-height:1}
.stat-card.urgent .stat-num{color:#DC2626}
.stat-card.warn .stat-num{color:#D97706}
.stat-card.tip .stat-num{color:#3B82F6}
.stat-label{font-size:13px;color:var(--text-2);margin-top:4px}
.stat-icon{position:absolute;right:16px;top:50%;transform:translateY(-50%);font-size:32px;opacity:.12}
.stat-card::after{content:'';position:absolute;bottom:0;left:20px;right:20px;height:3px;border-radius:2px;width:0%;transition:width .8s var(--ease-out)}
.stat-card.animated::after{width:60%}
.stat-card.urgent::after{background:linear-gradient(90deg,#FCA5A5,#DC2626,#FCA5A5)}
.stat-card.warn::after{background:linear-gradient(90deg,#FCD34D,#D97706,#FCD34D)}
.stat-card.tip::after{background:linear-gradient(90deg,#93C5FD,#3B82F6,#93C5FD)}

/* ===== Section Title ===== */
.sec-title{display:flex;align-items:center;gap:10px;margin:40px 0 20px;font-size:20px;font-weight:700;color:var(--text);padding-bottom:12px;border-bottom:1px solid rgba(0,0,0,.05)}
.sec-title .dot{width:10px;height:10px;border-radius:50%}
.sec-title .dot.red{background:var(--red)}
.sec-title .dot.amber{background:var(--amber)}
.sec-title .dot.blue{background:var(--blue)}

/* ===== News Cards ===== */
.news-list{display:flex;flex-direction:column;gap:14px;margin-bottom:36px}
.news-card{position:relative;background:var(--card);border-radius:var(--r);padding:20px 22px;box-shadow:var(--shadow-xs);transition:transform .25s var(--ease-spring),box-shadow .25s var(--ease-out);opacity:0;transform:translateY(20px)}
.news-card.visible{opacity:1;transform:translateY(0);transition:opacity .5s var(--ease-out),transform .5s var(--ease-spring)}
.news-card:hover{box-shadow:0 8px 28px rgba(255,94,98,.07),0 2px 10px rgba(0,0,0,.04);transform:translateY(-1px)}
.news-card.urgent{border-left:4px solid #DC2626}
.news-card.warn{border-left:4px solid #D97706}
.news-card .card-header{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:10px;cursor:pointer;user-select:none;-webkit-tap-highlight-color:transparent}
.news-card .card-header:hover .collapse-chevron{opacity:.7}
.collapse-chevron{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:var(--r-full);background:var(--bg);color:var(--text-3);font-size:14px;flex-shrink:0;transition:transform .35s var(--ease-spring),opacity .25s;margin-top:2px}
.news-card .card-details{max-height:2000px;overflow:hidden;opacity:1;transition:max-height .5s var(--ease-out),opacity .35s var(--ease-out),margin .4s var(--ease-out)}
.news-card.collapsed .card-details{max-height:0;opacity:0;margin-top:0}
.news-card.collapsed .collapse-chevron{transform:rotate(-90deg)}
.news-card.collapsed .card-header{margin-bottom:0}
.news-card.collapsed:hover{transform:none;box-shadow:var(--shadow-xs)}
.news-card .severity{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:700;padding:3px 10px;border-radius:var(--r-full);white-space:nowrap}
.news-card.urgent .severity{background:#FEE2E2;color:#B91C1C}
.news-card.warn .severity{background:#FEF3C7;color:#92400E}
.news-card h3{font-size:17px;font-weight:700;line-height:1.4;margin:0;color:var(--text)}
.news-card .card-body{font-size:14px;color:var(--text-2);line-height:1.7;margin-bottom:12px}
.news-card .card-body p{margin:0 0 6px}
.news-card .tag-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.nc-tag{display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:600;padding:3px 8px;border-radius:var(--r-sm)}
.nc-tag.danger{background:#FEE2E2;color:#B91C1C}
.nc-tag.prevent{background:#FEF3C7;color:#92400E}
.nc-tag.action{background:#D1FAE5;color:#065F46}
.news-card .source-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:12px;color:var(--text-3)}
.source-tag{display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:600;padding:2px 8px;border-radius:var(--r-sm);text-decoration:none;transition:opacity .2s}
.source-tag:hover{opacity:.75}
.source-tag.cn{background:#FEF3C7;color:#92400E}
.source-tag.us{background:#DBEAFE;color:#1E40AF}
.source-tag.intl{background:#D1FAE5;color:#065F46}
.source-date{color:var(--text-3)}
.source-row .source-more{display:none;font-size:11px;color:var(--coral);cursor:pointer;font-weight:600;padding:1px 6px;border-radius:4px;background:var(--coral-bg);border:none;font-family:var(--sans);transition:opacity .2s}
.source-row .source-more:hover{opacity:.7}
.source-row.has-more .source-tag:nth-of-type(n+4){display:none}
.source-row.has-more.expanded .source-tag:nth-of-type(n+4){display:inline-flex}
.source-row.has-more .source-more{display:inline-flex}

/* ===== Tips Section ===== */
.tips-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:36px}
.tip-card{background:var(--card);border-radius:var(--r-lg);padding:22px 20px;box-shadow:var(--shadow-xs);border-left:3px solid var(--blue);transition:transform .25s var(--ease-spring),box-shadow .25s var(--ease-spring);opacity:0;transform:translateY(20px)}
.tip-card.visible{opacity:1;transform:translateY(0);transition:opacity .5s var(--ease-out),transform .5s var(--ease-spring)}
.tip-card:hover{transform:translateY(-3px);box-shadow:0 6px 22px rgba(59,130,246,.1),0 1px 4px rgba(0,0,0,.03)}
.tip-num{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:var(--r-full);background:var(--blue-bg);color:var(--blue);font-weight:800;font-size:13px;margin-bottom:10px;box-shadow:0 2px 8px rgba(59,130,246,.12);transition:box-shadow .3s var(--ease-spring)}
.tip-card:hover .tip-num{box-shadow:0 4px 16px rgba(59,130,246,.22)}
.tip-card h4{font-size:15px;font-weight:700;color:var(--text);margin:0 0 6px}
.tip-card p{font-size:13px;color:var(--text-2);line-height:1.6;margin:0}

/* ===== Category Chips ===== */
.cat-section{margin-bottom:36px;padding-bottom:20px;border-bottom:1px solid rgba(0,0,0,.04)}
.cat-chips{display:flex;flex-wrap:wrap;gap:8px}
.cat-chip{display:inline-flex;align-items:center;gap:4px;font-size:12px;padding:6px 14px;border-radius:var(--r-full);background:var(--card);color:var(--text-2);border:1.5px solid transparent;cursor:pointer;transition:all .2s var(--ease-out);user-select:none}
.cat-chip:hover{background:var(--coral-bg);color:var(--coral-d);transform:translateY(-1px)}
.cat-chip.active{border:1.5px solid #FECACA;background:var(--coral-bg);color:var(--coral-d);font-weight:600}
.cat-chip-all{font-weight:600}
.news-card.filtered-out{display:none}
@keyframes chipHighlight{0%,100%{box-shadow:0 8px 28px rgba(255,94,98,.07),0 2px 10px rgba(0,0,0,.04)}50%{box-shadow:0 8px 28px rgba(255,94,98,.2),0 0 0 3px rgba(255,94,98,.15)}}

/* ===== Footer ===== */
.page-footer{text-align:center;padding:36px 0 32px;margin-top:40px;position:relative}
.page-footer::before{content:'';position:absolute;top:0;left:10%;right:10%;height:2px;background:linear-gradient(90deg,transparent,rgba(255,94,98,.12),rgba(59,130,246,.1),transparent);border-radius:1px}
.page-footer p{font-size:12px;color:var(--text-3);margin:0}
.page-footer .disclaimer{margin-top:8px;font-size:11px;color:var(--text-3);opacity:.7;max-width:500px;margin-left:auto;margin-right:auto}

/* ===== Back to Top ===== */
#back-to-top{position:fixed;bottom:28px;right:28px;width:44px;height:44px;border-radius:var(--r-full);background:var(--coral);color:#fff;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:var(--shadow-md);opacity:0;pointer-events:none;transform:translateY(10px);transition:all .3s var(--ease-spring);z-index:99;font-size:18px}
#back-to-top.visible{opacity:1;pointer-events:auto;transform:translateY(0)}
#back-to-top:hover{background:var(--coral-d);transform:translateY(-2px) scale(1.05)}

/* ===== FAB Share ===== */
#fab-share{position:fixed;bottom:82px;right:28px;width:44px;height:44px;border-radius:var(--r-full);background:var(--card);color:var(--coral);border:1.5px solid #FECACA;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:var(--shadow-sm);opacity:0;pointer-events:none;transform:translateY(10px);transition:all .3s var(--ease-spring);z-index:99;font-size:16px}
#fab-share.visible{opacity:1;pointer-events:auto;transform:translateY(0)}
#fab-share:hover{background:var(--coral-bg);transform:translateY(-2px) scale(1.05)}

/* ===== Reading Progress Tip ===== */
.read-progress-tip{position:fixed;bottom:28px;left:50%;transform:translateX(-50%);background:rgba(15,23,42,.85);backdrop-filter:blur(12px);color:#fff;font-size:11px;padding:6px 16px;border-radius:var(--r-full);pointer-events:none;opacity:0;transition:opacity .4s;z-index:98;white-space:nowrap}
.read-progress-tip.show{opacity:1}

@media print{
  body{max-width:100%;background:#fff;color:#000;padding:0}
  .sticky-header,#progress-bar,#back-to-top,#fab-share,.read-progress-tip{display:none!important}
  .hero{background:#FF5E62!important;color:#fff!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .news-card,.stat-card,.tip-card{box-shadow:none!important;border:1px solid #e5e7eb!important;break-inside:avoid}
  .news-card{opacity:1!important;transform:none!important}
  .tip-card{opacity:1!important;transform:none!important}
}
@media(max-width:640px){
  body{padding:0 14px}
  .hero{padding:32px 22px;border-radius:var(--r-lg)}
  .hero h1{font-size:24px}
  .stats-row{grid-template-columns:1fr;gap:10px}
  .tips-grid{grid-template-columns:1fr;gap:10px}
  .sticky-nav a{font-size:11px;padding:3px 7px}
  #back-to-top,#fab-share{right:14px}
}
'''


# ═══════════════════════════════════════════════
# JS 模板 — V5 完整版所有交互
# ═══════════════════════════════════════════════
JS_TEMPLATE = r'''
// ===== 🔙 Scroll Position Save/Restore v3 ====
(function(){
  var STORAGE_KEY = '_daily_rpt_state';
  function getCardAnchor(){
    var cards = document.querySelectorAll('.news-card:not(.filtered-out)');
    var best = undefined, bestDist = Infinity;
    for(var i=0;i<cards.length;i++){
      var rect = cards[i].getBoundingClientRect();
      if(rect.top <= window.innerHeight*0.6 && rect.bottom > -80){
        var dist = Math.abs(rect.top);
        if(dist < bestDist){ bestDist = dist; best = cards[i].getAttribute('data-index'); }
      }
    }
    return best;
  }
  function saveState(){
    var y = window.scrollY || window.pageYOffset;
    var ci = getCardAnchor();
    try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify({y:y, ci:ci})); } catch(e){}
  }
  document.addEventListener('mousedown', function(e){
    var link = e.target.closest('a[href^="http"]');
    if(link) saveState();
  }, true);
  document.addEventListener('touchstart', function(e){
    var link = e.target.closest('a[href^="http"]');
    if(link) saveState();
  }, {passive: true});
  window.addEventListener('pagehide', saveState);
  var scrollTimer = 0;
  window.addEventListener('scroll', function(){
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(saveState, 200);
  }, {passive: true});
  window.addEventListener('pageshow', function(e){
    if(e.persisted){
      document.documentElement.classList.remove('scroll-restoring');
      delete window.__ds;
    }
  });
  if(window.__ds){
    var state = window.__ds;
    function restoreAndReveal(){
      var restored = false;
      if(state.ci !== undefined && state.ci !== null){
        var card = document.querySelector('.news-card[data-index="' + state.ci + '"]');
        if(card){
          card.scrollIntoView({block:'start', behavior:'instant'});
          window.scrollBy(0, -80);
          restored = true;
        }
      }
      if(!restored && state.y > 10){
        window.scrollTo(0, state.y);
        restored = true;
      }
      if(restored){
        setTimeout(function(){
          if(window.__ds){
            document.documentElement.classList.remove('scroll-restoring');
            delete window.__ds;
          }
        }, 80);
      }
    }
    restoreAndReveal();
    window.addEventListener('load', function(){
      if(window.__ds) restoreAndReveal();
    });
    setTimeout(function(){
      if(window.__ds){
        document.documentElement.classList.remove('scroll-restoring');
        if(window.__ds.ci !== undefined){
          var card = document.querySelector('.news-card[data-index="' + window.__ds.ci + '"]');
          if(card){ card.scrollIntoView({block:'start', behavior:'instant'}); window.scrollBy(0, -80); }
        }
        delete window.__ds;
      }
    }, 3000);
  }
})();

// ===== Progress Bar =====
(function(){
  const bar = document.getElementById('progress-bar');
  const tip = document.getElementById('readProgressTip');
  window.addEventListener('scroll',function(){
    const h = document.documentElement.scrollHeight - window.innerHeight;
    const p = h > 0 ? Math.round((window.scrollY / h) * 100) : 0;
    bar.style.width = p + '%';
    if(p > 0 && p < 100){
      tip.textContent = '已阅读 ' + p + '%';
      tip.classList.add('show');
    } else {
      tip.classList.remove('show');
    }
  });
})();

// ===== Sticky Header Scroll =====
(function(){
  const header = document.getElementById('stickyHeader');
  window.addEventListener('scroll',function(){
    header.classList.toggle('scrolled', window.scrollY > 20);
  });
})();

// ===== Sticky Nav Smooth Scroll =====
(function(){
  document.querySelectorAll('.sticky-nav a[href^="#"]').forEach(function(a){
    a.addEventListener('click',function(e){
      e.preventDefault();
      var id = this.getAttribute('href').substring(1);
      var el = document.getElementById(id);
      if(el){ el.scrollIntoView({behavior:'smooth',block:'start'}); }
    });
  });
})();

// ===== Back to Top =====
(function(){
  var btn = document.getElementById('back-to-top');
  window.addEventListener('scroll',function(){
    btn.classList.toggle('visible', window.scrollY > 400);
  });
  btn.addEventListener('click',function(){
    window.scrollTo({top:0,behavior:'smooth'});
  });
})();

// ===== FAB Share (Web Share API / Copy) =====
(function(){
  var fab = document.getElementById('fab-share');
  window.addEventListener('scroll',function(){
    fab.classList.toggle('visible', window.scrollY > 400);
  });
  fab.addEventListener('click',function(){
    var url = window.location.href;
    var title = document.title;
    if(navigator.share){
      navigator.share({title:title,url:url}).catch(function(){});
    } else {
      navigator.clipboard.writeText(title + '\n' + url).then(function(){
        fab.textContent = '✓';
        setTimeout(function(){ fab.textContent = '📤'; }, 1500);
      }).catch(function(){});
    }
  });
})();

// ===== Counter Animation + Mini Progress Bar =====
(function(){
  var animated = false;
  var observer = new IntersectionObserver(function(entries){
    entries.forEach(function(entry){
      if(entry.isIntersecting && !animated){
        animated = true;
        var cards = document.querySelectorAll('.stat-card');
        cards.forEach(function(card){
          var numEl = card.querySelector('.stat-num[data-target]');
          if(!numEl) return;
          var target = parseInt(numEl.getAttribute('data-target'),10);
          var current = 0;
          var duration = 1200;
          var step = Math.max(1, Math.ceil(target / (duration / 16)));
          var timer = setInterval(function(){
            current += step;
            if(current >= target){ current = target; clearInterval(timer); }
            numEl.textContent = current;
          }, 16);
          setTimeout(function(){
            card.classList.add('animated');
          }, duration + 200);
        });
      }
    });
  },{threshold:.3});
  var statsEl = document.getElementById('stats');
  if(statsEl){ observer.observe(statsEl); }
})();

// ===== Category Chip Filter =====
(function(){
  const chips = document.querySelectorAll('.cat-chip[data-cat]');
  const allChip = document.querySelector('.cat-chip[data-cat="all"]');
  const newsCards = document.querySelectorAll('.news-card[data-categories]');

  chips.forEach(function(chip){
    chip.addEventListener('click', function(){
      const cat = this.getAttribute('data-cat');
      if(cat === 'all'){
        chips.forEach(function(c){ c.classList.remove('active'); });
        this.classList.add('active');
        newsCards.forEach(function(card){
          card.classList.remove('filtered-out');
          card.style.animation = 'none';
          card.offsetHeight;
          card.style.animation = '';
        });
        return;
      }
      if(this.style.opacity === '0.4') return; // 无内容品类不可点击
      allChip.classList.remove('active');
      const wasActive = this.classList.contains('active');
      chips.forEach(function(c){ c.classList.remove('active'); });
      if(!wasActive){
        this.classList.add('active');
        newsCards.forEach(function(card){
          const cardCats = card.getAttribute('data-categories').split(',');
          if(cardCats.indexOf(cat) === -1){
            card.classList.add('filtered-out');
          } else {
            card.classList.remove('filtered-out');
            card.style.animation = 'chipHighlight .8s ease';
            setTimeout(function(){ card.style.animation = ''; }, 800);
          }
        });
      } else {
        allChip.classList.add('active');
        newsCards.forEach(function(card){
          card.classList.remove('filtered-out');
        });
      }
    });
  });

  // 无内容品类半透明标记（已通过 style 内联设置）
})();

// ===== News Card Collapse/Expand =====
(function(){
  document.querySelectorAll('.news-card .card-header').forEach(function(header){
    header.addEventListener('click', function(e){
      if(e.target.closest('a')) return;
      this.closest('.news-card').classList.toggle('collapsed');
    });
  });
})();

// ===== Sticky Nav Active Section Tracking =====
(function(){
  var navLinks = document.querySelectorAll('.sticky-nav a[href^="#"]');
  var sectionIds = [];
  navLinks.forEach(function(a){
    sectionIds.push(a.getAttribute('href').substring(1));
  });
  var observer = new IntersectionObserver(function(entries){
    entries.forEach(function(entry){
      if(entry.isIntersecting){
        var id = entry.target.id;
        navLinks.forEach(function(a){
          a.classList.remove('active');
          if(a.getAttribute('href') === '#' + id){
            a.classList.add('active');
          }
        });
      }
    });
  },{threshold:.3,rootMargin:'-80px 0px -60% 0px'});
  sectionIds.forEach(function(id){
    var el = document.getElementById(id);
    if(el){ observer.observe(el); }
  });
})();

// ===== Intersection Observer — 卡片入场动画 =====
(function(){
  var observer = new IntersectionObserver(function(entries){
    entries.forEach(function(entry){
      if(entry.isIntersecting){
        entry.target.classList.add('visible');
      }
    });
  },{threshold:.15,rootMargin:'0px 0px -30px 0px'});
  document.querySelectorAll('.news-card,.tip-card').forEach(function(card){
    observer.observe(card);
  });
})();

// ===== Source Link Truncation: >3 -> show 3 + expand button =====
(function(){
  document.querySelectorAll('.news-card .source-row').forEach(function(row){
    var links = row.querySelectorAll('.source-tag');
    if(links.length <= 3) return;
    row.classList.add('has-more');
    var hidden = links.length - 3;
    var btn = document.createElement('span');
    btn.className = 'source-more';
    btn.textContent = '+' + hidden + ' 更多来源 ▼';
    btn.addEventListener('click', function(e){
      e.preventDefault();
      e.stopPropagation();
      row.classList.toggle('expanded');
      btn.textContent = row.classList.contains('expanded') ? '收起 ▲' : '+' + hidden + ' 更多来源 ▼';
    });
    links[2].after(btn);
  });
})();
'''


def generate_html_report(urgent_news, important_news, reminder_news, tips, report_date, mode):
    """生成完整 HTML 报告（V5 完整版 — 匹配 2026-06-19-婴儿安全日报-v5.html）"""
    date_iso = report_date.strftime("%Y-%m-%d")
    date_display = report_date.strftime("%Y年%m月%d日")
    weekday = get_weekday_str(report_date)
    title = "婴儿安全资讯日报"

    n_urgent = len(urgent_news)
    n_important = len(important_news) + len(reminder_news)

    all_news = urgent_news + important_news + reminder_news
    cat_chips_html = build_category_chips(all_news)

    age_label = "1~2 岁"
    minutes = max(1, n_urgent + n_important + len(tips))

    # 分区卡片
    urgent_cards_html = build_news_cards_html(urgent_news, n_urgent) if n_urgent > 0 else ""
    important_cards_html = build_news_cards_html(important_news + reminder_news, 0) if n_important > 0 else ""

    # 贴士网格
    tips_html = ""
    for i, tip in enumerate(tips):
        tips_html += (
            '<div class="tip-card" data-index="' + str(i) + '">\n'
            '  <div class="tip-num">' + str(i + 1) + '</div>\n'
            '  <h4>' + tip["title"] + '</h4>\n'
            '  <p>' + tip["desc"] + '</p>\n'
            '</div>\n'
        )

    # 构建完整 HTML
    html = (
        '<!DOCTYPE html>\n'
        '<html lang="zh-CN">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">\n'
        '<meta name="color-scheme" content="light">\n'
        '<title>' + title + ' · ' + date_iso + '</title>\n'
        '<!-- 🔙 滚动恢复预处理 v3 -->\n'
        '<script>\n'
        '(function(){\n'
        '  var k=\'_daily_rpt_state\',v;try{v=sessionStorage.getItem(k)}catch(e){}\n'
        '  if(v){try{var s=JSON.parse(v);if(s.y>10||s.ci!==undefined){document.documentElement.className=\'scroll-restoring\';window.__ds=s;}}catch(e){}}\n'
        '})();\n'
        '</script>\n'
        '<style>\n'
        + CSS_TEMPLATE +
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '\n'
        '<!-- Progress Bar -->\n'
        '<div id="progress-bar"></div>\n'
        '\n'
        '<!-- Sticky Header -->\n'
        '<header class="sticky-header" id="stickyHeader">\n'
        '  <div class="sticky-header-inner">\n'
        '    <a href="#" class="sticky-logo">\n'
        '      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/></svg>\n'
        '      婴儿安全日报\n'
        '    </a>\n'
        '    <ul class="sticky-nav">\n'
        '      <li><a href="#stats"><span class="live-dot"></span>概览</a></li>\n'
        '      <li><a href="#urgent">🔴紧急</a></li>\n'
        '      <li><a href="#important">🟡重要</a></li>\n'
        '      <li><a href="#tips">💡贴士</a></li>\n'
        '    </ul>\n'
        '  </div>\n'
        '</header>\n'
        '\n'
        '<!-- Hero -->\n'
        '<section class="hero">\n'
        '  <div class="hero-dots">\n'
        '    <span></span><span></span><span></span><span></span><span></span>\n'
        '  </div>\n'
        '  <div class="hero-content">\n'
        '    <div class="hero-badge"><span class="live-dot"></span> 每日更新 · 守护宝宝安全</div>\n'
        '    <h1>' + title + '</h1>\n'
        '    <p>' + date_display + ' ' + weekday + ' · 重点关注 ' + age_label + ' · 14个安全类别覆盖</p>\n'
        '    <div class="hero-meta">\n'
        '      <span>📅 ' + date_iso + '</span>\n'
        '      <span>👶 重点：' + age_label + '</span>\n'
        '      <span>⏱️ 预计阅读 ' + str(minutes) + ' 分钟</span>\n'
        '      <span>🌐 来源：CDC · FDA · CPSC · 市场监管总局</span>\n'
        '    </div>\n'
        '  </div>\n'
        '  <svg class="hero-wave" viewBox="0 0 680 40" preserveAspectRatio="none"><path d="M0,20 C170,0 340,40 510,20 C595,10 680,0 680,0 L680,40 L0,40 Z" fill="var(--bg)" opacity=".12"/></svg>\n'
        '</section>\n'
        '\n'
        '<!-- Stats -->\n'
        '<div class="stats-row" id="stats">\n'
        '  <div class="stat-card urgent">\n'
        '    <div class="stat-icon">⚠️</div>\n'
        '    <div class="stat-num" data-target="' + str(n_urgent) + '">0</div>\n'
        '    <div class="stat-label">🔴 紧急新闻</div>\n'
        '  </div>\n'
        '  <div class="stat-card warn">\n'
        '    <div class="stat-icon">📋</div>\n'
        '    <div class="stat-num" data-target="' + str(n_important) + '">0</div>\n'
        '    <div class="stat-label">🟡 重要提醒</div>\n'
        '  </div>\n'
        '  <div class="stat-card tip">\n'
        '    <div class="stat-icon">💡</div>\n'
        '    <div class="stat-num" data-target="' + str(len(tips)) + '">0</div>\n'
        '    <div class="stat-label">💡 安全贴士</div>\n'
        '  </div>\n'
        '</div>\n'
        '\n'
        '<!-- Category Chips -->\n'
        '<div class="cat-section">\n'
        '  <div class="cat-chips" id="catChips">\n'
        + cat_chips_html +
        '  </div>\n'
        '</div>\n'
    )

    # 紧急新闻区
    if n_urgent > 0:
        html += (
            '<!-- ====== 🔴 URGENT ====== -->\n'
            '<div class="sec-title" id="urgent"><span class="dot red"></span>🔴 紧急新闻</div>\n'
            '\n'
            '<div class="news-list">\n'
            + urgent_cards_html +
            '</div><!-- /news-list -->\n'
            '\n'
        )

    # 重要提醒区
    if n_important > 0:
        html += (
            '<!-- ====== 🟡 IMPORTANT ====== -->\n'
            '<div class="sec-title" id="important"><span class="dot amber"></span>🟡 重要提醒</div>\n'
            '\n'
            '<div class="news-list">\n'
            + important_cards_html +
            '</div><!-- /news-list -->\n'
            '\n'
        )

    # 贴士区
    html += (
        '<!-- ====== 💡 TIPS ====== -->\n'
        '<div class="sec-title" id="tips"><span class="dot blue"></span>💡 本周安全贴士</div>\n'
        '\n'
        '<div class="tips-grid">\n'
        + tips_html +
        '</div>\n'
        '\n'
        '<!-- Footer -->\n'
        '<footer class="page-footer">\n'
        '  <p>📋 婴儿安全资讯日报 · ' + date_display + ' ' + weekday + ' · 由 AI 自动采集生成</p>\n'
        '  <p class="disclaimer">⚠️ 本报告仅供参考，不构成医疗或消费建议。如有安全疑虑，请咨询专业机构或拨打当地市场监管热线12315。</p>\n'
        '  <p style="margin-top:6px;font-size:11px;color:var(--text-3)">数据来源：CDC · FDA · CPSC · NHTSA · 国家市场监管总局缺陷产品召回技术中心</p>\n'
        '</footer>\n'
        '\n'
        '<!-- Back to Top -->\n'
        '<button id="back-to-top" aria-label="返回顶部" title="返回顶部">↑</button>\n'
        '\n'
        '<!-- FAB Share -->\n'
        '<button id="fab-share" aria-label="分享" title="分享日报">📤</button>\n'
        '\n'
        '<!-- Reading Progress Tip -->\n'
        '<div class="read-progress-tip" id="readProgressTip">已阅读 0%</div>\n'
        '\n'
        '<script>\n'
        + JS_TEMPLATE +
        '</script>\n'
        '\n'
        '</body>\n'
        '</html>\n'
    )
    return html


def deploy_html_report(urgent_news, important_news, reminder_news, tips, report_date, mode):
    """生成 HTML 报告并写入 docs/ 目录，返回公网可访问 URL"""
    date_str = report_date.strftime("%Y-%m-%d")
    filename = date_str + "-婴儿安全日报"
    if mode == "evening":
        filename += "-晚间更新"
    filename += ".html"

    html_content = generate_html_report(urgent_news, important_news, reminder_news, tips, report_date, mode)

    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    os.makedirs(docs_dir, exist_ok=True)

    filepath = os.path.join(docs_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("✅ HTML 报告已生成: docs/" + filename)

    # 记录推送时间到独立文件（不受 git checkout 重置 mtime 影响）
    push_ts_file = os.path.join(docs_dir, ".last_push")
    with open(push_ts_file, "w") as f:
        f.write(str(datetime.datetime.now().timestamp()))

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        url = "https://" + repo.split("/")[0] + ".github.io/" + repo.split("/")[1] + "/docs/" + filename
        return url, filepath

    return None, filepath


# ═══════════════════════════════════════════════
# 🛡️ SelfHealRunner — 无限自愈引擎
# ═══════════════════════════════════════════════

class SelfHealRunner:
    """无限自愈循环：包裹完整推送流程，失败自动诊断修复重试"""

    MAX_RETRIES = 8
    BASE_DELAY = 15
    MAX_DELAY = 300

    def __init__(self, mode):
        self.mode = mode
        self.retry_count = 0
        self.fixes_applied = []
        self.diagnosis_log = []
        self.today = datetime.date.today()
        self.is_evening = mode == "evening"

    def _log_fix(self, category, detail):
        entry = f"[自愈·{category}] {detail}"
        self.fixes_applied.append(entry)
        self.diagnosis_log.append(entry)
        print("🔧 " + entry, flush=True)

    def _diagnose(self, error_type, context):
        fixes = []
        if error_type == "empty_news":
            self._log_fix("empty_news", "0条新闻，将扩大搜索范围")
        elif error_type == "feishu_auth_fail":
            self._log_fix("feishu_auth", "飞书认证失败，将重试")
        elif error_type == "feishu_send_fail":
            self._log_fix("feishu_send", "飞书发送失败，将重试")
        elif error_type == "network_error":
            self._log_fix("network", "网络超时，增加等待时间")
        elif error_type == "exception":
            error_msg = context.get("error", "unknown") if context else "unknown"
            self._log_fix("exception", f"捕获异常: {error_msg[:80]}")
        else:
            self._log_fix("unknown", f"未知错误: {error_type}")
        return fixes

    def _attempt_push(self):
        try:
            docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
            push_ts_file = os.path.join(docs_dir, ".last_push")
            if os.path.exists(push_ts_file):
                with open(push_ts_file, "r") as f:
                    last_ts = float(f.read().strip())
                age_minutes = (datetime.datetime.now().timestamp() - last_ts) / 60
                if age_minutes < 10:
                    print("⏭️  最近推送（" + str(int(age_minutes)) + "分钟前），跳过重复推送", flush=True)
                    return (0, None, None)

            print("🚀 开始执行云端推送 (mode=" + self.mode + ", date=" + str(self.today) + ", 第" + str(self.retry_count + 1) + "次尝试)", flush=True)

            days_back = 3 if not self.is_evening else 1
            if self.retry_count >= 3:
                days_back += 2
            if self.retry_count >= 6:
                days_back += 3

            news_items = fetch_news(days_back=days_back, mode=self.mode)
            print("[TRACE] fetch_news done, " + str(len(news_items)) + " items", flush=True)

            if len(news_items) == 0:
                return (2, "empty_news", {"count": 0})

            urgent, important, reminder = format_for_report(news_items)
            print("[TRACE] format_for_report done, urgent=" + str(len(urgent)) + " important=" + str(len(important)) + " reminder=" + str(len(reminder)), flush=True)

            tips = get_tips(self.today)
            print("[TRACE] get_tips done, " + str(len(tips)) + " tips", flush=True)

            print("📄 生成 HTML 报告...", flush=True)
            cloud_url, html_path = deploy_html_report(urgent, important, reminder, tips, self.today, self.mode)
            print("[TRACE] deploy_html_report done", flush=True)
            print("   HTML 路径: " + str(html_path), flush=True)
            print("   Cloud URL: " + str(cloud_url or "(需要设置 GITHUB_REPOSITORY)"), flush=True)

            print("📤 发送飞书消息...", flush=True)
            success = send_daily_report_with_retry(
                urgent_news=urgent,
                important_news=important,
                reminder_news=reminder,
                tips=tips,
                cloud_url=cloud_url or "",
                report_date=self.today,
                is_evening=self.is_evening,
            )

            if success:
                print("✅ 推送完成！", flush=True)
                return (0, None, None)
            else:
                return (2, "feishu_send_fail", {"success": False})

        except Exception as e:
            return (2, "exception", {"error": str(e)})

    def run(self):
        print("=" * 60, flush=True)
        print("🛡️ SelfHealRunner 启动 (mode=" + self.mode + ")", flush=True)
        print("   最大重试: " + str(self.MAX_RETRIES) + " 次", flush=True)
        print("   退避策略: " + str(self.BASE_DELAY) + "s × 2^attempt", flush=True)
        print("=" * 60, flush=True)

        for attempt in range(1, self.MAX_RETRIES + 1):
            self.retry_count = attempt - 1
            print("\n--- 第 " + str(attempt) + "/" + str(self.MAX_RETRIES) + " 次尝试 ---", flush=True)

            exit_code, error_type, context = self._attempt_push()

            if exit_code == 0:
                print("\n🎉 推送成功！（第" + str(attempt) + "次尝试）", flush=True)
                if self.fixes_applied:
                    print("🔧 应用过的修复:", flush=True)
                    for fix_item in self.fixes_applied:
                        print("   " + fix_item, flush=True)
                return 0

            self._diagnose(error_type, context or {})

            delay = min(self.BASE_DELAY * (2 ** (attempt - 1)), self.MAX_DELAY)
            print("⏳ 等待 " + str(delay) + " 秒后重试...", flush=True)
            time.sleep(delay)

        print("\n" + "=" * 60, flush=True)
        print("🆘 自愈循环耗尽！" + str(self.MAX_RETRIES) + "次重试全部失败", flush=True)
        for entry in self.diagnosis_log:
            print("   " + entry, flush=True)

        diag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SELFHEAL_FAILED.log")
        with open(diag_file, "w") as f:
            f.write("SelfHealRunner exhausted after " + str(self.MAX_RETRIES) + " retries\n")
            f.write("Mode: " + self.mode + "\n")
            for e in self.diagnosis_log:
                f.write("  " + e + "\n")

        print("📝 诊断日志已写入 SELFHEAL_FAILED.log", flush=True)
        return 2


def main():
    parser = argparse.ArgumentParser(description="婴儿安全资讯云端推送")
    parser.add_argument("--mode", choices=["morning", "evening"], required=True, help="morning=早间版, evening=晚间版")
    parser.add_argument("--self-heal", action="store_true", help="启用自愈循环（失败自动重试）")
    parser.add_argument("--force", action="store_true", help="跳过幂等保护，强制重新推送")
    args = parser.parse_args()

    today = datetime.date.today()
    is_evening = args.mode == "evening"

    # 幂等保护（使用 .last_push 文件，不受 git checkout 重置 mtime 影响）
    if not args.force:
        docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
        push_ts_file = os.path.join(docs_dir, ".last_push")
        if os.path.exists(push_ts_file):
            with open(push_ts_file, "r") as f:
                last_ts = float(f.read().strip())
            age_minutes = (datetime.datetime.now().timestamp() - last_ts) / 60
            if age_minutes < 10:
                print("⏭️  最近推送（" + str(int(age_minutes)) + "分钟前），跳过重复推送", flush=True)
                return 0
            else:
                print("⏳ 上次推送已超过（" + str(int(age_minutes)) + "分钟前），重新生成", flush=True)

    if args.self_heal:
        runner = SelfHealRunner(args.mode)
        return runner.run()

    print("🚀 开始执行云端推送 (mode=" + args.mode + ", date=" + str(today) + ")", flush=True)

    news_items = fetch_news(days_back=3 if not is_evening else 1, mode=args.mode)
    print("[TRACE] fetch_news done, " + str(len(news_items)) + " items", flush=True)

    urgent, important, reminder = format_for_report(news_items)
    print("[TRACE] format_for_report done, urgent=" + str(len(urgent)) + " important=" + str(len(important)) + " reminder=" + str(len(reminder)), flush=True)

    tips = get_tips(today)
    print("[TRACE] get_tips done, " + str(len(tips)) + " tips", flush=True)

    print("📄 生成 HTML 报告...", flush=True)
    cloud_url, html_path = deploy_html_report(urgent, important, reminder, tips, today, args.mode)
    print("[TRACE] deploy_html_report done", flush=True)
    print("   HTML 路径: " + str(html_path), flush=True)
    print("   Cloud URL: " + str(cloud_url or "(需要设置 GITHUB_REPOSITORY)"), flush=True)

    print("📤 发送飞书消息...", flush=True)
    success = send_daily_report_with_retry(
        urgent_news=urgent,
        important_news=important,
        reminder_news=reminder,
        tips=tips,
        cloud_url=cloud_url or "",
        report_date=today,
        is_evening=is_evening,
    )

    if success:
        print("✅ 推送完成！", flush=True)
        return 0
    else:
        print("❌ 推送失败（可能是凭证未配置）", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
