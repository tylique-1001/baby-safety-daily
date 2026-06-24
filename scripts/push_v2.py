#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
push_v2.py — 重新推送今日日报（v5分区版）
以手动整理的国内热点为主，自动采集做补充
"""

import sys
import os
import json
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cloud_push"))

from news_fetcher import fetch_news, format_for_report, get_manual_today_hotspots
from main import generate_html_report, deploy_html_report
from feishu_sender import build_v9_card, get_access_token, send_interactive_card

today = datetime.date.today()
date_str = today.strftime("%Y-%m-%d")
print(f"🚀 采集 {date_str} 国内婴幼儿安全资讯...")

# 手动数据为主（覆盖品类全面），自动采集做补充
manual_items = get_manual_today_hotspots()
print(f"📋 手动整理: {len(manual_items)} 条")

# 自动采集（去重后补充）
auto_items = fetch_news(days_back=7, mode="manual")
# 去重：标题前30字相同视为重复
seen_titles = {item["title"][:30] for item in manual_items}
for item in auto_items:
    if item["title"][:30] not in seen_titles:
        seen_titles.add(item["title"][:30])
        manual_items.append(item)
        print(f"   + 自动补充: {item['title'][:60]}")

print(f"\n📊 合并后共 {len(manual_items)} 条资讯")

# 三档分类
urgent, important, reminder = format_for_report(manual_items)

# 品类覆盖统计
all_cats = set()
for nlist in [urgent, important, reminder]:
    for n in nlist:
        for c in n.get("categories", ["日常用品"]):
            all_cats.add(c)

print(f"   🔴 紧急: {len(urgent)}")
print(f"   🟡 重要: {len(important)}")
print(f"   🟠 提醒: {len(reminder)}")
print(f"   📂 覆盖品类: {len(all_cats)} → {', '.join(sorted(all_cats))}")

# 贴士 — 根据今日热点定制
tips = [
    "🍼 纸尿裤选购：关注国家市场监管总局联合调查结果，暂避《经济参考报》报道的涉事批次，选择正规渠道购买，保留购买凭证",
    "👕 婴儿服装安全：避免购买有绳带/长装饰物的连帽衫和婴儿服，纽扣装饰物需牢固不易脱落",
    "🧸 玩具小零件：对≤3岁宝宝的所有玩具做\"卷筒测试\"——能塞入卫生纸卷筒的小零件都有窒息风险",
    "🛏️ 婴儿床护栏：确保护栏间距≤6cm、锁紧装置牢固，床垫与护栏间缝隙不超过两指宽",
]

print(f"\n📄 生成 HTML 报告...")
html = generate_html_report(urgent, important, reminder, tips, today, "manual")
html_path = f"outputs/daily-reports/{date_str}-婴儿安全日报.html"
os.makedirs("outputs/daily-reports", exist_ok=True)
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"   ✅ HTML: {html_path}")

# MD 版本
md_path = f"outputs/wechat-articles/{date_str}-婴儿安全日报.md"
os.makedirs("outputs/wechat-articles", exist_ok=True)
with open(md_path, "w", encoding="utf-8") as f:
    f.write(f"# 🛡️ 婴儿安全资讯日报 — {today.strftime('%Y年%m月%d日')}\n\n")
    f.write(f"> 覆盖品类：{' · '.join(sorted(all_cats))}\n\n")
    f.write(f"## 🔴 紧急警示（{len(urgent)}条）\n\n")
    for n in urgent:
        f.write(f"### {n['title']}\n")
        f.write(f"- 来源：{n.get('source', '')} | {n.get('date', '')}\n")
        f.write(f"- 品类：{' · '.join(n.get('categories', []))}\n")
        f.write(f"- {n.get('desc', '')}\n")
        f.write(f"- [查看原文]({n.get('url', '#')})\n\n")
    f.write(f"## 🟡 重要召回/通报（{len(important)}条）\n\n")
    for n in important:
        f.write(f"### {n['title']}\n")
        f.write(f"- 来源：{n.get('source', '')} | {n.get('date', '')}\n")
        f.write(f"- 品类：{' · '.join(n.get('categories', []))}\n")
        f.write(f"- {n.get('desc', '')}\n")
        f.write(f"- [查看原文]({n.get('url', '#')})\n\n")
    f.write(f"## 🟠 提醒关注（{len(reminder)}条）\n\n")
    for n in reminder:
        f.write(f"### {n['title']}\n")
        f.write(f"- 来源：{n.get('source', '')} | {n.get('date', '')}\n")
        f.write(f"- 品类：{' · '.join(n.get('categories', []))}\n")
        f.write(f"- {n.get('desc', '')}\n")
        f.write(f"- [查看原文]({n.get('url', '#')})\n\n")
    f.write(f"## 💡 安全贴士\n\n")
    for t in tips:
        f.write(f"- {t}\n")
print(f"   ✅ Markdown: {md_path}")

# 验证质量关卡
print("\n🛡️ 质量关卡验证:")
checks = [
    ("has-more 源截断", "has-more" in html),
    ("target=_blank", 'target="_blank"' in html),
    ("滚动恢复 __ds", '__ds' in html),
    ("四区锚点 urgent", 'urgent-section' in html),
    ("四区锚点 important", 'important-section' in html),
    ("四区锚点 reminder", 'reminder-section' in html),
    ("四区锚点 tips", 'tips-section' in html),
    ("jumpToSection 函数", 'jumpToSection' in html),
    ("品类芯片 cat-chip", 'cat-chip' in html),
    ("四栏统计 stat-reminder", 'stat-reminder' in html),
    ("覆盖品类栏", 'filter-chip' in html or 'cat-bar' in html),
]
all_pass = True
for label, ok in checks:
    print(f"   {'✅' if ok else '❌'} {label}")
    if not ok: all_pass = False

print(f"\n{'✅ 全部通过!' if all_pass else '❌ 有未通过项!'}")

# 构建飞书卡片
print("\n📤 构建飞书卡片...")
card = build_v9_card(urgent, important, reminder, tips, "CLOUD_URL_PLACEHOLDER", today)
card_path = f"outputs/feishu_card_v2_{date_str}.json"
with open(card_path, "w", encoding="utf-8") as f:
    json.dump(card, f, ensure_ascii=False, indent=2)
print(f"   ✅ 飞书卡片 JSON: {card_path}")

print(f"\n🎉 所有准备工作完成!")
print(f"   HTML: {html_path}")
print(f"   MD: {md_path}")
print(f"   品类覆盖: {len(all_cats)}/13")
