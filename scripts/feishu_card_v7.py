#!/usr/bin/env python3
"""飞书交互式卡片 V9 — 珊瑚画廊·信息均衡版"""

import json, subprocess, sys

# ── 配置 ──
USER_ID = "ou_e61d62d0f233b8c91fc56ea461f88f0c"
CLOUD_URL = "https://41af91463cdb43a78a5900a9d71dc4d1.app.codebuddy.work"

DATE = "2026-06-22"
WEEKDAY = "周一"
AGE = "1~2 岁"

# ═══ 晚间增量更新版 ═══
IS_EVENING = True

URGENT_NEWS = [
    {
        "title": "四部委成立联合调查组核查婴幼儿纸尿裤甲酰胺问题：市场监管总局+工信部+卫健委+疾控局联合出手",
        "source": "🇨🇳 市场监管总局 · 新华社 · 财新网",
        "date": "2026-06-22 16:00",
        "body": "6月22日下午，国家市场监管总局通报：针对媒体反映的\"婴幼儿纸尿裤甲酰胺问题\"，市场监管总局、工业和信息化部、国家卫生健康委、国家疾控局高度重视，成立联合调查组，核查婴幼儿纸尿裤甲酰胺有关问题，并依法依规处理。这是纸尿裤甲酰胺事件从企业层面上升到国家监管层面的关键节点。杭州滨江、湖州长兴、上海黄浦等地市监局已24小时内进驻涉事企业，首批官方抽检结果预计6月底—7月初公布。",
        "symptom": "长期接触甲酰胺可致皮肤刺激、过敏，1B类生殖毒性物质可能影响婴幼儿发育",
        "prevent": "关注官方抽检结果与国标修订进展，暂保留产品购买凭证",
        "action": "保留宝宝纸尿裤样品与购买凭证→关注国家市场监管总局官微→如宝宝反复红臀立即停用并就医",
        "urls": [
            ("🇨🇳 市场监管总局", "https://www.samr.gov.cn/xw/zj/art/2026/art_78c0425db7604b27bd7a3f36ba319975.html"),
            ("🇨🇳 新华社", "https://www.news.cn/fortune/20260622/9ff27fe21ab549f19d62b53f5ff0bc74/c.html"),
            ("🇨🇳 财新网", "https://www.caixin.com/2026-06-22/102456347.html"),
            ("🇨🇳 腾讯新闻", "https://news.qq.com/rain/a/20260622A0ARWE00"),
            ("🇨🇳 央视新闻", "https://www.cnenergynews.cn/article/4S5F4nciXfw"),
        ]
    }
]

IMPORTANT_NEWS = [
    {
        "title": "纸尿裤甲酰胺国标修订前期调研已启动：现行GB/T 28004.1-2021等三项标准均未将甲酰胺纳入强制检测",
        "source": "🇨🇳 新浪财经 · 新浪头条",
        "date": "06-22",
        "body": "国家市场监管总局标准技术司消费品处已明确回应，相关科室已收集本次暴露的标准漏洞信息，同步对接行业专家，启动国标修订前期调研工作。修订方向包括将甲酰胺纳入纸尿裤强制检测清单。执行标准GB/T 28004.1-2021、GB 43631-2023、GB 15979-2024均未将甲酰胺列为强制检测项目；6月1日起实施的GB/T 46856-2025主要适用于婴儿床、餐具、奶嘴、床垫，不包括纸尿裤——是关键监管漏洞。",
        "url": "https://finance.sina.com.cn/tech/roll/2026-06-22/doc-iniehfpu0335524.shtml"
    },
    {
        "title": "CPSC召回The Black Sheep Fam儿童睡衣约2,100件：违反美国联邦阻燃强制标准，存在严重烧伤风险",
        "source": "🇺🇸 CPSC · 商务部WTO/FTA咨询网",
        "date": "06-11/12",
        "body": "2026年6月11日美国CPSC召回The Black Sheep Fam品牌儿童睡衣，涉及女童睡裙（中国产）和儿童通用款束脚睡衣套装（危地马拉产）共约2,100件。召回产品违反美国《联邦儿童睡衣可燃性标准》（16 CFR 1615/1616），存在严重烧伤甚至死亡风险。截至召回日暂无事故报告。召回编号26-554，消费者应立即停用并联系品牌全额退款。",
        "url": "https://www.cpsc.gov/Recalls/2026/The-Black-Sheep-Fam-Recalls-Childrens-Pajamas-Due-to-Risk-of-Serious-Injury-or-Death-from-Burn-Hazard-Violates-Mandatory-Flammability-Standards-for-Childrens-Sleepwear"
    }
]

TIPS = [
    {"emoji": "🧸", "title": "小零件三秒测试", "desc": "玩具零件能否塞入卫生纸卷筒？可塞入=窒息风险，必须远离3岁以下儿童"},
    {"emoji": "🪢", "title": "拉绳玩具专项检查", "desc": "长度>7cm或直径<3.5cm的拉绳均不建议给1-3岁幼儿使用（GOPO/LiKee召回警示）"},
    {"emoji": "🔥", "title": "儿童睡衣认\"低火\"标签", "desc": "合规儿童睡衣标有\"低易燃性\"，标签缺失或不达标请勿使用（SHEIN/Veseacky/Black Sheep Fam召回警示）"},
]

CATEGORIES_ACTIVE = ["🍑纸尿裤", "👕服饰寝具"]
CATEGORIES_TOTAL = 13

N_SOURCES = 8
N_URGENT = len(URGENT_NEWS)
N_IMPORTANT = len(IMPORTANT_NEWS)
N_TIPS = len(TIPS)
N_ACTIVE_CATS = len(CATEGORIES_ACTIVE)
N_INACTIVE = CATEGORIES_TOTAL - N_ACTIVE_CATS

# ═══════════════════════════════════════════════
# 构建卡片
# ═══════════════════════════════════════════════

elements = []

# ╔══════════════════════════════════════════════╗
# ║  今日概况 — 一句引语                        ║
# ╚══════════════════════════════════════════════╝

elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": (
        f"🔍 晚间增量扫描 · 新增 **{N_URGENT}** 条紧急 + **{N_IMPORTANT}** 条重要 · 截至18:30"
    )}
})

# ╔══════════════════════════════════════════════╗
# ║  统计条 — 三栏色标                          ║
# ╚══════════════════════════════════════════════╝

elements.append({
    "tag": "column_set",
    "flex_mode": "none",
    "background_style": "default",
    "columns": [
        {
            "tag": "column", "width": "weighted", "weight": 1,
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": (
                f"🚨 **紧急**\n{N_URGENT} 项\n需立即行动"
            )}}]
        },
        {
            "tag": "column", "width": "weighted", "weight": 1,
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": (
                f"📌 **提醒**\n{N_IMPORTANT} 项\n值得关注"
            )}}]
        },
        {
            "tag": "column", "width": "weighted", "weight": 1,
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": (
                f"💡 **贴士**\n{N_TIPS} 条\n{AGE}适用"
            )}}]
        }
    ]
})
elements.append({"tag": "hr"})

# ╔══════════════════════════════════════════════╗
# ║  🔴 紧急安全警示                             ║
# ╚══════════════════════════════════════════════╝

elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "🔴 **紧急安全警示** — 请立即检查"}
})

for i, news in enumerate(URGENT_NEWS):
    # V9: 简洁结构化 — 标题→概述→三标签（无重复标题间的空行）
    card_lines = []
    card_lines.append(f"**{news['title']}**")
    card_lines.append(f"{news['source']} · {news['date']}")
    card_lines.append("")
    card_lines.append(news['body'])
    card_lines.append("")
    card_lines.append(f"🩺 症状：{news['symptom']}")
    card_lines.append(f"🛡️ 预防：{news['prevent']}")
    card_lines.append(f"✅ 行动：{news['action']}")

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
    # 每个紧急新闻可以有多个原文链接按钮
    url_buttons = []
    for label, url in news['urls']:
        url_buttons.append({
            "tag": "button",
            "text": {"tag": "lark_md", "content": f"📋 {label}"},
            "type": "danger",
            "url": url,
            "multi_url": {"url": url}
        })
    elements.append({
        "tag": "action",
        "actions": url_buttons
    })

elements.append({"tag": "hr"})

# ╔══════════════════════════════════════════════╗
# ║  🟡 重要安全提醒 — V9 新增描述               ║
# ╚══════════════════════════════════════════════╝

elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "🟡 **重要安全提醒** — 值得关注"}
})

# V9: 每条重要提醒现在有 body 描述，格式 = 标题 + 来源日期 + 描述
imp_lines = []
for i, news in enumerate(IMPORTANT_NEWS):
    imp_lines.append(f"**{i+1}. {news['title']}**")
    imp_lines.append(f"　　{news['source']} · {news['date']}")
    imp_lines.append(f"　　{news['body']}")
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
            "text": {"tag": "lark_md", "content": f"📋 {n['source']} 原文"},
            "type": "default",
            "url": n['url'],
            "multi_url": {"url": n['url']}
        }
        for n in IMPORTANT_NEWS
    ]
})

elements.append({"tag": "hr"})

# ╔══════════════════════════════════════════════╗
# ║  📰 品类速览 — V9 完备度提示                 ║
# ╚══════════════════════════════════════════════╝

elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": (
        f"📰 **品类覆盖** · {N_ACTIVE_CATS} 类活跃 · {N_INACTIVE} 类今日暂无新增"
    )}
})
elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": "  |  ".join(CATEGORIES_ACTIVE)}
})

elements.append({"tag": "hr"})

# ╔══════════════════════════════════════════════╗
# ║  💡 每日安全贴士                             ║
# ╚══════════════════════════════════════════════╝

elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": f"💡 **每日安全贴士** · {AGE}"}
})

for i, tip in enumerate(TIPS):
    elements.append({
        "tag": "column_set",
        "flex_mode": "none",
        "background_style": "grey",
        "columns": [{
            "tag": "column", "width": "weighted", "weight": 1,
            "elements": [{
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"{tip['emoji']} **{tip['title']}** · {tip['desc']}"}
            }]
        }]
    })

elements.append({"tag": "hr"})

# ╔══════════════════════════════════════════════╗
# ║  CTA — 带引语引导                            ║
# ╚══════════════════════════════════════════════╝

elements.append({
    "tag": "div",
    "text": {"tag": "lark_md", "content": f"📱 以上为 {N_URGENT + N_IMPORTANT} 条资讯摘要 · 完整图文请见下方"}
})

elements.append({
    "tag": "action",
    "actions": [{
        "tag": "button",
        "text": {"tag": "lark_md", "content": "📖 查看完整图文日报"},
        "type": "primary",
        "url": CLOUD_URL,
        "multi_url": {"url": CLOUD_URL}
    }]
})

# ╔══════════════════════════════════════════════╗
# ║  Footer                                     ║
# ╚══════════════════════════════════════════════╝

elements.append({"tag": "hr"})
elements.append({
    "tag": "note",
    "elements": [{
        "tag": "lark_md",
        "content": "📡 市场监管总局 · FDA · WHO · CPSC · 央视新闻 | ⚠️ 仅供参考 · 紧急情况请立即就医 | V9"
    }]
})

# ═══════════════════════════════════════════════
# 🔒 URL 硬验证 — 禁止官网首页
# ═══════════════════════════════════════════════

import re

# 常见官网首页域名模式（无具体文章路径）
HOMEPAGE_PATTERNS = [
    r'^https?://[^/]+/?$',                          # 纯域名或域名/
    r'^https?://www\.fda\.gov/?$',                  # FDA 首页
    r'^https?://www\.fda\.gov/safety/?$',
    r'^https?://www\.fda\.gov/safety/recalls/?$',
    r'^https?://www\.cpsc\.gov/?$',                 # CPSC 首页
    r'^https?://www\.cpsc\.gov/Recalls/?$',
    r'^https?://www\.cctv\.com/?$',                 # 央视首页
    r'^https?://www\.cqn\.com\.cn/?$',              # 质量新闻网首页
    r'^https?://www\.samr\.gov\.cn/?$',             # 市场监管总局首页
    r'^https?://www\.cdc\.gov/?$',                  # CDC 首页
    r'^https?://www\.nhtsa\.gov/?$',                # NHTSA 首页
    r'^https?://www\.who\.int/?$',                  # WHO 首页
    r'^https?://news\.qq\.com/?$',                  # 腾讯新闻首页
    r'^https?://www\.163\.com/?$',                  # 网易首页
    r'^https?://www\.163\.com/dy/?$',               # 网易号首页
]

def validate_url(url, label=""):
    """检查 URL 是否为官网首页，返回 (is_valid, reason)"""
    for pattern in HOMEPAGE_PATTERNS:
        if re.match(pattern, url):
            return False, f"🚫 {label} → 疑似官网首页: {url}"
    # 检查 URL 路径深度：至少要有 2 级以上路径
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path_segments = [s for s in parsed.path.strip('/').split('/') if s]
    if len(path_segments) < 2:
        return False, f"🚫 {label} → 路径过短（{len(path_segments)}级），可能是导航页: {url}"
    return True, ""

def validate_all_urls():
    """验证所有 URL，有不合法则报错退出"""
    errors = []
    for i, news in enumerate(URGENT_NEWS):
        for label, url in news.get('urls', []):
            ok, reason = validate_url(url, f"紧急[{i}] {label}")
            if not ok:
                errors.append(reason)
    for i, news in enumerate(IMPORTANT_NEWS):
        ok, reason = validate_url(news.get('url', ''), f"重要[{i}] {news.get('source','')}")
        if not ok:
            errors.append(reason)
    if errors:
        print("❌ URL 验证失败 — 以下链接疑似官网首页或导航页，禁止发送：")
        for e in errors:
            print(f"   {e}")
        print("⚠️ 请修改为具体的原文文章链接后再重试。")
        sys.exit(1)
    print("🔒 URL 验证通过 ✓")

# ── 执行验证 ──
validate_all_urls()

# ═══════════════════════════════════════════════
# 组装 & 发送
# ═══════════════════════════════════════════════

card = {
    "config": {"wide_screen_mode": True},
    "header": {
        "template": "carmine",
        "title": {
            "tag": "plain_text",
            "content": f"🛡️ 晚间更新 · 新增资讯 · {DATE} {WEEKDAY}"
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

print("📤 发送飞书交互式卡片 V9...")
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
