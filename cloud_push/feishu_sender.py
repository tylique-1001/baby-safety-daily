#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feishu_sender.py - 飞书消息发送模块
使用 subprocess curl，OS 级硬超时，GitHub Actions 安全
"""

import json
import subprocess
import tempfile
import os
import time

# 从配置文件读取
try:
    from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_USER_OPEN_ID
except ImportError:
    FEISHU_APP_ID = ""
    FEISHU_APP_SECRET = ""
    FEISHU_USER_OPEN_ID = ""


def _curl_post(url, json_body, timeout=20):
    """用 curl 发 POST JSON 请求，OS 级硬超时"""
    t0 = time.time()
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="feishu_")
    os.close(tmp_fd)
    proc = None
    try:
        proc = subprocess.Popen(
            ["curl", "-sS",
             "--max-time", str(timeout),
             "--connect-timeout", "8",
             "-H", "Content-Type: application/json",
             "-X", "POST",
             "-d", json_body,
             "-o", tmp_path,
             url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        proc.wait(timeout=timeout + 5)
        elapsed = time.time() - t0

        if proc.returncode != 0:
            print(f"    ⚠️ curl POST {url[:50]} exit={proc.returncode} ({elapsed:.1f}s)")
            return None

        with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
            result = json.loads(f.read())
        return result

    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        if proc:
            proc.kill()
        print(f"    ⛔ curl POST {url[:50]} 硬超时 ({elapsed:.1f}s)")
        return None
    except Exception as e:
        elapsed = time.time() - t0
        if proc and proc.poll() is None:
            proc.kill()
        print(f"    ⚠️ curl POST {url[:50]} 异常 ({elapsed:.1f}s): {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def get_access_token(app_id, app_secret):
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    body = json.dumps({
        "app_id": app_id,
        "app_secret": app_secret,
    }, ensure_ascii=False)

    print("    → 请求飞书 token...", flush=True)
    result = _curl_post(url, body, timeout=20)

    if result is None:
        print("❌ 获取 token 失败: 网络错误或超时")
        return None

    if result.get("code") == 0:
        print(f"    ✓ token 获取成功 (expire={result.get('expire', '?')}s)")
        return result["tenant_access_token"]
    else:
        print(f"❌ 获取 token 失败: code={result.get('code')} msg={result.get('msg', '')}")
        return None


def send_interactive_card(token, open_id, card_json):
    """
    发送交互式卡片（V9 风格）
    card_json: 飞书卡片 JSON 对象
    """
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    payload = json.dumps({
        "receive_id": open_id,
        "msg_type": "interactive",
        "content": json.dumps(card_json, ensure_ascii=False),
    }, ensure_ascii=False)

    headers = [
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: Bearer {token}",
    ]

    t0 = time.time()
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="feishu_send_")
    os.close(tmp_fd)
    proc = None
    try:
        proc = subprocess.Popen(
            ["curl", "-sS",
             "--max-time", "20",
             "--connect-timeout", "8",
             *headers,
             "-X", "POST",
             "-d", payload,
             "-o", tmp_path,
             url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        proc.wait(timeout=25)
        elapsed = time.time() - t0

        if proc.returncode != 0:
            print(f"    ⚠️ 发送卡片 curl exit={proc.returncode} ({elapsed:.1f}s)")
            return False, {"error": f"curl exit={proc.returncode}"}

        with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
            result = json.loads(f.read())

        success = result.get("code") == 0
        if not success:
            print(f"    ⚠️ 飞书返回错误: code={result.get('code')} msg={result.get('msg','')}")
        return success, result

    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        if proc:
            proc.kill()
        print(f"    ⛔ 发送卡片硬超时 ({elapsed:.1f}s)")
        return False, {"error": "timeout"}
    except Exception as e:
        elapsed = time.time() - t0
        if proc and proc.poll() is None:
            proc.kill()
        print(f"    ⚠️ 发送卡片异常 ({elapsed:.1f}s): {e}")
        return False, {"error": str(e)}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def build_v9_card(urgent_news, important_news, reminder_news, tips, cloud_url, report_date, is_evening=False):
    """
    构建 V9 飞书交互式卡片（carmine header + 四栏统计 + 紧急/重要/提醒 + 贴士 + CTA）
    与现有 feishu_card_v7.py 输出格式兼容
    """
    n_urgent = len(urgent_news)
    n_important = len(important_news)
    n_reminder = len(reminder_news)
    n_tips = len(tips)

    # 日期显示
    date_str = report_date.strftime("%Y年%m月%d日")
    title = f"🛡️ 婴儿安全资讯日报 · {'晚间更新' if is_evening else '早间版'}"
    subtitle = f"{date_str} | 重点关注 {date_str} 安全动态"

    # 统计摘要
    all_news = n_urgent + n_important + n_reminder
    summary = f"今日概况：🔴 紧急 {n_urgent} · 🟡 重要 {n_important} · 🟠 提醒 {n_reminder} · 💡 贴士 {n_tips}"

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
                    "content": f"{subtitle}\n{summary}\n\n> 数据来源：市场监管总局 · CQN · 央视新闻 · 财新",
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
            lines = [f"**{news['title']}**"]
            lines.append(f"📅 {news.get('date', '')} | 来源：{news.get('source', '')}")
            if news.get('body') or news.get('desc'):
                lines.append(news.get('body') or news.get('desc', ''))
            # V9: 症状/预防/行动 三标签（如果有）
            if news.get('symptom'):
                lines.append(f"🩺 症状：{news['symptom']}")
            if news.get('prevent'):
                lines.append(f"🛡️ 预防：{news['prevent']}")
            if news.get('action'):
                lines.append(f"✅ 行动：{news['action']}")
            card["elements"].append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "\n".join(lines)},
            })
            # 原文链接按钮（支持多源）
            urls = news.get('urls', [])
            single_url = news.get('url', '')
            if single_url and not urls:
                urls = [(news.get('source', '原文'), single_url)]
            if urls:
                card["elements"].append({
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": f"📖 {label}"},
                            "url": url,
                            "type": "danger" if news.get("severity") == "urgent" else "default",
                        }
                        for label, url in urls
                    ],
                })

    # 重要提醒
    if important_news:
        card["elements"].append({"tag": "hr"})
        card["elements"].append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**🟡 重要提醒**"},
        })
        for i, news in enumerate(important_news):
            lines = [f"**{i+1}. {news['title']}**"]
            lines.append(f"📅 {news.get('date', '')} | 来源：{news.get('source', '')}")
            if news.get('body') or news.get('desc'):
                lines.append(news.get('body') or news.get('desc', ''))
            card["elements"].append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "\n".join(lines)},
            })
            # 原文链接
            single_url = news.get('url', '')
            if single_url:
                card["elements"].append({
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "📖 查看原文"},
                            "url": single_url,
                            "type": "default",
                        },
                    ],
                })

    # 🟠 提醒关注
    if reminder_news:
        card["elements"].append({"tag": "hr"})
        card["elements"].append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**🟠 提醒关注**"},
        })
        for i, news in enumerate(reminder_news):
            lines = [f"**{i+1}. {news['title']}**"]
            lines.append(f"📅 {news.get('date', '')} | 来源：{news.get('source', '')}")
            if news.get('body') or news.get('desc'):
                lines.append(news.get('body') or news.get('desc', ''))
            # 品类标签
            cats = news.get('categories', [])
            if cats:
                lines.append("📂 " + " · ".join(cats))
            card["elements"].append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": "\n".join(lines)},
            })
            single_url = news.get('url', '')
            if single_url:
                card["elements"].append({
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "📖 查看原文"},
                            "url": single_url,
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


def send_plain_text_message(token, open_id, text):
    """兜底：发送纯文本消息（卡片失败时的最后手段）"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"
    payload = json.dumps({
        "receive_id": open_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }, ensure_ascii=False)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="feishu_text_")
    os.close(tmp_fd)
    proc = None
    try:
        proc = subprocess.Popen(
            ["curl", "-sS", "--max-time", "15", "--connect-timeout", "8",
             "-H", "Content-Type: application/json",
             "-H", f"Authorization: Bearer {token}",
             "-X", "POST", "-d", payload, "-o", tmp_path, url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        proc.wait(timeout=20)
        if proc.returncode != 0:
            return False
        with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
            result = json.loads(f.read())
        return result.get("code") == 0
    except Exception:
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def send_daily_report(urgent_news, important_news, reminder_news, tips, cloud_url, report_date, is_evening=False):
    """完整发送流程（单次，无重试）"""
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
    card = build_v9_card(urgent_news, important_news, reminder_news, tips, cloud_url, report_date, is_evening)

    print("📤 发送飞书卡片...")
    success, result = send_interactive_card(token, FEISHU_USER_OPEN_ID, card)

    if success:
        print("✅ 飞书卡片发送成功！")
        return True
    else:
        print(f"❌ 飞书卡片发送失败: {result}")
        return False


def send_daily_report_with_retry(urgent_news, important_news, reminder_news, tips, cloud_url, report_date, is_evening=False,
                                  max_retries=3, base_delay=5):
    """
    🛡️ 带重试的发送（自愈引擎调用）
    第1层: 卡片发送 → 失败重试3次
    第2层: token过期 → 刷新token重试
    第3层: 纯文本兜底 → 卡片彻底失败时发送摘要文本
    """
    if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
        print("❌ 飞书凭证未配置，跳过发送", flush=True)
        return False

    # 生成纯文本兜底内容
    fallback_text = "🛡️ 婴儿安全资讯日报\n"
    fallback_text += report_date.strftime("%Y年%m月%d日") + "\n"
    if urgent_news:
        fallback_text += f"\n🔴 紧急提醒 {len(urgent_news)} 项:\n"
        for n in urgent_news[:3]:
            fallback_text += f"• {n['title']}\n"
    if important_news:
        fallback_text += f"\n🟡 重要提醒 {len(important_news)} 项:\n"
        for n in important_news[:3]:
            fallback_text += f"• {n['title']}\n"
    if cloud_url:
        fallback_text += f"\n📖 完整报告: {cloud_url}"

    last_error = None
    for attempt in range(1, max_retries + 1):
        print(f"  📤 发送尝试 {attempt}/{max_retries}...", flush=True)

        # 每次重试都重新获取 token（防止 token 过期）
        token = get_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
        if not token:
            last_error = "token_auth_failed"
            if attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))
                print(f"  ⏳ token获取失败，{delay}秒后重试...", flush=True)
                time.sleep(delay)
            continue

        # 构建卡片
        card = build_v9_card(urgent_news, important_news, reminder_news, tips, cloud_url, report_date, is_evening)

        # 发送卡片
        success, result = send_interactive_card(token, FEISHU_USER_OPEN_ID, card)
        if success:
            print(f"  ✅ 飞书卡片发送成功！（第{attempt}次尝试）", flush=True)
            return True

        last_error = f"send_failed: {result.get('msg', result.get('error', 'unknown'))}"
        print(f"  ⚠️ 发送失败: {last_error}", flush=True)

        if attempt < max_retries:
            delay = base_delay * (2 ** (attempt - 1))
            print(f"  ⏳ {delay}秒后重试...", flush=True)
            time.sleep(delay)

    # 🆘 第3层：纯文本兜底
    print("  🆘 卡片发送全部失败，尝试纯文本兜底...", flush=True)
    token = get_access_token(FEISHU_APP_ID, FEISHU_APP_SECRET)
    if token:
        if send_plain_text_message(token, FEISHU_USER_OPEN_ID, fallback_text):
            print("  ✅ 纯文本兜底发送成功！", flush=True)
            return True
        else:
            print("  ❌ 纯文本兜底也失败了", flush=True)
    else:
        print("  ❌ 无法获取token进行兜底发送", flush=True)

    print(f"  ❌ 所有发送方式均失败，最后错误: {last_error}", flush=True)
    return False


if __name__ == "__main__":
    # 测试：打印卡片 JSON（不实际发送）
    print("🧪 测试模式：生成测试卡片...")
    test_card = build_v9_card(
        urgent_news=[{"title": "测试紧急新闻", "desc": "这是一条测试", "url": "https://www.cpsc.gov/", "source": "CPSC", "date": "2026-06-21", "severity": "urgent"}],
        important_news=[],
        tips=["测试贴士1", "测试贴士2"],
        cloud_url="https://example.com",
        report_date=__import__("datetime").date.today(),
        is_evening=False,
    )
    print(json.dumps(test_card, ensure_ascii=False, indent=2))
