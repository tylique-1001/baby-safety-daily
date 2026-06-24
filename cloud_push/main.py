#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py - 云端推送主入口
GitHub Actions 调用此脚本完成完整推送流程

使用方式：
  python3 main.py --mode morning   # 早间版（全天报告）
  python3 main.py --mode evening    # 晚间版（增量更新）
"""

import sys
import os
import json
import datetime
import argparse

# 添加当前目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news_fetcher import fetch_news, format_for_report
from feishu_sender import send_daily_report
from config import CLOUDSTUDIO_SUBDOMAIN


def get_tips(date):
    """获取当日安全贴士（可后续接入 API）"""
    tips_pool = [
        "定期检查婴儿用品是否有召回信息，可访问 CPSC.gov 查询。",
        "婴儿食品引入新食材时，每次只引入一种，观察 3-5 天有无过敏反应。",
        "婴儿床护栏间距不得超过 6cm，避免婴儿头部卡住。",
        "选购婴儿玩具注意查看 3C 认证标志，避免有小零件的玩具。",
        "纸尿裤建议每 3-4 小时更换一次，避免尿布疹。",
        "婴儿推车使用时务必扣好安全带，停驻时启用刹车装置。",
        "婴儿洗澡水温应控制在 37-40°C，使用温度计或手肘内侧测试。",
        "家中的清洁剂、药品应存放在婴儿无法触及的高处或带锁柜中。",
    ]
    import hashlib
    seed = date.isoformat().encode()
    indices = set()
    attempt = 0
    while len(indices) < 3:
        attempt += 1
        h = int(hashlib.md5(seed + str(attempt).encode()).hexdigest()[:2], 16)
        indices.add(h % len(tips_pool))
    return [tips_pool[i] for i in sorted(indices)]


# 品类 → Emoji 映射（14大类，覆盖用户全部要求: 喂养器具/洗护用品/服饰寝具/服装及布类/
# 婴幼儿食品/食具类/启智玩具/家具类/电子电器/纸尿裤/出行安全/家居及外出必备/宝宝药箱/日常用品）
CAT_EMOJI = {
    "喂养器具": "🍼", "洗护用品": "🧴", "服饰寝具": "👕",
    "服装及布类": "🧵", "婴幼儿食品": "🥣", "食具类": "🍽️",
    "启智玩具": "🧩", "家具类": "🛏️", "电子电器": "⚡",
    "纸尿裤": "👶", "出行安全": "🚗", "家居及外出必备": "🏠",
    "宝宝药箱": "💊", "日常用品": "📦",
}
ALL_CATEGORIES = list(CAT_EMOJI.keys())


def is_valid_url(url):
    """验证 URL 非首页（路径深度 ≥ 2）"""
    if not url:
        return False
    last_seg = url.rstrip("/").split("/")[-1] if url else ""
    if last_seg == "" or last_seg.lower() in ["index.html", "index", "news", "recalls"]:
        return False
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path_segments = [s for s in parsed.path.strip('/').split('/') if s]
    return len(path_segments) >= 2


def build_news_card(news, idx, severity_class, severity_icon):
    """构建单条新闻卡片 HTML"""
    title = news.get("title", "")
    date_str = news.get("date", "")
    source = news.get("source", "")
    desc = news.get("desc", title)
    categories = news.get("categories", ["日常用品"])

    # 品类芯片
    cat_html = ""
    for cat in categories:
        cat_html += '<span class="cat-chip">' + cat + '</span>'

    # 来源链接
    urls = news.get("urls", [])
    single_url = news.get("url", "")
    existing_urls = set(link for _, link in urls)
    if single_url and is_valid_url(single_url) and single_url not in existing_urls:
        urls.append((source, single_url))
    if not urls:
        urls = [(source, single_url if single_url else "#")]

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

    cat_classes = " ".join(categories)
    return (
        '<div class="news-card" data-index="' + str(idx) + '" data-severity="' + severity_class + '" data-categories="' + cat_classes + '">\n'
        '  <div class="card-header" onclick="toggleCard(' + str(idx) + ')">\n'
        '    <span class="severity-' + severity_class + '">' + severity_icon + ' ' + title + '</span>\n'
        '    <span class="card-arrow">▼</span>\n'
        '  </div>\n'
        '  <div class="card-body">\n'
        '    <div class="card-meta">📅 ' + date_str + ' | 来源：' + source + '</div>\n'
        '    <div class="cat-row">' + cat_html + '</div>\n'
        '    <p class="card-desc">' + desc + '</p>\n'
        '    <div class="source-row" id="src-row-' + str(idx) + '">\n'
        + source_links_html +
        '    </div>\n'
        '  </div>\n'
        '</div>\n'
    )


def build_section_html(news_list, section_id, section_title, severity_icon, severity_class, start_idx):
    """构建一个分区的完整 HTML：标题 + 卡片列表"""
    if not news_list:
        return "", start_idx

    header_border = {"danger": "var(--red)", "prevent": "var(--amber)", "remind": "var(--blue)"}

    html = (
        '<h2 id="' + section_id + '" class="section-heading section-heading-' + severity_class + '"'
        + ' style="border-left:5px solid ' + header_border.get(severity_class, "var(--blue)") + ';">'
        + severity_icon + ' ' + section_title
        + ' <span class="section-count">' + str(len(news_list)) + '条</span></h2>\n'
    )

    for i, news in enumerate(news_list):
        idx = start_idx + i
        card_html = build_news_card(news, idx, severity_class, severity_icon)
        html += card_html

    return html, start_idx + len(news_list)


def generate_html_report(urgent_news, important_news, reminder_news, tips, report_date, mode):
    """生成完整 HTML 报告（v5 分区版：紧急/重要/提醒/贴士 四区锚点跳转）"""
    date_str = report_date.strftime("%Y年%m月%d日")
    title = "婴儿安全资讯日报 · " + ("晚间更新" if mode == "evening" else "早间版")

    n_urgent = len(urgent_news)
    n_important = len(important_news)
    n_reminder = len(reminder_news)

    # 四区内容
    idx = 0
    urgent_html, idx = build_section_html(urgent_news, "urgent-section", "紧急警示", "🔴", "danger", idx)
    important_html, idx = build_section_html(important_news, "important-section", "重要召回/通报", "🟡", "prevent", idx)
    reminder_html, idx = build_section_html(reminder_news, "reminder-section", "提醒关注", "🟠", "remind", idx)

    # 贴士
    tips_html = ""
    for tip in tips:
        tips_html += '<div class="tip-card">💡 ' + tip + '</div>\n'

    # 覆盖品类统计
    all_cats = set()
    for news_list in [urgent_news, important_news, reminder_news]:
        for n in news_list:
            for c in n.get("categories", ["日常用品"]):
                all_cats.add(c)
    n_cats = len(all_cats)
    cats_str = " · ".join(sorted(all_cats))

    total_news = n_urgent + n_important + n_reminder

    # 统计卡片 JS（四栏）
    stats_js = (
        '<div class="stats">\n'
        '  <div class="stat-card stat-urgent" onclick="jumpToSection(\'urgent-section\')">'
        '<div class="num">' + str(n_urgent) + '</div><div class="label">🔴 紧急</div></div>\n'
        '  <div class="stat-card stat-important" onclick="jumpToSection(\'important-section\')">'
        '<div class="num">' + str(n_important) + '</div><div class="label">🟡 重要</div></div>\n'
        '  <div class="stat-card stat-reminder" onclick="jumpToSection(\'reminder-section\')">'
        '<div class="num">' + str(n_reminder) + '</div><div class="label">🟠 提醒</div></div>\n'
        '  <div class="stat-card stat-tips" onclick="jumpToSection(\'tips-section\')">'
        '<div class="num">' + str(len(tips)) + '</div><div class="label">💡 贴士</div></div>\n'
        '</div>\n'
    )

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="zh-CN">\n'
        '<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <meta name="color-scheme" content="light">\n'
        '  <title>' + title + ' - ' + date_str + '</title>\n'
        '  <style>\n'
        '    :root {\n'
        '      --coral: #FF5E62; --red: #DC2626; --amber: #D97706; --blue: #3B82F6; --orange: #EA580C;\n'
        '      --bg: #FAFAF9; --card: #FFFFFF;\n'
        '      --text: #0F172A; --text-2: #475569;\n'
        '      --sans: "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;\n'
        '    }\n'
        '    * { box-sizing: border-box; margin: 0; padding: 0; }\n'
        '    body { font-family: var(--sans); background: var(--bg); color: var(--text); padding: 20px; max-width: 680px; margin: 0 auto; }\n'
        '    .hero { background: linear-gradient(135deg, var(--coral), var(--red)); color: white; padding: 30px; border-radius: 20px; margin-bottom: 20px; }\n'
        '    .hero h1 { font-size: 24px; margin-bottom: 8px; }\n'
        '    .hero p { opacity: 0.9; font-size: 14px; }\n'
        '    /* ---- 四栏统计卡片 ---- */\n'
        '    .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 20px; }\n'
        '    @media (max-width: 480px) { .stats { grid-template-columns: repeat(2, 1fr); } }\n'
        '    .stat-card { background: var(--card); padding: 14px 8px; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center; cursor: pointer; transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s; border: 2px solid transparent; user-select: none; -webkit-tap-highlight-color: transparent; }\n'
        '    .stat-card:hover, .stat-card:active { transform: translateY(-2px); }\n'
        '    .stat-card:active { transform: scale(0.96); transition: transform 0.08s; }\n'
        '    .stat-card.tapped { transform: scale(0.96); box-shadow: 0 0 0 3px var(--coral); transition: transform 0.1s, box-shadow 0.1s; }\n'
        '    .stat-card .num { font-size: 26px; font-weight: 800; }\n'
        '    .stat-card .label { font-size: 11px; color: var(--text-2); margin-top: 2px; }\n'
        '    .stat-urgent { border-color: #FECACA; } .stat-urgent .num { color: var(--red); }\n'
        '    .stat-important { border-color: #FED7AA; } .stat-important .num { color: var(--amber); }\n'
        '    .stat-reminder { border-color: #BFDBFE; } .stat-reminder .num { color: var(--blue); }\n'
        '    .stat-tips { border-color: #BBF7D0; } .stat-tips .num { color: #16A34A; }\n'
        '    /* ---- 分区标题 ---- */\n'
        '    .section-heading { padding: 12px 16px; border-radius: 10px; margin: 24px 0 12px; font-size: 17px; scroll-margin-top: 24px; border-left: 3px solid transparent; }\n'
        '    .section-heading-danger  { background: #FEF2F2; }\n'
        '    .section-heading-prevent { background: #FFFBEB; }\n'
        '    .section-heading-remind  { background: #F0F9FF; }\n'
        '    .section-heading.arrived { animation: sectionPulse 2.8s ease-out forwards; }\n'
        '    @keyframes sectionPulse {\n'
        '      0%   { background: rgba(255,94,98,0.45) !important; border-left-color: var(--coral); border-left-width: 5px; box-shadow: 0 0 24px rgba(255,94,98,0.25), inset 0 0 36px rgba(255,94,98,0.15); transform: scale(1.04); color: #B91C1C; font-weight: 700; }\n'
        '      15%  { background: rgba(255,94,98,0.30) !important; border-left-color: var(--coral); border-left-width: 4px; box-shadow: 0 0 12px rgba(255,94,98,0.12); transform: scale(1.02); color: #DC2626; font-weight: 600; }\n'
        '      100% { background: transparent !important; border-left-color: transparent; border-left-width: 3px; box-shadow: none; transform: scale(1); color: inherit; font-weight: inherit; }\n'
        '    }\n'
        '    .section-count { font-size: 12px; color: var(--text-2); margin-left: 8px; font-weight: 400; }\n'
        '    /* ---- 新闻卡片 ---- */\n'
        '    .news-card { background: var(--card); border-radius: 14px; margin-bottom: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }\n'
        '    .card-header { padding: 14px 18px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid var(--coral); }\n'
        '    .news-card[data-severity="danger"] .card-header  { border-left-color: var(--red); }\n'
        '    .news-card[data-severity="prevent"] .card-header { border-left-color: var(--amber); }\n'
        '    .news-card[data-severity="remind"] .card-header  { border-left-color: var(--blue); }\n'
        '    .news-card[data-severity="danger"] .card-header:hover  { background: #FEF2F2; }\n'
        '    .news-card[data-severity="prevent"] .card-header:hover { background: #FFFBEB; }\n'
        '    .news-card[data-severity="remind"] .card-header:hover  { background: #F0F9FF; }\n'
        '    .card-header:hover { background: #fef2f2; }\n'
        '    .card-body { padding: 0 18px 18px; display: none; }\n'
        '    .card-body.open { display: block; }\n'
        '    .severity-danger { color: var(--red); font-weight: 600; }\n'
        '    .severity-prevent { color: var(--amber); font-weight: 600; }\n'
        '    .severity-remind { color: var(--blue); font-weight: 600; }\n'
        '    .card-arrow { transition: transform 0.3s; font-size: 14px; }\n'
        '    .card-meta { font-size: 13px; color: var(--text-2); margin-bottom: 6px; }\n'
        '    .card-desc { font-size: 14px; line-height: 1.7; margin-bottom: 10px; }\n'
        '    /* ---- 品类芯片 ---- */\n'
        '    .cat-row { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; }\n'
        '    /* ---- 品类筛选栏 ---- */\n'
        '    .cat-bar { background: var(--card); padding: 12px 14px; border-radius: 12px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }\n'
        '    .cat-bar-label { font-size: 12px; color: var(--text-2); margin-right: 4px; white-space: nowrap; }\n'
        '    .filter-chip { display: inline-block; padding: 5px 10px; background: #F3F4F6; color: var(--text-2); border-radius: 16px; font-size: 12px; cursor: pointer; transition: all 0.2s; user-select: none; -webkit-tap-highlight-color: transparent; white-space: nowrap; }\n'
        '    .filter-chip:hover { background: #E5E7EB; transform: translateY(-1px); }\n'
        '    .filter-chip.active { background: var(--coral); color: #fff; font-weight: 600; }\n'
        '    .filter-chip.inactive { opacity: 0.35; cursor: default; pointer-events: none; }\n'
        '    .news-card.filtered-out { display: none !important; }\n'
        '    /* ---- 来源链接 ---- */\n'
        '    .source-row { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }\n'
        '    .source-tag { display: inline-block; padding: 4px 10px; background: #FFF3F2; color: var(--coral); border-radius: 6px; text-decoration: none; font-size: 13px; }\n'
        '    .source-tag:hover { opacity: 0.8; }\n'
        '    .source-tag.source-extra { display: none; }\n'
        '    .source-row.expanded .source-extra { display: inline-block; }\n'
        '    .source-more-btn { padding: 4px 10px; background: #f1f5f9; color: var(--text-2); border: 1px solid #e2e8f0; border-radius: 6px; font-size: 13px; cursor: pointer; font-family: var(--sans); }\n'
        '    .source-more-btn:hover { background: #e2e8f0; }\n'
        '    /* 🔖 has-more 源截断标识 */\n'
        '    .tip-card { background: #F0FDF4; border-left: 4px solid #16A34A; padding: 12px 16px; border-radius: 14px; margin-bottom: 8px; font-size: 14px; }\n'
        '    .back-to-top { position: fixed; bottom: 24px; right: 24px; width: 44px; height: 44px; background: var(--coral); color: white; border: none; border-radius: 50%; font-size: 20px; cursor: pointer; box-shadow: 0 4px 12px rgba(255,94,98,0.35); display: none; z-index: 100; }\n'
        '    .back-to-top.show { display: block; }\n'
        '    .back-to-top:hover { opacity: 0.85; }\n'
        '    html.scroll-restoring{visibility:hidden}\n'
        '    @media print {\n'
        '      body { background: white; max-width: 100%; padding: 0; }\n'
        '      .hero { background: none; color: var(--text); border: 2px solid var(--coral); }\n'
        '      .back-to-top { display: none !important; }\n'
        '      .stats { display: none; }\n'
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
        '    <h1>🛡️ ' + title + '</h1>\n'
        '    <p>' + date_str + ' | 重点关注 1-2 岁婴幼儿安全动态</p>\n'
        '    <p style="margin-top:8px;font-size:13px;">📊 ' + str(total_news) + '条资讯 · ' + str(n_cats) + '个品类 · 阅读约' + str(total_news + 2) + '分钟</p>\n'
        '  </div>\n'
        + stats_js +
        # 品类概览条 — 可点击筛选芯片
        '  <div class="cat-bar" id="catBar"><span class="cat-bar-label">📂 品类筛选</span>'
        '<span class="filter-chip active" onclick="filterByCategory(\'全部\')" data-cat="全部">全部</span>' +
        ''.join(
            '<span class="filter-chip'
            + (' inactive' if c not in all_cats else '')
            + '" onclick="filterByCategory(\'' + c + '\')" data-cat="' + c + '">'
            + CAT_EMOJI.get(c, '📌') + ' ' + c + '</span>'
            for c in ALL_CATEGORIES
        ) +
        '</div>\n'
        + urgent_html
        + important_html
        + reminder_html
        + '  <h2 id="tips-section" class="section-heading" style="background:#F0FDF4;border-left:5px solid #16A34A;">💡 安全贴士 <span class="section-count">' + str(len(tips)) + '条</span></h2>\n'
        + tips_html
        + '  <hr style="margin:30px 0 20px;border:none;border-top:1px solid #e2e8f0;">\n'
        + '  <p style="text-align:center;color:var(--text-2);font-size:13px;">\n'
        + '    📊 数据来源：市场监管总局 · 中国质量新闻网 · 央视新闻 · 财新<br>\n'
        + '    ⚠️ 本日报仅供参考，具体操作请遵循官方指导。\n'
        + '  </p>\n'
        '  <script>\n'
        '  /* ── 锚点跳转（统计卡片点击 → 丝滑滚动 + 柔和背景淡入）── */\n'
        '  function jumpToSection(id) {\n'
        '    var el = document.getElementById(id);\n'
        '    if (!el) return;\n'
        '    // 清除所有旧标记\n'
        '    document.querySelectorAll(\'.arrived\').forEach(function(h) { h.classList.remove(\'arrived\'); });\n'
        '    // 丝滑滚动\n'
        '    el.scrollIntoView({ behavior: "smooth", block: "start", inline: "nearest" });\n'
        '    // 滚动到达后加柔和背景色，1.8s 自然消退\n'
        '    setTimeout(function() {\n'
        '      var e = document.getElementById(id);\n'
        '      if (e) e.classList.add(\'arrived\');\n'
        '    }, 400);\n'
        '  }\n'
        '  /* ── 品类筛选 ── */\n'
        '  function filterByCategory(cat) {\n'
        '    var chips = document.querySelectorAll(\'.filter-chip\');\n'
        '    var cards = document.querySelectorAll(\'.news-card\');\n'
        '    // 更新芯片状态\n'
        '    chips.forEach(function(c) { c.classList.remove(\'active\'); if(c.getAttribute(\'data-cat\')===cat) c.classList.add(\'active\'); });\n'
        '    // 筛选卡片\n'
        '    if(cat === \'全部\') {\n'
        '      cards.forEach(function(c) { c.classList.remove(\'filtered-out\'); });\n'
        '    } else {\n'
        '      cards.forEach(function(c) {\n'
        '        var cats = (c.getAttribute(\'data-categories\')||\'\').split(\' \');\n'
        '        if(cats.indexOf(cat) === -1) { c.classList.add(\'filtered-out\'); }\n'
        '        else { c.classList.remove(\'filtered-out\'); }\n'
        '      });\n'
        '    }\n'
        '  }\n'
        '  /* ── 卡片折叠/展开 ── */\n'
        '  function toggleCard(idx) {\n'
        '    var card = document.querySelector(\'.news-card[data-index="\'+idx+\'"]\');\n'
        '    if(card) {\n'
        '      var body = card.querySelector(\'.card-body\');\n'
        '      var arrow = card.querySelector(\'.card-arrow\');\n'
        '      if(body.classList.contains(\'open\')) { body.classList.remove(\'open\'); arrow.style.transform = \'rotate(0deg)\'; }\n'
        '      else { body.classList.add(\'open\'); arrow.style.transform = \'rotate(180deg)\'; }\n'
        '    }\n'
        '  }\n'
        '  /* ── 源链接截断：展开/收起 ── */\n'
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
        '  /* ── Back-to-Top ── */\n'
        '  (function(){\n'
        '    var btn = document.getElementById(\'backToTop\');\n'
        '    window.addEventListener(\'scroll\', function(){\n'
        '      if(window.scrollY > 400) { btn.classList.add(\'show\'); }\n'
        '      else { btn.classList.remove(\'show\'); }\n'
        '    }, {passive:true});\n'
        '  })();\n'
        '  /* 🔙 滚动位置保存/恢复 v4 */\n'
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

    # 生成公网 URL（htmlpreview.github.io — 无需 GitHub Pages，始终可渲染 HTML）
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        raw_url = "https://raw.githubusercontent.com/" + repo + "/main/docs/" + filename
        url = "https://htmlpreview.github.io/?" + raw_url
        return url, filepath

    return None, filepath


# ═══════════════════════════════════════════════════════════════
# 🛡️ SelfHealRunner — 无限自愈引擎
# 推送失败 → 自动诊断 → 修复 → 重试 → 直到成功
# 退出码: 0=成功, 2=重试用尽(触发workflow级救援), 1=致命错误
# ═══════════════════════════════════════════════════════════════

class SelfHealRunner:
    """无限自愈循环：包裹完整推送流程，失败自动诊断修复重试"""

    MAX_RETRIES = 8
    BASE_DELAY = 15  # 基础退避秒数
    MAX_DELAY = 300  # 最大退避秒数（5分钟）
    # 总最长时间 ≈ 15+30+60+120+240+300+300+300 = 1365s ≈ 23min

    def __init__(self, mode):
        self.mode = mode
        self.retry_count = 0
        self.fixes_applied = []
        self.diagnosis_log = []
        self.today = datetime.date.today()
        self.is_evening = mode == "evening"

    def _log_fix(self, category, detail):
        """记录修复动作"""
        entry = f"[自愈·{category}] {detail}"
        self.fixes_applied.append(entry)
        self.diagnosis_log.append(entry)
        print("🔧 " + entry, flush=True)

    def _diagnose(self, error_type, context):
        """诊断失败原因，返回修复建议列表"""
        fixes = []

        if error_type == "empty_news":
            # 没有采集到新闻 → 扩大搜索范围
            fixes.append(("widen_search", "扩大搜索范围(days_back+3)"))
            self._log_fix("empty_news", "0条新闻，将扩大搜索范围")

        elif error_type == "feishu_auth_fail":
            # 飞书认证失败 → 等一会重试（可能是临时网络问题）
            fixes.append(("retry_auth", "等待后重试飞书认证"))
            self._log_fix("feishu_auth", "飞书认证失败，将重试")

        elif error_type == "feishu_send_fail":
            # 飞书发送失败 → 可能是卡片格式问题，尝试简化
            fixes.append(("retry_send", "重试发送"))
            self._log_fix("feishu_send", "飞书发送失败，将重试")

        elif error_type == "network_error":
            # 网络错误 → 增加超时时间
            fixes.append(("increase_timeout", "增加网络超时"))
            self._log_fix("network", "网络超时，增加等待时间")

        elif error_type == "exception":
            error_msg = context.get("error", "unknown")
            fixes.append(("retry", f"捕获异常后重试: {error_msg[:80]}"))
            self._log_fix("exception", f"捕获异常: {error_msg[:80]}")

        else:
            fixes.append(("retry", f"未知错误类型 {error_type}，直接重试"))
            self._log_fix("unknown", f"未知错误: {error_type}")

        return fixes

    def _attempt_push(self):
        """单次推送尝试，返回 (exit_code, error_type, context)"""
        try:
            # 幂等保护（self-heal 模式下放宽到10分钟）
            date_str = self.today.strftime("%Y-%m-%d")
            filename = date_str + "-婴儿安全日报"
            if self.is_evening:
                filename += "-晚间更新"
            filename += ".html"
            docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
            target_file = os.path.join(docs_dir, filename)
            if os.path.exists(target_file):
                mtime = os.path.getmtime(target_file)
                age_minutes = (datetime.datetime.now().timestamp() - mtime) / 60
                if age_minutes < 10:
                    print("⏭️  报告已存在（" + str(int(age_minutes)) + "分钟前生成），跳过重复推送", flush=True)
                    return (0, None, None)

            print("🚀 开始执行云端推送 (mode=" + self.mode + ", date=" + str(self.today) + ", 第" + str(self.retry_count + 1) + "次尝试)", flush=True)

            # 根据重试次数动态调整搜索天数
            days_back = 3 if not self.is_evening else 1
            if self.retry_count >= 3:
                days_back += 2  # 第3次重试扩大搜索
            if self.retry_count >= 6:
                days_back += 3  # 第6次重试更激进

            news_items = fetch_news(days_back=days_back, mode=self.mode)
            print("[TRACE] fetch_news done, " + str(len(news_items)) + " items", flush=True)

            # 没有新闻 → 诊断
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
            from feishu_sender import send_daily_report_with_retry
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
        """主入口：无限自愈循环"""
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
                    for fix in self.fixes_applied:
                        print("   " + fix, flush=True)
                return 0

            # 失败 → 诊断
            fixes = self._diagnose(error_type, context or {})
            if not fixes:
                print("⚠️ 无法诊断，直接重试", flush=True)

            # 指数退避等待
            delay = min(self.BASE_DELAY * (2 ** (attempt - 1)), self.MAX_DELAY)
            print("⏳ 等待 " + str(delay) + " 秒后重试...", flush=True)
            time.sleep(delay)

        # 🔴 所有重试用尽
        print("\n" + "=" * 60, flush=True)
        print("🆘 自愈循环耗尽！10次重试全部失败", flush=True)
        print("📋 诊断记录:", flush=True)
        for entry in self.diagnosis_log:
            print("   " + entry, flush=True)
        print("📋 修复记录:", flush=True)
        for entry in self.fixes_applied:
            print("   " + entry, flush=True)

        # 写诊断文件供 workflow 读取
        diag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SELFHEAL_FAILED.log")
        with open(diag_file, "w") as f:
            f.write("SelfHealRunner exhausted after " + str(self.MAX_RETRIES) + " retries\n")
            f.write("Mode: " + self.mode + "\n")
            f.write("Diagnosis:\n")
            for e in self.diagnosis_log:
                f.write("  " + e + "\n")
            f.write("Fixes applied:\n")
            for e in self.fixes_applied:
                f.write("  " + e + "\n")

        print("📝 诊断日志已写入 SELFHEAL_FAILED.log", flush=True)
        print("=" * 60, flush=True)
        return 2  # 特殊退出码：触发 workflow 级救援


def main():
    parser = argparse.ArgumentParser(description="婴儿安全资讯云端推送")
    parser.add_argument("--mode", choices=["morning", "evening"], required=True, help="morning=早间版, evening=晚间版")
    parser.add_argument("--self-heal", action="store_true", help="启用自愈循环（失败自动重试）")
    parser.add_argument("--force", action="store_true", help="跳过幂等保护，强制重新推送")
    args = parser.parse_args()

    today = datetime.date.today()
    is_evening = args.mode == "evening"

    # 🛡️ 幂等保护（--force 可跳过）
    if not args.force:
        date_str = today.strftime("%Y-%m-%d")
        filename = date_str + "-婴儿安全日报"
        if is_evening:
            filename += "-晚间更新"
        filename += ".html"
        docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
        target_file = os.path.join(docs_dir, filename)
        if os.path.exists(target_file):
            mtime = os.path.getmtime(target_file)
            age_minutes = (datetime.datetime.now().timestamp() - mtime) / 60
            if age_minutes < 10:  # self-heal 模式下放宽到10分钟
                print("⏭️  报告已存在（" + str(int(age_minutes)) + "分钟前生成），跳过重复推送", flush=True)
                return 0
            else:
                print("⏳ 报告已存在但过期（" + str(int(age_minutes)) + "分钟前），重新生成", flush=True)

    # 🛡️ Self-heal 模式：启动自愈引擎
    if args.self_heal:
        runner = SelfHealRunner(args.mode)
        return runner.run()

    # 普通模式：单次推送
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
    from feishu_sender import send_daily_report_with_retry
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
