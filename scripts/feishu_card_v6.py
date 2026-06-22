#!/usr/bin/env python3
"""飞书交互式卡片 V6 — 暖珊瑚画廊 · 结构化日报推送"""

import json, subprocess, sys

# ── 配置 ──
USER_ID = "ou_e61d62d0f233b8c91fc56ea461f88f0c"
CLOUD_URL = "https://b51a3dd5be6645809a2aeb394808ad37.app.codebuddy.work"

# ── 日报数据 ──
DATE = "2026-06-19"
WEEKDAY = "周五"
AGE = "1~2 岁"

URGENT_NEWS = [
    {
        "title": "FDA 警告某品牌婴儿磨牙棒窒息风险",
        "source": "🇺🇸 FDA · 2026-06-18",
        "body": "磨牙棒碎片脱落，可能导致婴幼儿气管堵塞窒息。涉及 3 批次 12,000 件，全美召回中。",
        "tags": "🩺 碎片脱落→窒息 | 🛡️ 立即停用 | ✅ 选一体成型款",
        "url": "https://www.fda.gov/safety/recalls/"
    },
    {
        "title": "市场监管总局通报儿童床护栏召回",
        "source": "🇨🇳 市场监管总局 · 2026-06-17",
        "body": "护栏间隙超标（>6cm），婴幼儿头颈可能卡住致死。涉及 8,500 件，全国紧急召回。",
        "tags": "🩺 间隙超标→窒息 | 🛡️ 停用联系退货 | ✅ 换 <6cm 间隙款",
        "url": "https://www.samr.gov.cn/"
    }
]

IMPORTANT_NEWS = [
    {
        "title": "湿巾防腐剂 MIT/CMIT 超标",
        "source": "🇨🇳 央视新闻 · 2026-06-18",
        "url": "https://www.cctv.com/"
    },
    {
        "title": "奶瓶刻度偏差超 10% 致喂养过量",
        "source": "🇨🇳 质量新闻网 · 2026-06-16",
        "url": "https://www.cqn.com.cn/"
    },
    {
        "title": "爬行垫甲酰胺挥发物警示",
        "source": "🇺🇸 CPSC · 2026-06-15",
        "url": "https://www.cpsc.gov/"
    }
]

TIPS = [
    "🍼 喂奶后竖抱拍嗝 15 分钟 — 降低呛奶风险",
    "🛁 洗澡水温 37-38°C — 冷水先放热水后加",
    "🛌 睡眠区清空软物 — 仰卧降 SIDS 风险 60%+"
]

CATEGORIES_ACTIVE = ["🍼喂养器具", "🧴洗护用品", "🛏️寝具家具", "🍪食品零食", "🧸玩具"]
CATEGORIES_TOTAL = 13

# ═══════════════════════════════════════════════
# 构建卡片 JSON
# ═══════════════════════════════════════════════

elements = []

# ── Header 统计条 ──
elements.append({
    "tag": "column_set",
    "flex_mode": "bisect",
    "background_style": "default",
    "columns": [
        {
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [{
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**🚨 紧急**\n**{len(URGENT_NEWS)} 项**"
                }
            }]
        },
        {
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [{
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**📌 提醒**\n**{len(IMPORTANT_NEWS)} 项**"
                }
            }]
        },
        {
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [{
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**💡 贴士**\n**{len(TIPS)} 条**"
                }
            }]
        }
    ]
})

# ── 分隔 ──
elements.append({"tag": "hr"})

# ── 紧急新闻 ──
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "**🔴 紧急安全警示**"}
})

for i, news in enumerate(URGENT_NEWS):
    # 新闻内容卡片 (grey背景)
    elements.append({
        "tag": "column_set",
        "flex_mode": "none",
        "background_style": "grey",
        "columns": [{
            "tag": "column",
            "width": "weighted",
            "weight": 1,
            "elements": [{
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{news['title']}**\n\n{news['source']}\n\n{news['body']}\n\n{news['tags']}"
                }
            }]
        }]
    })
    # 操作按钮 (独立在外)
    elements.append({
        "tag": "action",
        "actions": [{
            "tag": "button",
            "text": {"tag": "lark_md", "content": "📋 查看官方公告"},
            "type": "danger",
            "url": news['url'],
            "multi_url": {"url": news['url']}
        }]
    })

# ── 分隔 ──
elements.append({"tag": "hr"})

# ── 重要提醒 ──
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "**🟡 重要安全提醒**"}
})

# 合并到一个 grey 卡片 + 多个 action buttons
imp_lines = []
for i, news in enumerate(IMPORTANT_NEWS):
    imp_lines.append(f"{i+1}. **{news['title']}** — {news['source']}")

elements.append({
    "tag": "column_set",
    "flex_mode": "none",
    "background_style": "grey",
    "columns": [{
        "tag": "column",
        "width": "weighted",
        "weight": 1,
        "elements": [{
            "tag": "div",
            "text": {"tag": "lark_md", "content": "\n".join(imp_lines)}
        }]
    }]
})

# 重要提醒的操作按钮 (独立在外)
elements.append({
    "tag": "action",
    "actions": [
        {
            "tag": "button",
            "text": {"tag": "lark_md", "content": news['source'][:3]},
            "type": "default",
            "url": news['url'],
            "multi_url": {"url": news['url']}
        }
        for news in IMPORTANT_NEWS
    ]
})

# ── 分隔 ──
elements.append({"tag": "hr"})

# ── 品类速览 ──
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": f"**📰 品类速览** — 扫描 {CATEGORIES_TOTAL} 类，**{len(CATEGORIES_ACTIVE)} 类**有动态"}
})

elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": " · ".join(CATEGORIES_ACTIVE)}
})

# ── 分隔 ──
elements.append({"tag": "hr"})

# ── 每日贴士 ──
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "**💡 每日安全贴士 · " + AGE + "**"}
})

elements.append({
    "tag": "column_set",
    "flex_mode": "none",
    "background_style": "grey",
    "columns": [{
        "tag": "column",
        "width": "weighted",
        "weight": 1,
        "elements": [{
            "tag": "div",
            "text": {"tag": "lark_md", "content": "\n".join(TIPS)}
        }]
    }]
})

# ── 分隔 ──
elements.append({"tag": "hr"})

# ── CTA 按钮 ──
elements.append({
    "tag": "action",
    "actions": [{
        "tag": "button",
        "text": {"tag": "lark_md", "content": "🌐 打开完整图文日报"},
        "type": "primary",
        "url": CLOUD_URL,
        "multi_url": {"url": CLOUD_URL}
    }]
})

# ── Footer ──
elements.append({"tag": "hr"})
elements.append({
    "tag": "note",
    "elements": [{
        "tag": "lark_md",
        "content": "📡 市场监管总局 · FDA · WHO · CPSC · 央视新闻 | ⚠️ 仅供参考 · 紧急情况请立即就医 | V6 Gallery"
    }]
})

# ═══════════════════════════════════════════════
# 组装完整卡片
# ═══════════════════════════════════════════════

card = {
    "config": {"wide_screen_mode": True},
    "header": {
        "template": "carmine",
        "title": {
            "tag": "plain_text",
            "content": f"🐣 宝宝安全日报 · {DATE} {WEEKDAY}"
        }
    },
    "elements": elements
}

card_json = json.dumps(card, ensure_ascii=False)

# ═══════════════════════════════════════════════
# 发送
# ═══════════════════════════════════════════════

cmd = [
    "lark-cli", "im", "+messages-send",
    "--user-id", USER_ID,
    "--as", "bot",
    "--msg-type", "interactive",
    "--content", card_json
]

print("📤 发送飞书交互式卡片...")
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
