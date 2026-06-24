#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急手动推送 — 2026-06-24 婴儿安全日报
严格过滤：仅婴儿安全相关，无垃圾新闻
"""

import json
import os
import subprocess
import sys
import datetime
from urllib.parse import urlparse

# ═══ 配置 ═══
USER_ID = "ou_e61d62d0f233b8c91fc56ea461f88f0c"
TODAY = datetime.date(2026, 6, 24)
DATE_STR = "2026-06-24"
DATE_DISPLAY = "2026年06月24日"
WEEKDAY = "周三"
AGE = "1~2 岁"
MODE = "evening"  # 晚间更新版

# ═══ 新闻数据 — 仅婴儿安全相关，每条含真实原文链接 ═══

URGENT_NEWS = [
    {
        "title": "FDA调查婴儿肉毒杆菌爆发：Nara Organics全线召回有机婴儿配方奶粉 — 3例确诊、3州受影响",
        "source": "FDA",
        "date": "06-13/14",
        "desc": "FDA与CDC联合加州公共卫生部调查多州婴儿肉毒杆菌爆发。3例确诊/疑似A型肉毒毒素感染（加州、宾州、华盛顿州），发病时间2026年4-5月，全部3例均食用Nara Organics婴儿配方奶粉。6月13日Nara Organics同意召回全部批次产品。该品牌在Target线上线下及Nara.com销售，不涉及中国市场。",
        "severity": "urgent",
        "symptom": "便秘、喂养困难、头部控制力丧失、吞咽困难，可进展为呼吸困难甚至呼吸停止",
        "prevent": "立即停止使用Nara Organics婴儿配方奶粉；保留开封奶粉至少一个月供检测",
        "action": "如宝宝已食用并出现上述症状→立即就医；接触过奶粉的物品用热肥皂水清洗",
        "urls": [
            ("FDA 官方通告", "https://www.fda.gov/food/outbreaks-foodborne-illness/outbreak-investigation-infant-botulism-powdered-infant-formula-june-2026"),
        ]
    },
    {
        "title": "CPSC召回CooCooBaby婴儿躺椅：窒息与跌落风险，违反婴儿睡眠产品强制标准",
        "source": "CPSC",
        "date": "06-19",
        "desc": "CooCooBaby婴儿躺椅（Baby Loungers）因违反婴儿睡眠产品强制安全标准被召回。产品存在严重窒息和跌落风险，可能导致婴儿死亡。消费者应立即停止使用并联系品牌退款。",
        "severity": "urgent",
        "symptom": "婴儿在躺椅中可能翻身导致口鼻被遮挡→窒息；可能从躺椅跌落→头部外伤",
        "prevent": "婴儿睡眠应使用符合安全标准的婴儿床，不使用躺椅作为睡眠替代品",
        "action": "立即停用CooCooBaby婴儿躺椅→联系品牌办理退款",
        "urls": [
            ("CPSC 召回详情", "https://www.cpsc.gov/Recalls/2026/CooCooBaby-Baby-Loungers-Recalled-Due-to-Risk-of-Serious-Injury-or-Death-from-Suffocation-and-Fall-Hazards-Violates-Mandatory-Standard-for-Infant-Sleep-Products"),
        ]
    },
    {
        "title": "CPSC召回GOPO拉绳磨牙玩具：窒息风险，违反玩具强制安全标准",
        "source": "CPSC",
        "date": "06-19",
        "desc": "GOPO Toys召回拉绳式磨牙玩具（Pull String Teething Toys），产品含有小零件且拉绳过长，存在严重窒息甚至死亡风险。违反玩具强制安全标准。消费者应立即停止使用。",
        "severity": "urgent",
        "symptom": "拉绳过长可能缠绕婴儿颈部→勒颈窒息；小零件脱落→气道阻塞窒息",
        "prevent": "选择磨牙玩具时确认无小零件、拉绳长度<7cm，检查3C认证",
        "action": "立即停用GOPO拉绳磨牙玩具→检查家中所有磨牙玩具的安全性",
        "urls": [
            ("CPSC 召回详情", "https://www.cpsc.gov/Recalls/2026/GOPO-Toys-Recalls-Pull-String-Teething-Toys-Due-to-Risk-of-Serious-Injury-or-Death-from-Choking-Violate-Mandatory-Standard-for-Toys"),
        ]
    },
    {
        "title": "CPSC召回BABESIDE娃娃与推车玩具：小零件窒息风险，违反小型部件禁令",
        "source": "CPSC",
        "date": "06-19",
        "desc": "BABESIDE品牌娃娃与推车儿童玩具因含有小零件被召回，存在严重窒息甚至死亡风险。产品通过HYBDOLLS店铺在Amazon销售，违反小型部件禁令。消费者应立即停止使用。",
        "severity": "urgent",
        "symptom": "玩具小零件脱落被婴幼儿误吞→气道阻塞→窒息",
        "prevent": "购买玩具前做\"卫生纸卷筒测试\"：能塞入卷筒的小零件有窒息风险",
        "action": "立即停用BABESIDE娃娃推车玩具→远离3岁以下婴幼儿",
        "urls": [
            ("CPSC 召回详情", "https://www.cpsc.gov/Recalls/2026/BABESIDE-Doll-and-Stroller-Childrens-Toys-Recalled-Due-to-Risk-of-Serious-Injury-or-Death-from-Choking-Hazard-Violate-Small-Parts-Ban-Sold-on-Amazon-by-HYBDOLLS"),
        ]
    },
    {
        "title": "CPSC召回Joolz Aer2婴儿车适配器：跌倒/受伤风险",
        "source": "CPSC",
        "date": "06-19",
        "desc": "Joolz召回Aer2婴儿车汽车安全座椅适配器（Car Seat Adapters），适配器可能意外脱落导致婴儿跌倒受伤。消费者应停止使用并联系品牌更换。",
        "severity": "urgent",
        "symptom": "安全座椅适配器脱落→婴儿连同安全座椅从推车坠落→头部/身体外伤",
        "prevent": "每次安装安全座椅适配器时检查卡扣是否完全锁定，听到\"咔嗒\"声确认",
        "action": "立即停用Joolz Aer2适配器→联系Joolz免费更换",
        "urls": [
            ("CPSC 召回详情", "https://www.cpsc.gov/Recalls/2026/Joolz-Recalls-Aer2-Car-Seat-Adapters-for-Strollers-Due-to-Risk-of-Serious-Injury-from-Fall-Hazard"),
        ]
    },
]

IMPORTANT_NEWS = [
    {
        "title": "Veseacky儿童睡衣套装召回：严重烧伤风险，违反联邦阻燃强制标准",
        "source": "CPSC",
        "date": "06-19",
        "desc": "Veseacky品牌儿童睡衣套装因违反美国联邦儿童睡衣可燃性标准（16 CFR 1615/1616）被召回，存在严重烧伤甚至死亡风险。消费者应立即停用并联系品牌全额退款。",
        "severity": "important",
        "symptom": "睡衣接触火源后迅速燃烧→严重烧伤",
        "prevent": "选购儿童睡衣时确认标签注明\"低易燃性\"标志，避免购买无合规标签产品",
        "action": "立即停用Veseacky睡衣→检查宝宝所有睡衣的阻燃标签",
        "urls": [
            ("CPSC 召回详情", "https://www.cpsc.gov/Recalls/2026/Veseacky-Pajama-Sets-Recalled-Due-to-Risk-of-Serious-Injury-or-Death-from-Burn-Hazard-Violate-Mandatory-Standards-for-Childrens-Sleepwear"),
        ]
    },
    {
        "title": "SHEIN召回Michley儿童睡衣：烧伤风险，违反联邦阻燃标准",
        "source": "CPSC",
        "date": "06-19",
        "desc": "SHEIN旗下Michley品牌儿童睡衣因违反联邦儿童睡衣可燃性标准被召回。产品在接触火源时可能迅速燃烧，造成严重烧伤或死亡。消费者应立即停用。",
        "severity": "important",
        "symptom": "睡衣材质易燃→接触火源→严重烧伤",
        "prevent": "避免在电商平台购买无阻燃标签的廉价儿童睡衣",
        "action": "立即停用SHEIN/Michley儿童睡衣→申请退款",
        "urls": [
            ("CPSC 召回详情", "https://www.cpsc.gov/Recalls/2026/SHEIN-Distribution-Corporation-Recalls-Michley-Childrens-Pajamas-Due-to-Risk-of-Serious-Injury-or-Death-from-Burn-Hazard-Violate-Mandatory-Standard-for-Childrens-Sleepwear"),
        ]
    },
    {
        "title": "中国造纸学会就纸尿裤甲酰胺事件声明：市面在售产品安全可控，报道检测信息缺失",
        "source": "中国造纸学会",
        "date": "06-19",
        "desc": "针对《经济参考报》6月18日报道好奇、碧芭宝贝、Babycare等纸尿裤检出甲酰胺，中国造纸学会声明：报道未披露检测方法、数值、机构等核心信息，不具备科学依据；涉事品牌已委托CMA资质第三方检测均未检出甲酰胺。造纸学会将组织行业甲酰胺风险专项自查。",
        "severity": "important",
        "symptom": "长期接触甲酰胺可致皮肤刺激、过敏反应，属1B类生殖毒性物质",
        "prevent": "关注官方抽检结果与标准修订进展，选择正规渠道购买纸尿裤",
        "action": "保留纸尿裤购买凭证→关注市场监管总局后续通报→如宝宝反复红臀及时就医",
        "urls": [
            ("中国造纸学会声明", "https://baijiahao.baidu.com/s?id=1868422937374110920"),
        ]
    },
]

TIPS = [
    {"emoji": "🍼", "title": "奶粉安全自查", "desc": "检查家中婴儿奶粉品牌及批次，关注FDA/市场监管总局召回公告；开封奶粉密封冷藏保存，4周内用完"},
    {"emoji": "🛏️", "title": "婴儿睡眠安全", "desc": "1-2岁宝宝应睡在符合安全标准的婴儿床上，不使用躺椅/沙发作为睡眠替代品；床垫与护栏间缝隙不超过两指宽"},
    {"emoji": "🧸", "title": "磨牙玩具三查", "desc": "一查拉绳长度<7cm，二查无小零件脱落风险，三查3C认证标志；GOPO召回警示"},
]

CATEGORIES_ACTIVE = ["🍼婴幼儿食品", "🧸启智玩具", "👕服饰寝具", "🚼出行安全", "👶纸尿裤"]
CATEGORIES_TOTAL = 13

N_URGENT = len(URGENT_NEWS)
N_IMPORTANT = len(IMPORTANT_NEWS)
N_TIPS = len(TIPS)
N_ACTIVE_CATS = len(CATEGORIES_ACTIVE)
N_INACTIVE = CATEGORIES_TOTAL - N_ACTIVE_CATS

# ═══════════════════════════════════════════════
# 🔒 URL 硬验证
# ═══════════════════════════════════════════════

HOMEPAGE_PATTERNS = [
    r'^https?://[^/]+/?$',
    r'^https?://www\.fda\.gov/?$',
    r'^https?://www\.fda\.gov/safety/?$',
    r'^https?://www\.fda\.gov/safety/recalls/?$',
    r'^https?://www\.cpsc\.gov/?$',
    r'^https?://www\.cpsc\.gov/Recalls/?$',
    r'^https?://www\.samr\.gov\.cn/?$',
    r'^https?://www\.cdc\.gov/?$',
    r'^https?://baijiahao\.baidu\.com/?$',
]

def validate_url(url, label=""):
    import re
    # 首页模式检查
    for pattern in HOMEPAGE_PATTERNS:
        if re.match(pattern, url):
            return False, f"🚫 {label} → 疑似首页: {url}"
    parsed = urlparse(url)
    path_segments = [s for s in parsed.path.strip('/').split('/') if s]
    # 路径≥2级 OR 有查询参数(如百家号 s?id=xxx) 视为有效
    if len(path_segments) >= 2:
        return True, ""
    if parsed.query and len(parsed.query) > 10:
        # 查询参数足够长视为具体文章
        return True, ""
    return False, f"🚫 {label} → 路径过短({len(path_segments)}级)且无有效查询参数: {url}"

def validate_all_urls():
    errors = []
    for i, news in enumerate(URGENT_NEWS):
        for label, url in news.get('urls', []):
            ok, reason = validate_url(url, f"紧急[{i}] {label}")
            if not ok:
                errors.append(reason)
    for i, news in enumerate(IMPORTANT_NEWS):
        for label, url in news.get('urls', []):
            ok, reason = validate_url(url, f"重要[{i}] {label}")
            if not ok:
                errors.append(reason)
    if errors:
        print("❌ URL 验证失败:")
        for e in errors:
            print(f"   {e}")
        sys.exit(1)
    print("🔒 URL 验证通过 ✓")

validate_all_urls()

# ═══════════════════════════════════════════════
# 📄 生成 HTML 报告 (V4.4 Lumin 风格)
# ═══════════════════════════════════════════════

def is_valid_url(url):
    if not url:
        return False
    last_seg = url.rstrip("/").split("/")[-1] if url else ""
    if last_seg == "" or last_seg.lower() in ["index.html", "index", "news", "recalls"]:
        return False
    parsed = urlparse(url)
    path_segments = [s for s in parsed.path.strip('/').split('/') if s]
    return len(path_segments) >= 2

def build_news_cards_html(news_list, n_urgent=0):
    cards_html = ""
    for idx, news in enumerate(news_list):
        is_urgent = news.get("severity") == "urgent"
        severity_class = "danger" if is_urgent else "prevent"
        severity_icon = "🔴" if is_urgent else "🟡"
        title = news.get("title", "")
        date_str = news.get("date", "")
        source = news.get("source", "")
        desc = news.get("desc", title)

        urls = news.get("urls", [])
        if not urls:
            single_url = news.get("url", "")
            if single_url and is_valid_url(single_url):
                urls = [(source, single_url)]
            else:
                urls = [(source, "#")]

        url_count = len(urls)
        max_visible = 3
        source_links_html = ""
        for j, (label, link) in enumerate(urls):
            extra_class = " source-extra" if j >= max_visible else ""
            source_links_html += (
                '      <a href="' + link + '" target="_blank" rel="noopener" class="source-tag' + extra_class + '">'
                '📖 ' + label + '</a>\n'
            )
        if url_count > max_visible:
            source_links_html += (
                '      <button class="source-more-btn has-more" onclick="toggleMoreSources(event,' + str(idx) + ')">'
                '📋 +' + str(url_count - max_visible) + ' 更多来源 ▼</button>\n'
            )

        # 锚点ID — 统计卡片点击跳转
        anchor_attr = ""
        if idx == 0 and n_urgent > 0:
            anchor_attr = ' id="urgent-anchor"'
        elif idx == n_urgent and n_urgent > 0 and idx < len(news_list):
            anchor_attr = ' id="important-anchor"'
        elif idx == 0 and n_urgent == 0:
            anchor_attr = ' id="important-anchor"'

        # 症状/预防/行动标签
        tags_html = ""
        if news.get('symptom'):
            tags_html += '<span class="info-tag">🩺 ' + news['symptom'][:60] + '</span> '
        if news.get('prevent'):
            tags_html += '<span class="info-tag">🛡️ ' + news['prevent'][:60] + '</span> '
        if news.get('action'):
            tags_html += '<span class="info-tag">✅ ' + news['action'][:60] + '</span>'

        card = (
            '<div class="news-card"' + anchor_attr + ' data-index="' + str(idx) + '">\n'
            '  <div class="card-header" onclick="toggleCard(' + str(idx) + ')">\n'
            '    <span class="severity-' + severity_class + '">' + severity_icon + ' ' + title + '</span>\n'
            '    <span class="card-arrow">▼</span>\n'
            '  </div>\n'
            '  <div class="card-body">\n'
            '    <p>📅 ' + date_str + ' | 来源：' + source + '</p>\n'
            '    <p>' + desc + '</p>\n'
        )
        if tags_html:
            card += '    <p style="margin-top:10px;">' + tags_html + '</p>\n'
        card += (
            '    <div class="source-row" id="src-row-' + str(idx) + '">\n'
            + source_links_html +
            '    </div>\n'
            '  </div>\n'
            '</div>\n'
        )
        cards_html += card
    return cards_html

def generate_html():
    title = "🛡️ 婴儿安全资讯日报 · 晚间更新"
    news_cards_html = build_news_cards_html(URGENT_NEWS + IMPORTANT_NEWS, n_urgent=N_URGENT)

    tips_html = ""
    for tip in TIPS:
        tips_html += '<div class="tip-card">' + tip['emoji'] + ' <b>' + tip['title'] + '</b> · ' + tip['desc'] + '</div>\n'

    total_items = N_URGENT + N_IMPORTANT
    urgent_target = "urgent-anchor" if N_URGENT > 0 else "important-anchor"
    important_target = "important-anchor"

    return (
        '<!DOCTYPE html>\n'
        '<html lang="zh-CN">\n'
        '<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <meta name="color-scheme" content="light">\n'
        '  <title>' + title + ' - ' + DATE_DISPLAY + '</title>\n'
        '  <style>\n'
        '    :root {\n'
        '      --coral: #FF5E62; --red: #DC2626; --amber: #D97706; --blue: #3B82F6;\n'
        '      --bg: #FAFAF9; --card: #FFFFFF;\n'
        '      --text: #0F172A; --text-2: #475569;\n'
        '      --sans: "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;\n'
        '    }\n'
        '    * { box-sizing: border-box; margin: 0; padding: 0; }\n'
        '    body { font-family: var(--sans); background: var(--bg); color: var(--text); padding: 20px; max-width: 680px; margin: 0 auto; }\n'
        '    .hero { background: linear-gradient(135deg, var(--coral), var(--red)); color: white; padding: 30px; border-radius: 20px; margin-bottom: 20px; }\n'
        '    .hero h1 { font-size: 24px; margin-bottom: 8px; }\n'
        '    .hero p { opacity: 0.9; font-size: 14px; }\n'
        '    .stats { display: flex; gap: 12px; margin-bottom: 20px; }\n'
        '    .stat-card { flex: 1; background: var(--card); padding: 16px; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }\n'
        '    .stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(255,94,98,0.18); }\n'
        '    .stat-card .num { font-size: 28px; font-weight: 700; color: var(--coral); }\n'
        '    .stat-card .label { font-size: 12px; color: var(--text-2); }\n'
        '    .news-card { background: var(--card); border-radius: 14px; margin-bottom: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }\n'
        '    .card-header { padding: 14px 18px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid var(--coral); }\n'
        '    .card-header:hover { background: #fef2f2; }\n'
        '    .card-body { padding: 0 18px 18px; display: none; }\n'
        '    .card-body.open { display: block; }\n'
        '    .severity-danger { color: var(--red); font-weight: 600; }\n'
        '    .severity-prevent { color: var(--amber); font-weight: 600; }\n'
        '    .card-arrow { transition: transform 0.3s; }\n'
        '    .source-row { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }\n'
        '    .source-tag { display: inline-block; padding: 4px 10px; background: #FFF3F2; color: var(--coral); border-radius: 6px; text-decoration: none; font-size: 13px; }\n'
        '    .source-tag:hover { opacity: 0.8; }\n'
        '    .source-tag.source-extra { display: none; }\n'
        '    .source-row.expanded .source-extra { display: inline-block; }\n'
        '    .source-more-btn { padding: 4px 10px; background: #f1f5f9; color: var(--text-2); border: 1px solid #e2e8f0; border-radius: 6px; font-size: 13px; cursor: pointer; font-family: var(--sans); }\n'
        '    .source-more-btn:hover { background: #e2e8f0; }\n'
        '    /* 🔖 has-more 源截断标识 */\n'
        '    .info-tag { display: inline-block; padding: 2px 8px; background: #fef3c7; border-radius: 4px; font-size: 12px; margin: 2px; }\n'
        '    .tip-card { background: #EFF6FF; border-left: 4px solid var(--blue); padding: 12px 16px; border-radius: 14px; margin-bottom: 8px; font-size: 14px; }\n'
        '    .back-to-top { position: fixed; bottom: 24px; right: 24px; width: 44px; height: 44px; background: var(--coral); color: white; border: none; border-radius: 50%; font-size: 20px; cursor: pointer; box-shadow: 0 4px 12px rgba(255,94,98,0.35); display: none; z-index: 100; }\n'
        '    .back-to-top.show { display: block; }\n'
        '    .back-to-top:hover { opacity: 0.85; }\n'
        '    html.scroll-restoring{visibility:hidden}\n'
        '    @media print {\n'
        '      body { background: white; max-width: 100%; padding: 0; }\n'
        '      .hero { background: none; color: var(--text); border: 2px solid var(--coral); }\n'
        '      .back-to-top { display: none !important; }\n'
        '      .news-card { break-inside: avoid; box-shadow: none; border: 1px solid #e2e8f0; }\n'
        '      .card-body { display: block !important; }\n'
        '      .card-arrow { display: none; }\n'
        '      .source-more-btn { display: none; }\n'
        '      .source-extra { display: inline-block !important; }\n'
        '    }\n'
        '  </style>\n'
        '  <script>\n'
        '  (function(){\n'
        '    var k="_daily_rpt_state",v;try{v=sessionStorage.getItem(k)}catch(e){}\n'
        '    if(v){try{var s=JSON.parse(v);if(s.y>10||s.ci!==undefined){document.documentElement.className="scroll-restoring";window.__ds=s;}}catch(e){}}\n'
        '  })();\n'
        '  </script>\n'
        '</head>\n'
        '<body>\n'
        '  <button class="back-to-top" id="backToTop" onclick="window.scrollTo({top:0,behavior:\'smooth\'})" title="返回顶部">↑</button>\n'
        '  <div class="hero">\n'
        '    <h1>' + title + '</h1>\n'
        '    <p>' + DATE_DISPLAY + ' ' + WEEKDAY + ' | 重点关注 1-2 岁婴幼儿安全动态</p>\n'
        '    <p style="margin-top:8px;font-size:13px;">⏱️ 阅读时长约 ' + str(total_items + 2) + ' 分钟</p>\n'
        '  </div>\n'
        '  <div class="stats">\n'
        '    <div class="stat-card" onclick="(function(){var el=document.getElementById(\'' + urgent_target + '\');if(el){el.scrollIntoView({behavior:\'smooth\',block:\'start\'});setTimeout(function(){window.scrollBy(0,-20)},100)}})()"><div class="num">' + str(N_URGENT) + '</div><div class="label">🔴 紧急</div></div>\n'
        '    <div class="stat-card" onclick="(function(){var el=document.getElementById(\'' + important_target + '\');if(el){el.scrollIntoView({behavior:\'smooth\',block:\'start\'});setTimeout(function(){window.scrollBy(0,-20)},100)}})()"><div class="num">' + str(N_IMPORTANT) + '</div><div class="label">🟡 重要</div></div>\n'
        '    <div class="stat-card" onclick="(function(){var el=document.getElementById(\'tips-section\');if(el){el.scrollIntoView({behavior:\'smooth\',block:\'start\'});setTimeout(function(){window.scrollBy(0,-20)},100)}})()"><div class="num">' + str(N_TIPS) + '</div><div class="label">💡 贴士</div></div>\n'
        '  </div>\n'
        '  <h2 id="news-section" style="margin:20px 0 12px;font-size:18px;">📰 安全资讯</h2>\n'
        + news_cards_html +
        '  <h2 id="tips-section" style="margin:20px 0 12px;font-size:18px;">💡 安全贴士</h2>\n'
        + tips_html +
        '  <hr style="margin:30px 0 20px;border:none;border-top:1px solid #e2e8f0;">\n'
        '  <p style="text-align:center;color:var(--text-2);font-size:13px;">\n'
        '    📊 数据来源：FDA · CPSC · 中国造纸学会 · 市场监管总局<br>\n'
        '    ⚠️ 本日报仅供参考，具体操作请遵循官方指导。\n'
        '  </p>\n'
        '  <script>\n'
        '  function toggleCard(idx) {\n'
        '    var card = document.querySelector(\'.news-card[data-index="\'+idx+\'"]\');\n'
        '    if(card) {\n'
        '      var body = card.querySelector(\'.card-body\');\n'
        '      var arrow = card.querySelector(\'.card-arrow\');\n'
        '      if(body.classList.contains(\'open\')) { body.classList.remove(\'open\'); arrow.style.transform = \'rotate(0deg)\'; }\n'
        '      else { body.classList.add(\'open\'); arrow.style.transform = \'rotate(180deg)\'; }\n'
        '    }\n'
        '  }\n'
        '  function toggleMoreSources(e, idx) {\n'
        '    e.stopPropagation();\n'
        '    var row = document.getElementById(\'src-row-\' + idx);\n'
        '    if(row) {\n'
        '      var btn = row.querySelector(\'.source-more-btn\');\n'
        '      if(row.classList.contains(\'expanded\')) {\n'
        '        row.classList.remove(\'expanded\');\n'
        '        if(btn) btn.innerHTML = btn.innerHTML.replace(\'▲\', \'▼\');\n'
        '      } else {\n'
        '        row.classList.add(\'expanded\');\n'
        '        if(btn) btn.innerHTML = btn.innerHTML.replace(\'▼\', \'▲\');\n'
        '      }\n'
        '    }\n'
        '  }\n'
        '  // Back-to-Top\n'
        '  (function(){\n'
        '    var btn = document.getElementById(\'backToTop\');\n'
        '    window.addEventListener(\'scroll\', function(){\n'
        '      if(window.scrollY > 400) { btn.classList.add(\'show\'); }\n'
        '      else { btn.classList.remove(\'show\'); }\n'
        '    }, {passive:true});\n'
        '  })();\n'
        '  // 🔙 滚动位置保存/恢复 v3\n'
        '  (function(){\n'
        '    var STORAGE_KEY = \'_daily_rpt_state\';\n'
        '    function getCardAnchor() {\n'
        '      var cards = document.querySelectorAll(\'.news-card\');\n'
        '      var best = undefined, bestDist = Infinity;\n'
        '      for(var i=0;i<cards.length;i++) {\n'
        '        var rect = cards[i].getBoundingClientRect();\n'
        '        if(rect.top <= window.innerHeight*0.6 && rect.bottom > -80) {\n'
        '          var dist = Math.abs(rect.top);\n'
        '          if(dist < bestDist) { bestDist = dist; best = cards[i].getAttribute(\'data-index\'); }\n'
        '        }\n'
        '      }\n'
        '      return best;\n'
        '    }\n'
        '    function saveState() {\n'
        '      var y = window.scrollY || window.pageYOffset;\n'
        '      var ci = getCardAnchor();\n'
        '      try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify({y:y, ci:ci})); } catch(e){}\n'
        '    }\n'
        '    document.addEventListener(\'mousedown\', function(e) {\n'
        '      var link = e.target.closest(\'a[href^="http"]\');\n'
        '      if(link) saveState();\n'
        '    }, true);\n'
        '    window.addEventListener(\'touchstart\', function(e) {\n'
        '      var link = e.target.closest(\'a[href^="http"]\');\n'
        '      if(link) saveState();\n'
        '    }, {passive:true});\n'
        '    window.addEventListener(\'pagehide\', saveState);\n'
        '    var scrollTimer = 0;\n'
        '    window.addEventListener(\'scroll\', function() {\n'
        '      clearTimeout(scrollTimer);\n'
        '      scrollTimer = setTimeout(saveState, 200);\n'
        '    }, {passive:true});\n'
        '    window.addEventListener(\'pageshow\', function(e){\n'
        '      if(e.persisted) { document.documentElement.classList.remove(\'scroll-restoring\'); delete window.__ds; }\n'
        '    });\n'
        '    if(window.__ds) {\n'
        '      var state = window.__ds;\n'
        '      function restore() {\n'
        '        if(state.ci !== undefined && state.ci !== null) {\n'
        '          var card = document.querySelector(\'.news-card[data-index="\'+state.ci+\'"]\');\n'
        '          if(card) { card.scrollIntoView({block:\'start\', behavior:\'instant\'}); window.scrollBy(0,-80); }\n'
        '        }\n'
        '        setTimeout(function() {\n'
        '          if(window.__ds) { document.documentElement.classList.remove(\'scroll-restoring\'); delete window.__ds; }\n'
        '        }, 80);\n'
        '      }\n'
        '      restore();\n'
        '      window.addEventListener(\'load\', restore);\n'
        '      setTimeout(function() {\n'
        '        if(window.__ds) document.documentElement.classList.remove(\'scroll-restoring\');\n'
        '      }, 3000);\n'
        '    }\n'
        '  })();\n'
        '  </script>\n'
        '</body>\n'
        '</html>\n'
    )

# ═══════════════════════════════════════════════
# 📁 保存文件
# ═══════════════════════════════════════════════

os.makedirs("outputs/daily-reports", exist_ok=True)
os.makedirs("outputs/wechat-articles", exist_ok=True)

html_content = generate_html()
html_path = "outputs/daily-reports/" + DATE_STR + "-婴儿安全日报.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print("✅ HTML 报告: " + html_path + " (" + str(len(html_content)) + " chars)")

# Markdown 版本
md_lines = []
md_lines.append("# 🛡️ 婴儿安全资讯日报 · 晚间更新")
md_lines.append("")
md_lines.append("**" + DATE_DISPLAY + " " + WEEKDAY + "** | 重点关注 1-2 岁婴幼儿安全动态")
md_lines.append("")
md_lines.append("> 今日概况：🔴 紧急 " + str(N_URGENT) + " 项 · 🟡 重要 " + str(N_IMPORTANT) + " 项 · 💡 贴士 " + str(N_TIPS) + " 条")
md_lines.append("")
md_lines.append("---")
md_lines.append("")
md_lines.append("## 🔴 紧急安全警示")
md_lines.append("")
for i, news in enumerate(URGENT_NEWS):
    md_lines.append("### " + str(i+1) + ". " + news['title'])
    md_lines.append("")
    md_lines.append("📅 " + news['date'] + " | 来源：" + news['source'])
    md_lines.append("")
    md_lines.append(news['desc'])
    md_lines.append("")
    if news.get('symptom'):
        md_lines.append("- 🩺 症状：" + news['symptom'])
    if news.get('prevent'):
        md_lines.append("- 🛡️ 预防：" + news['prevent'])
    if news.get('action'):
        md_lines.append("- ✅ 行动：" + news['action'])
    md_lines.append("")
    for label, url in news.get('urls', []):
        md_lines.append("- 📖 [" + label + "](" + url + ")")
    md_lines.append("")

md_lines.append("---")
md_lines.append("")
md_lines.append("## 🟡 重要安全提醒")
md_lines.append("")
for i, news in enumerate(IMPORTANT_NEWS):
    md_lines.append("### " + str(i+1) + ". " + news['title'])
    md_lines.append("")
    md_lines.append("📅 " + news['date'] + " | 来源：" + news['source'])
    md_lines.append("")
    md_lines.append(news['desc'])
    md_lines.append("")
    for label, url in news.get('urls', []):
        md_lines.append("- 📖 [" + label + "](" + url + ")")
    md_lines.append("")

md_lines.append("---")
md_lines.append("")
md_lines.append("## 💡 安全贴士")
md_lines.append("")
for tip in TIPS:
    md_lines.append("- " + tip['emoji'] + " **" + tip['title'] + "**：" + tip['desc'])
md_lines.append("")
md_lines.append("---")
md_lines.append("")
md_lines.append("📊 数据来源：FDA · CPSC · 中国造纸学会 | ⚠️ 仅供参考")

md_path = "outputs/wechat-articles/" + DATE_STR + "-婴儿安全日报.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))
print("✅ MD 版本: " + md_path)

# ═══════════════════════════════════════════════
# 📤 构建飞书卡片 V9
# ═══════════════════════════════════════════════

elements = []

# 引语
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": (
        "🔍 晚间推送 · 新增 **" + str(N_URGENT) + "** 条紧急 + **" + str(N_IMPORTANT) + "** 条重要 · 截至21:00"
    )}
})

# 三栏统计
elements.append({
    "tag": "column_set",
    "flex_mode": "none",
    "background_style": "default",
    "columns": [
        {
            "tag": "column", "width": "weighted", "weight": 1,
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": (
                "🚨 **紧急**\n" + str(N_URGENT) + " 项\n需立即行动"
            )}}]
        },
        {
            "tag": "column", "width": "weighted", "weight": 1,
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": (
                "📌 **提醒**\n" + str(N_IMPORTANT) + " 项\n值得关注"
            )}}]
        },
        {
            "tag": "column", "width": "weighted", "weight": 1,
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": (
                "💡 **贴士**\n" + str(N_TIPS) + " 条\n" + AGE + "适用"
            )}}]
        }
    ]
})
elements.append({"tag": "hr"})

# 紧急
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "🔴 **紧急安全警示** — 请立即检查"}
})

for news in URGENT_NEWS:
    card_lines = []
    card_lines.append("**" + news['title'] + "**")
    card_lines.append(news['source'] + " · " + news['date'])
    card_lines.append("")
    card_lines.append(news['desc'])
    card_lines.append("")
    if news.get('symptom'):
        card_lines.append("🩺 症状：" + news['symptom'])
    if news.get('prevent'):
        card_lines.append("🛡️ 预防：" + news['prevent'])
    if news.get('action'):
        card_lines.append("✅ 行动：" + news['action'])

    elements.append({
        "tag": "column_set",
        "flex_mode": "none",
        "background_style": "grey",
        "columns": [{
            "tag": "column", "width": "weighted", "weight": 1,
            "elements": [{
                "tag": "div",
                "text": {"tag": "lark_md", "content": "\n".join(card_lines)}
            }]
        }]
    })

    url_buttons = []
    for label, url in news.get('urls', []):
        url_buttons.append({
            "tag": "button",
            "text": {"tag": "lark_md", "content": "📋 " + label},
            "type": "danger",
            "url": url,
            "multi_url": {"url": url}
        })
    elements.append({
        "tag": "action",
        "actions": url_buttons
    })

elements.append({"tag": "hr"})

# 重要
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "🟡 **重要安全提醒** — 值得关注"}
})

imp_lines = []
for i, news in enumerate(IMPORTANT_NEWS):
    imp_lines.append("**" + str(i+1) + ". " + news['title'] + "**")
    imp_lines.append("　　" + news['source'] + " · " + news['date'])
    imp_lines.append("　　" + news['desc'])
    if i < len(IMPORTANT_NEWS) - 1:
        imp_lines.append("")

elements.append({
    "tag": "column_set",
    "flex_mode": "none",
    "background_style": "grey",
    "columns": [{
        "tag": "column", "width": "weighted", "weight": 1,
        "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(imp_lines)}}]
    }]
})

elements.append({
    "tag": "action",
    "actions": [
        {
            "tag": "button",
            "text": {"tag": "lark_md", "content": "📋 " + n['source'] + " 原文"},
            "type": "default",
            "url": n['urls'][0][1],
            "multi_url": {"url": n['urls'][0][1]}
        }
        for n in IMPORTANT_NEWS
    ]
})

elements.append({"tag": "hr"})

# 品类覆盖
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": (
        "📰 **品类覆盖** · " + str(N_ACTIVE_CATS) + " 类活跃 · " + str(N_INACTIVE) + " 类今日暂无新增"
    )}
})
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "  |  ".join(CATEGORIES_ACTIVE)}
})

elements.append({"tag": "hr"})

# 贴士
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "💡 **每日安全贴士** · " + AGE}
})

for tip in TIPS:
    elements.append({
        "tag": "column_set",
        "flex_mode": "none",
        "background_style": "grey",
        "columns": [{
            "tag": "column", "width": "weighted", "weight": 1,
            "elements": [{
                "tag": "div",
                "text": {"tag": "lark_md", "content": tip['emoji'] + " **" + tip['title'] + "** · " + tip['desc']}
            }]
        }]
    })

elements.append({"tag": "hr"})

# CTA
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "📱 以上为 " + str(N_URGENT + N_IMPORTANT) + " 条资讯摘要 · 完整图文请见下方"}
})

# CTA URL will be set after CloudStudio deploy
cta_url = "https://htmlpreview.github.io/?https://raw.githubusercontent.com/" + os.environ.get("GITHUB_REPOSITORY", "zltang/daily-baby-safety") + "/main/docs/" + DATE_STR + "-婴儿安全日报.html"

elements.append({
    "tag": "action",
    "actions": [{
        "tag": "button",
        "text": {"tag": "lark_md", "content": "📖 查看完整图文日报"},
        "type": "primary",
        "url": cta_url,
        "multi_url": {"url": cta_url}
    }]
})

elements.append({"tag": "hr"})
elements.append({
    "tag": "note",
    "elements": [{
        "tag": "lark_md",
        "content": "📡 FDA · CPSC · 中国造纸学会 · 市场监管总局 | ⚠️ 仅供参考 · 紧急情况请立即就医 | V9"
    }]
})

# ═══ 组装卡片 ═══
card = {
    "config": {"wide_screen_mode": True},
    "header": {
        "template": "carmine",
        "title": {
            "tag": "plain_text",
            "content": "🛡️ 婴儿安全资讯日报 · " + DATE_DISPLAY + " " + WEEKDAY
        }
    },
    "elements": elements
}

card_json = json.dumps(card, ensure_ascii=False)
card_path = "outputs/feishu_card_" + DATE_STR + ".json"
with open(card_path, "w", encoding="utf-8") as f:
    f.write(card_json)
print("✅ 飞书卡片 JSON: " + card_path + " (" + str(len(card_json)) + " chars)")

# ═══════════════════════════════════════════════
# ✅ 质量关卡
# ═══════════════════════════════════════════════

print("\n🔍 质量关卡验证...")

# 1. URL 验证
print("  1. URL 非首页验证...", end=" ")
validate_all_urls()
print("  ✅")

# 2. HTML 含滚动恢复
with open(html_path, "r") as f:
    html = f.read()
has_ds = "__ds" in html
print("  2. HTML 滚动恢复 v3: " + ("✅" if has_ds else "❌"))

# 3. HTML 含源截断
has_more = "has-more" in html
print("  3. HTML 源截断代码: " + ("✅" if has_more else "❌"))

# 4. target=_blank
blank_count = html.count('target="_blank"')
print("  4. source-tag target=_blank: " + ("✅ (" + str(blank_count) + ")" if blank_count > 0 else "❌"))

# 5. 飞书卡片 JSON 可解析
try:
    with open(card_path, "r") as f:
        json.loads(f.read())
    print("  5. 飞书卡片 JSON 无报错: ✅")
except Exception as e:
    print("  5. 飞书卡片 JSON 错误: ❌ " + str(e))

print("\n📄 生成文件:")
print("  HTML: " + html_path)
print("  MD:   " + md_path)
print("  JSON: " + card_path)
print("\n🚀 准备通过 lark-cli 发送飞书卡片...")
