#!/usr/bin/env python3
"""飞书交互式卡片 — 晚间增量模式（情况B：无新增）"""

import json, subprocess, sys

USER_ID = "ou_e61d62d0f233b8c91fc56ea461f88f0c"
CLOUD_URL = "https://b5875d7b0e66402ab4b2557678e42764.app.codebuddy.work"

DATE = "2026-06-20"
WEEKDAY = "周六"

# 早间报告统计（无需搜索，从已知数据引用）
URGENT_COUNT = 5
IMPORTANT_COUNT = 5
TIPS_COUNT = 3

# ═══════════════════════════════════════════════
# 卡片 V9 — 晚间无新增简报
# ═══════════════════════════════════════════════

elements = [
    # 概况引语
    {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"📅 **{DATE} {WEEKDAY} · 晚间 18:30 简报**\n\n截至 18:30，今日白天暂无新增婴儿安全相关紧急/重要资讯。早间报告的 **{URGENT_COUNT} 条紧急** + **{IMPORTANT_COUNT} 条重要提醒**仍然有效，请家长继续保持关注。"
        }
    },
    {"tag": "hr"},

    # 早间报告核心数据回看
    {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                f"📊 **早间报告回顾**\n"
                f"• 🔴 紧急新闻：{URGENT_COUNT} 条（GOPO牙胶 / CooCooBaby躺椅 / BABESIDE玩具 / Joolz适配器 / 多品牌纸尿裤甲酰胺）\n"
                f"• 🟡 重要提醒：{IMPORTANT_COUNT} 条（SHEIN睡衣 / Target湿巾 / B.Childhood推车 / 推车新国标 / 儿童用品召回数据）\n"
                f"• 💡 安全贴士：{TIPS_COUNT} 条"
            )
        }
    },
    {"tag": "hr"},

    # 重点关注
    {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                "🔥 **今日仍需重点关注**\n\n"
                "① **多品牌纸尿裤甲酰胺** — 6/18 媒体曝光，6/19 持续发酵，好奇/Babycare/碧芭宝贝等品牌回应中。\n"
                "② **GOPO 拉绳牙胶** — CPSC 大规模召回 70,410 件，已有 3 起窒息报告。\n"
                "③ **CooCooBaby 婴儿躺椅** — 违反婴儿睡眠产品强制标准，2,355 件召回。"
            )
        }
    },
    {"tag": "hr"},

    # 重要提醒 body
    {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                "💡 **持续防范要点**\n\n"
                "• 玩具小零件三秒测试（卫生纸卷筒法）\n"
                "• 拉绳/长绳玩具远离 1-3 岁幼儿\n"
                "• 婴儿睡眠产品认准合规标识\n"
                "• 儿童睡衣认\"低易燃性\"标签"
            )
        }
    },
    {"tag": "hr"},

    # CTA
    {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "📖 **查看早间完整图文日报**\n\n所有 10 条新闻的详情、症状标签、来源链接已整理在 CloudStudio 部署的完整 HTML 报告中。"
        }
    },
    {
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📖 查看早间完整报告"},
                "type": "primary",
                "url": CLOUD_URL
            }
        ]
    },

    # 底部分隔
    {"tag": "hr"},
    {
        "tag": "note",
        "elements": [
            {"tag": "plain_text", "content": "📡 市场监管总局 · FDA · CDC · CPSC · 央视新闻 | 晚间增量扫描完成 | V9"}
        ]
    }
]

card = {
    "config": {"wide_screen_mode": True},
    "header": {
        "template": "carmine",
        "title": {
            "tag": "plain_text",
            "content": f"🛡️ 晚间简报 · 无新增 · {DATE}"
        }
    },
    "elements": elements
}

card_json = json.dumps(card, ensure_ascii=False)

cmd = [
    "lark-cli", "im", "+messages-send",
    "--user-id", USER_ID,
    "--as", "bot",
    "--msg-type", "interactive",
    "--content", card_json
]

print("📤 发送飞书晚间简报卡片（情况B：无新增）...")
print(f"   内容长度: {len(card_json)} chars")
result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode == 0:
    print("✅ 发送成功！")
    try:
        resp = json.loads(result.stdout)
        print(f"   message_id: {resp.get('message_id', 'N/A')}")
    except:
        print(result.stdout)
else:
    print("❌ 发送失败:")
    print(result.stderr)
    sys.exit(1)
