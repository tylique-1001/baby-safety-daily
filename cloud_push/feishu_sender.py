#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feishu_sender.py - 飞书消息发送模块
使用飞书 Open API，无需本地 lark-cli
"""

import json
import urllib.request
import urllib.error
import time

# 从配置文件读取
try:
    from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_USER_OPEN_ID
except ImportError:
    FEISHU_APP_ID = ""
    FEISHU_APP_SECRET = ""
    FEISHU_USER_OPEN_ID = ""


def get_access_token(app_id, app_secret):
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({
        "app_id": app_id,
        "app_secret": app_secret,
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("code") == 0:
                return result["tenant_access_token"]
            else:
                print(f"❌ 获取 token 失败: {result}")
                return None
    except Exception as e:
        print(f"❌ 获取 token 异常: {e}")
        return None


def send_text_message(token, open_id, content):
    """发送纯文本消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    data = json.dumps({
        "receive_id": open_id,
        "msg_type": "text",
        "content": json.dumps({"text": content}),
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("code") == 0, result
    except Exception as e:
        return False, {"error": str(e)}


def send_interactive_card(token, open_id, card_json):
    """
    发送交互式卡片（V9 风格）
    card_json: 飞书卡片 JSON 对象
    """
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    data = json.dumps({
        "receive_id": open_id,
        "msg_type": "interactive",
        "content": json.dumps(card_json, ensure_ascii=False),
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("code") == 0, result
    except Exception as e:
        return False, {"error": str(e)}


def build_v9_card(urgent_news, important_news, tips, cloud_url, report_date, is_evening=False):
    """
    构建 V9 飞书交互式卡片（carmine header + 三栏统计 + 紧急/重要 + 贴士 + CTA）
    与现有 feishu_card_v7.py 输出格式兼容
    """
    n_urgent = len(urgent_news)
    n_important = len(important_news)
    n_tips = len(tips)
    
    # 日期显示
    date_str = report_date.strftime("%Y年%m月%d日")
    title = f"🛡️ 婴儿安全资讯日报 · {'晚间更新' if is_evening else '早间版'}"
    subtitle = f"{date_str} | 重点关注 {date_str} 安全动态"
    
    # 统计摘要
    if is_evening:
        summary = f"今日新增：🔴 紧急 {n_urgent} 项 · 🟡 重要 {n_important} 项"
    else:
        summary = f"今日概况：🔴 紧急 {n_urgent} 项 · 🟡 重要 {n_important} 项 · 💡 贴士 {n_tips} 条"
    
    # 构建卡片 JSON（飞书卡片格式）
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": "carmine",
        },
        "elements": [
            # 引言
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{subtitle}\n{summary}\n\n> 数据来源：CPSC · FDA · 中国市场监管总局 · 质量报",
                },
            },
            {"tag": "hr"},
        ],
    }
    
    # 紧急新闻
    if urgent_news:
        card["elements"].append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**🔴 紧急提醒**"},
        })
        for news in urgent_news:
            card["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{news['title']}**\n📅 {news.get('date', '')} | 来源：{news.get('source', '')}\n{news.get('desc', '')}",
                },
            })
            # 原文链接按钮
            card["elements"].append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📖 查看原文"},
                        "url": news.get("url", ""),
                        "type": "danger" if news.get("severity") == "urgent" else "default",
                    },
                ],
            })
    
    # 重要提醒
    if important_news:
        card["elements"].append({"tag": "hr"})
        card["elements"].append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**🟡 重要提醒**"},
        })
        for news in important_news:
            card["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{news['title']}**\n📅 {news.get('date', '')} | 来源：{news.get('source', '')}\n{news.get('desc', '')}",
                },
            })
            card["elements"].append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📖 查看原文"},
                        "url": news.get("url", ""),
                        "type": "default",
                    },
                ],
            })
    
    # 贴士
    if tips:
        card["elements"].append({"tag": "hr"})
        card["elements"].append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**💡 安全贴士**"},
        })
        for tip in tips:
            card["elements"].append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"• {tip}"},
            })
    
    # CTA
    card["elements"].append({"tag": "hr"})
    cta_text = "📖 查看完整图文日报（含全部新闻来源链接）" if cloud_url else "完整报告生成中..."
    card["elements"].append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"**{cta_text}**"},
    })
    
    if cloud_url:
        card["elements"].append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📖 查看完整报告"},
                    "url": cloud_url,
                    "type": "primary",
                },
            ],
        })
    
    return card


def send_daily_report(urgent_news, important_news, tips, cloud_url, report_date, is_evening=False):
    """完整发送流程"""
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        print("❌ 飞书凭证未配置，跳过发送")
        print("   请设置环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        return False
    
    print("📤 获取飞书 access token...")
    token = get_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
    if not token:
        print("❌ 获取 token 失败，中止发送")
        return False
    
    print("📤 构建飞书卡片...")
    card = build_v9_card(urgent_news, important_news, tips, cloud_url, report_date, is_evening)
    
    print("📤 发送飞书卡片...")
    success, result = send_interactive_card(token, FEISHU_USER_OPEN_ID, card)
    
    if success:
        print("✅ 飞书卡片发送成功！")
        return True
    else:
        print(f"❌ 飞书卡片发送失败: {result}")
        return False


if __name__ == "__main__":
    # 测试：发送一条测试消息
    print("🧪 测试模式：发送测试消息...")
    test_card = build_v9_card(
        urgent_news=[{"title": "测试紧急新闻", "desc": "这是一条测试", "url": "https://www.cpsc.gov/", "source": "CPSC", "date": "2026-06-21", "severity": "urgent"}],
        important_news=[],
        tips=["测试贴士1", "测试贴士2"],
        cloud_url="https://example.com",
        report_date=__import__("datetime").date.today(),
        is_evening=False,
    )
    print(json.dumps(test_card, ensure_ascii=False, indent=2))
