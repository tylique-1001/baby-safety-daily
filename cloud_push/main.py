#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py - 云端推送主入口
GitHub Actions 调用此脚本完成完整推送流程
V5 极简视觉 + 全部功能改进（14品类 / 3天过滤 / 自愈引擎 / 幂等保护）

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

# 添加当前目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news_fetcher import fetch_news, format_for_report
from feishu_sender import send_daily_report, send_daily_report_with_retry
from config import CLOUDSTUDIO_SUBDOMAIN


def get_tips(date):
    """获取当日安全贴士"""
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


def build_news_cards_html(news_list):
    """构建新闻卡片 HTML（V5 极简风格：标题+正文+源链接）"""
    cards_html = ""
    for idx, news in enumerate(news_list):
        is_urgent = news.get("severity") == "urgent"
        severity_class = "danger" if is_urgent else "prevent"
        severity_icon = "🔴" if is_urgent else "🟡"
        title = news.get("title", "")
        date_str = news.get("date", "")
        source = news.get("source", "")
        desc = news.get("desc", title)
        categories = news.get("categories", ["日常用品"])

        # 品类 → 简单文字（非芯片UI，V5风格）
        cat_text = " · ".join(categories)

        # 多源链接 → 构建 source row
        urls = news.get("urls", [])
        single_url = news.get("url", "")
        existing_urls = set(link for _, link in urls)
        if single_url and is_valid_url(single_url) and single_url not in existing_urls:
            urls.append((source, single_url))
        if not urls:
            urls = [(source, single_url if single_url else "#")]

        source_links_html = ""
        for label, link in urls:
            source_links_html += (
                '<a href="' + link + '" target="_blank" rel="noopener" class="source-tag">'
                '📖 ' + label + '</a>\n'
            )

        card = (
            '<div class="news-card" data-index="' + str(idx) + '">\n'
            '  <div class="card-header" onclick="toggleCard(' + str(idx) + ')">\n'
            '    <span class="severity-' + severity_class + '">' + severity_icon + ' ' + title + '</span>\n'
            '    <span class="card-arrow">▼</span>\n'
            '  </div>\n'
            '  <div class="card-body">\n'
            '    <p>📅 ' + date_str + ' | 来源：' + source + ' | 📂 ' + cat_text + '</p>\n'
            '    <p>' + desc + '</p>\n'
            '    <div class="source-row">\n'
            + source_links_html +
            '    </div>\n'
            '  </div>\n'
            '</div>\n'
        )
        cards_html += card
    return cards_html


def generate_html_report(urgent_news, important_news, reminder_news, tips, report_date, mode):
    """生成完整 HTML 报告（V5 极简风格 — 3栏统计 + 平铺卡片 + 贴士）"""
    date_str = report_date.strftime("%Y年%m月%d日")
    title = "婴儿安全资讯日报 · " + ("晚间更新" if mode == "evening" else "早间版")

    n_urgent = len(urgent_news)
    n_important = len(important_news) + len(reminder_news)  # 重要+提醒合并显示

    # 合并所有新闻（V5 风格：平铺列表，无分区）
    all_news = urgent_news + important_news + reminder_news
    news_cards_html = build_news_cards_html(all_news)

    # 贴士
    tips_html = ""
    for tip in tips:
        tips_html += '<div class="tip-card">💡 ' + tip + '</div>\n'

    # 完整 HTML（V5 原版 CSS + 结构）
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
        '    <p style="margin-top:8px;font-size:13px;">⏱️ 阅读时长约 ' + str(n_urgent + n_important + len(tips) + 2) + ' 分钟</p>\n'
        '  </div>\n'
        '  <div class="stats">\n'
        '    <div class="stat-card"><div class="num">' + str(n_urgent) + '</div><div class="label">🔴 紧急</div></div>\n'
        '    <div class="stat-card"><div class="num">' + str(n_important) + '</div><div class="label">🟡 重要/提醒</div></div>\n'
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

    # 生成访问 URL（htmlpreview.github.io）
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        url = "https://" + repo.split("/")[0] + ".github.io/" + repo.split("/")[1] + "/docs/" + filename
        return url, filepath

    return None, filepath


# ═══════════════════════════════════════════════════════════════
# 🛡️ SelfHealRunner — 无限自愈引擎
# ═══════════════════════════════════════════════════════════════

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
            fixes.append(("widen_search", "扩大搜索范围(days_back+3)"))
            self._log_fix("empty_news", "0条新闻，将扩大搜索范围")
        elif error_type == "feishu_auth_fail":
            fixes.append(("retry_auth", "等待后重试飞书认证"))
            self._log_fix("feishu_auth", "飞书认证失败，将重试")
        elif error_type == "feishu_send_fail":
            fixes.append(("retry_send", "重试发送"))
            self._log_fix("feishu_send", "飞书发送失败，将重试")
        elif error_type == "network_error":
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
        try:
            # 幂等保护：使用 .last_push 文件（不受 git checkout 重置 mtime 影响）
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

            # 根据重试次数动态调整搜索天数
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
                    for fix in self.fixes_applied:
                        print("   " + fix, flush=True)
                return 0

            fixes = self._diagnose(error_type, context or {})
            if not fixes:
                print("⚠️ 无法诊断，直接重试", flush=True)

            delay = min(self.BASE_DELAY * (2 ** (attempt - 1)), self.MAX_DELAY)
            print("⏳ 等待 " + str(delay) + " 秒后重试...", flush=True)
            time.sleep(delay)

        # 所有重试用尽
        print("\n" + "=" * 60, flush=True)
        print("🆘 自愈循环耗尽！" + str(self.MAX_RETRIES) + "次重试全部失败", flush=True)
        print("📋 诊断记录:", flush=True)
        for entry in self.diagnosis_log:
            print("   " + entry, flush=True)
        print("📋 修复记录:", flush=True)
        for entry in self.fixes_applied:
            print("   " + entry, flush=True)

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

    # Self-heal 模式
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
