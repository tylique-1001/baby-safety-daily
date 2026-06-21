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
    while len(indices) < 3:
        h = int(hashlib.md5(seed + len(indices).to_bytes(1, 'big')).hexdigest()[:2], 16)
        indices.add(h % len(tips_pool))
    return [tips_pool[i] for i in sorted(indices)]


def build_news_cards_html(news_list):
    """构建新闻卡片 HTML（逐条拼接，避免 f-string 转义问题）"""
    cards_html = ""
    for idx, news in enumerate(news_list):
        is_urgent = news.get("severity") == "urgent"
        severity_class = "danger" if is_urgent else "prevent"
        severity_icon = "🔴" if is_urgent else "🟡"
        url = news.get("url", "#")
        # 验证 URL 不是首页
        last_seg = url.rstrip("/").split("/")[-1] if url else ""
        is_homepage = last_seg == "" or last_seg in ["index.html", "index", "news", "recalls", "Recalls"]
        url_display = "#" if is_homepage else url
        title = news.get("title", "")
        date_str = news.get("date", "")
        source = news.get("source", "")
        desc = news.get("desc", title)

        card = (
            '<div class="news-card" data-index="' + str(idx) + '">\n'
            '  <div class="card-header" onclick="toggleCard(' + str(idx) + ')">\n'
            '    <span class="severity-' + severity_class + '">' + severity_icon + ' ' + title + '</span>\n'
            '    <span class="card-arrow">▼</span>\n'
            '  </div>\n'
            '  <div class="card-body">\n'
            '    <p>📅 ' + date_str + ' | 来源：' + source + '</p>\n'
            '    <p>' + desc + '</p>\n'
            '    <div class="source-row">\n'
            '      <a href="' + url_display + '" target="_blank" rel="noopener" class="source-tag">📖 查看原文 (' + source + ')</a>\n'
            '    </div>\n'
            '  </div>\n'
            '</div>\n'
        )
        cards_html += card
    return cards_html


def generate_html_report(urgent_news, important_news, tips, report_date, mode):
    """生成完整 HTML 报告（V4.4 风格，纯字符串拼接，无 f-string 模板问题）"""
    date_str = report_date.strftime("%Y年%m月%d日")
    title = "婴儿安全资讯日报 · " + ("晚间更新" if mode == "evening" else "早间版")

    n_urgent = len(urgent_news)
    n_important = len(important_news)

    # 构建新闻卡片
    news_cards_html = build_news_cards_html(urgent_news + important_news)

    # 构建贴士
    tips_html = ""
    for tip in tips:
        tips_html += '<div class="tip-card">💡 ' + tip + '</div>\n'

    # 完整 HTML
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
        '    .stat-card { flex: 1; background: var(--card); padding: 16px; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center; }\n'
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
        '    .source-row { margin-top: 10px; }\n'
        '    .source-tag { display: inline-block; padding: 4px 10px; background: #FFF3F2; color: var(--coral); border-radius: 6px; text-decoration: none; font-size: 13px; }\n'
        '    .source-tag:hover { opacity: 0.8; }\n'
        '    .tip-card { background: #EFF6FF; border-left: 4px solid var(--blue); padding: 12px 16px; border-radius: 14px; margin-bottom: 8px; font-size: 14px; }\n'
        '  </style>\n'
        '  <script>\n'
        '  (function(){\n'
        '    var k="_daily_rpt_state",v;try{v=sessionStorage.getItem(k)}catch(e){}\n'
        '    if(v){try{var s=JSON.parse(v);if(s.y>10||s.ci!==undefined){document.documentElement.className="scroll-restoring";window.__ds=s;}}catch(e){}}\n'
        '  })();\n'
        '  </script>\n'
        '  <style>html.scroll-restoring{visibility:hidden}</style>\n'
        '</head>\n'
        '<body>\n'
        '  <div class="hero">\n'
        '    <h1>🛡️ ' + title + '</h1>\n'
        '    <p>' + date_str + ' | 重点关注婴儿安全动态</p>\n'
        '    <p style="margin-top:8px;font-size:13px;">⏱️ 阅读时长约 ' + str(n_urgent + n_important + 2) + ' 分钟</p>\n'
        '  </div>\n'
        '  <div class="stats">\n'
        '    <div class="stat-card"><div class="num">' + str(n_urgent) + '</div><div class="label">🔴 紧急</div></div>\n'
        '    <div class="stat-card"><div class="num">' + str(n_important) + '</div><div class="label">🟡 重要</div></div>\n'
        '    <div class="stat-card"><div class="num">' + str(len(tips)) + '</div><div class="label">💡 贴士</div></div>\n'
        '  </div>\n'
        '  <h2 style="margin:20px 0 12px;font-size:18px;">📰 安全资讯</h2>\n'
        + news_cards_html +
        '  <h2 style="margin:20px 0 12px;font-size:18px;">💡 安全贴士</h2>\n'
        + tips_html +
        '  <hr style="margin:30px 0 20px;border:none;border-top:1px solid #e2e8f0;">\n'
        '  <p style="text-align:center;color:var(--text-2);font-size:13px;">\n'
        '    📊 数据来源：CPSC · FDA · 中国市场监管总局 · 中国质量报<br>\n'
        '    ⚠️ 本日报仅供参考，具体操作请遵循官方指导。\n'
        '  </p>\n'
        '  <script>\n'
        '  // 卡片折叠/展开\n'
        '  function toggleCard(idx) {\n'
        '    var card = document.querySelector(\'.news-card[data-index="\'+idx+\'"]\');\n'
        '    if(card) {\n'
        '      var body = card.querySelector(\'.card-body\');\n'
        '      var arrow = card.querySelector(\'.card-arrow\');\n'
        '      if(body.classList.contains(\'open\')) { body.classList.remove(\'open\'); arrow.style.transform = \'rotate(0deg)\'; }\n'
        '      else { body.classList.add(\'open\'); arrow.style.transform = \'rotate(180deg)\'; }\n'
        '    }\n'
        '  }\n'
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


def deploy_html_report(urgent_news, important_news, tips, report_date, mode):
    """生成 HTML 报告并写入 docs/ 目录"""
    date_str = report_date.strftime("%Y-%m-%d")
    filename = date_str + "-婴儿安全日报"
    if mode == "evening":
        filename += "-晚间更新"
    filename += ".html"

    html_content = generate_html_report(urgent_news, important_news, tips, report_date, mode)

    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    os.makedirs(docs_dir, exist_ok=True)

    filepath = os.path.join(docs_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("✅ HTML 报告已生成: docs/" + filename)

    # 生成访问 URL
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        url = "https://" + repo.split("/")[0] + ".github.io/" + repo.split("/")[1] + "/docs/" + filename
        return url, filepath

    return None, filepath


def main():
    parser = argparse.ArgumentParser(description="婴儿安全资讯云端推送")
    parser.add_argument("--mode", choices=["morning", "evening"], required=True, help="morning=早间版, evening=晚间版")
    args = parser.parse_args()

    today = datetime.date.today()
    print("🚀 开始执行云端推送 (mode=" + args.mode + ", date=" + str(today) + ")")

    is_evening = args.mode == "evening"
    news_items = fetch_news(days_back=3 if not is_evening else 1, mode=args.mode)

    urgent, important = format_for_report(news_items)
    tips = get_tips(today)

    print("📄 生成 HTML 报告...")
    cloud_url, html_path = deploy_html_report(urgent, important, tips, today, args.mode)
    print("   HTML 路径: " + str(html_path))
    print("   Cloud URL: " + str(cloud_url or "(需要设置 GITHUB_REPOSITORY)"))

    print("📤 发送飞书消息...")
    success = send_daily_report(
        urgent_news=urgent,
        important_news=important,
        tips=tips,
        cloud_url=cloud_url or "",
        report_date=today,
        is_evening=is_evening,
    )

    if success:
        print("✅ 推送完成！")
        return 0
    else:
        print("❌ 推送失败（可能是凭证未配置）")
        return 1


if __name__ == "__main__":
    sys.exit(main())
