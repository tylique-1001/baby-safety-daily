#!/usr/bin/env python3
"""GitHub Actions 环境诊断：逐步骤测试每个网络请求"""
import sys, time, subprocess, os

def test_curl(url, label, timeout=8):
    print(f"\n[{label}] curl测试: {url}", flush=True)
    t0 = time.time()
    try:
        proc = subprocess.run(
            ["curl", "-sS", "--max-time", str(timeout), "--connect-timeout", "5",
             "-H", "User-Agent: Mozilla/5.0",
             "-o", "/dev/null", "-w", "%{http_code}:%{size_download}:%{time_total}",
             url],
            capture_output=True, text=True, timeout=timeout+5
        )
        elapsed = time.time() - t0
        parts = proc.stdout.strip().split(":")
        if len(parts) >= 3:
            print(f"  状态码={parts[0]}  大小={parts[1]}B  curl用时={parts[2]}s  总耗时={elapsed:.1f}s", flush=True)
        else:
            print(f"  stdout={proc.stdout[:200]} stderr={proc.stderr[:200]} ({elapsed:.1f}s)", flush=True)
    except subprocess.TimeoutExpired:
        print(f"  ⛔ subprocess超时! ({time.time()-t0:.1f}s)", flush=True)
    except Exception as e:
        print(f"  ❌ 异常: {e} ({time.time()-t0:.1f}s)", flush=True)

# 步骤1: import
print("="*60, flush=True)
print("步骤1: 环境信息", flush=True)
print("="*60, flush=True)
for cmd, label in [
    ("python3 --version", "Python版本"),
    ("curl --version | head -1", "curl版本"),
    ("cat /etc/os-release | head -3", "OS"),
    ("python3 -c 'import socket; print(socket.gethostbyname(\"www.cpsc.gov\"))'", "CPSC DNS解析"),
    ("python3 -c 'import socket; print(socket.gethostbyname(\"www.fda.gov\"))'", "FDA DNS解析"),
    ("python3 -c 'import socket; print(socket.gethostbyname(\"open.feishu.cn\"))'", "飞书 DNS解析"),
]:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    print(f"  {label}: {r.stdout.strip()[:100]}", flush=True)
    if r.stderr.strip():
        print(f"    stderr: {r.stderr.strip()[:100]}", flush=True)

# 步骤2: 测试每个 URL
print("\n" + "="*60, flush=True)
print("步骤2: 逐个测试 URL", flush=True)
print("="*60, flush=True)

urls = [
    ("https://www.cpsc.gov/Recalls", "CPSC召回页", 12),
    ("https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts", "FDA安全页", 12),
    ("https://www.cqn.com.cn/", "中国质量报", 8),
    ("https://www.samr.gov.cn/xw/zj/", "市场监管总局", 8),
    ("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", "飞书Token API", 10),
]

for url, label, timeout in urls:
    test_curl(url, label, timeout)

# 步骤3: 测试完整 news_fetcher
print("\n" + "="*60, flush=True)
print("步骤3: 测试 news_fetcher.fetch_url", flush=True)
print("="*60, flush=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from news_fetcher import fetch_url
for url, label, timeout in urls[:4]:  # 跳过飞书 API
    t0 = time.time()
    body = fetch_url(url, timeout=min(timeout, 10))
    print(f"  fetch_url {label}: {len(body)}字符 ({time.time()-t0:.1f}s)", flush=True)

print("\n" + "="*60, flush=True)
print("步骤4: 测试完整 fetch_news", flush=True)
print("="*60, flush=True)
from news_fetcher import fetch_news, format_for_report
t0 = time.time()
items = fetch_news(days_back=3, mode="morning")
print(f"  fetch_news 完成: {len(items)}条 ({time.time()-t0:.1f}s)", flush=True)

print("\n" + "="*60, flush=True)
print("✅ 诊断完成！", flush=True)
