#!/usr/bin/env python3
"""飞书交互式卡片 — 晚间增量模式（情况B：无新增） — 2026-06-23"""

import json, subprocess, sys

USER_ID = "ou_e61d62d0f233b8c91fc56ea461f88f0c"
# 今日 (2026-06-23) 早间报告尚未生成；使用最新可用的晚间更新版链接
CLOUD_URL = "https://41af91463cdb43a78a5900a9d71dc4d1.app.codebuddy.work/2026-06-22-婴儿安全日报-晚间更新.html"

DATE = "2026-06-23"
WEEKDAY = "周二"

# 来自 2026-06-22 晚间报告（最新一期含 1 紧急 + 2 重要）
URGENT_COUNT = 1
IMPORTANT_COUNT = 2
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
            "content": (
                f"📅 **{DATE} {WEEKDAY} · 晚间 18:30 简报**\n\n"
                f"截至 18:30，今日白天暂无新增婴儿安全相关紧急/重要资讯。"
                f"昨日晚间报告的 **{URGENT_COUNT} 条紧急** + **{IMPORTANT_COUNT} 条重要提醒**仍然有效，请家长继续保持关注。"
            )
        }
    },
    {"tag": "hr"},

    # 持续生效的紧急事项回看
    {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                f"📊 **持续生效的安全事项**\n"
                f"• 🔴 紧急：**婴幼儿纸尿裤甲酰胺联合调查组成立**（市场监管总局+工信部+卫健委+疾控局四部委，6/22 16:00 官方通报）\n"
                f"• 🟡 重要①：**纸尿裤甲酰胺国标修订前期调研启动**（《21世纪经济报道》6/22，GB/T 28004.1-2021 等三项标准均未将甲酰胺纳入强制检测）\n"
                f"• 🟡 重要②：**CPSC 召回 The Black Sheep Fam 儿童睡衣约 2,100 件**（6/11 发布，违反美国联邦阻燃标准 16 CFR 1615/1616）"
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
                "① **多品牌纸尿裤甲酰胺事件** — 4 部委联合调查组已成立，"
                "好奇（Huggies）小森林系列、Babycare 非凡大师系列、碧芭宝贝（BEABA）大鱼海棠系列暂未下架但已立案调查。\n\n"
                "② **Nara Organics 婴儿配方奶粉肉毒杆菌** — 持续生效，"
                "美国 3 州 3 例确诊住院，海关总署已发布禁止携带邮寄入境消费提示。\n\n"
                "③ **B.Childhood 高景观推车** — CPSC 警告立即停用。"
            )
        }
    },
    {"tag": "hr"},

    # 持续防范要点
    {
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                "💡 **持续防范要点**\n\n"
                "• 婴幼儿纸尿裤关注品牌官方检测报告，留意电商渠道下架动态\n"
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
            "content": "📖 **查看最新完整图文日报**\n\n所有新闻的详情、症状标签、来源链接已整理在 CloudStudio 部署的完整 HTML 报告中。"
        }
    },
    {
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📖 查看最新完整报告"},
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
