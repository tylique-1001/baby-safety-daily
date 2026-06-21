# 🚀 婴儿安全日报 · 云端推送部署指南

## 问题背景

原方案依赖 Mac 本地运行的 WorkBuddy 后端（ACP），Mac 锁屏/休眠时自动化无法执行。

**本方案**：完全在 GitHub Actions 云端运行，不依赖 Mac。

---

## 架构

```
GitHub Actions (定时)
    ↓
news_fetcher.py  →  抓取 CPSC/FDA/中文来源
    ↓
main.py  →  生成 HTML 报告 → 写入 docs/
    ↓
feishu_sender.py  →  调用飞书 Open API → 发送卡片到你的飞书
    ↓
GitHub Pages  →  托管 HTML 报告（永久链接）
```

---

## 第一步：获取飞书 Bot 凭证

### 方式 A（推荐）：从现有 lark-cli 配置获取

你的 Mac 上已有配置，`app_id` 是：
```
cli_aabff12f9ab89be2
```

`app_secret` 存在 macOS Keychain 里，按以下步骤取出：

1. 打开「钥匙串访问」（Keychain Access）app
2. 搜索：`appsecret:cli_aabff12f9ab89be2`
3. 双击条目，展开「显示密码」，输入 Mac 密码
4. 复制 `app_secret` 字符串

### 方式 B：在飞书开放平台创建新应用

如果方式 A 取不到，可以创建新应用：

1. 访问：https://open.feishu.cn/app（中国版飞书）
2. 点击「创建自建应用」
3. 应用名称：`婴儿安全日报推送Bot`
4. 进入应用 → 「凭证与基础信息」→ 复制 `App ID` 和 `App Secret`
5. 进入「事件订阅」→ 添加机器人能力
6. 获取你的 `open_id`：`ou_e61d62d0f233b8c91fc56ea461f88f0c`（已有）

---

## 第二步：创建 GitHub 仓库

```bash
# 在你的 GitHub 创建新仓库，例如：baby-safety-daily
# 然后在本地初始化并推送

cd /Users/zltang/Desktop/2026-06-19-22-48-16
git init
git add cloud_push/ .github/
git commit -m "初始提交：云端推送脚本"
git remote add origin https://github.com/<你的用户名>/baby-safety-daily.git
git push -u origin main
```

---

## 第三步：设置 GitHub Secrets

进入仓库 → Settings → Secrets and variables → Actions → New repository secret

添加以下 3 个 Secret：

| Name | Value |
|------|-------|
| `FEISHU_APP_ID` | `cli_aabff12f9ab89be2` |
| `FEISHU_APP_SECRET` | *(从 Keychain 取出的 app_secret)* |
| `FEISHU_USER_OPEN_ID` | `ou_e61d62d0f233b8c91fc56ea461f88f0c` |

---

## 第四步：启用 GitHub Pages

进入仓库 → Settings → Pages：

- Source：`Deploy from a branch`
- Branch：`main` / `/docs`
- 点击 Save

等待 1-2 分钟，访问 `https://<用户名>.github.io/baby-safety-daily/docs/` 确认可访问。

---

## 第五步：手动触发测试

进入仓库 → Actions → 选择「婴儿安全日报 · 早间版」→ Run workflow

观察运行日志，确认：
- ✅ 新闻采集成功
- ✅ HTML 生成成功
- ✅ 飞书卡片发送成功

---

## 定时执行时间

| Workflow | Cron | 北京时间 |
|-----------|-------|---------|
| 早间版 | `30 1 * * *` UTC | **每天 09:30** |
| 晚间版 | `30 10 * * *` UTC | **每天 18:30** |

---

## 文件说明

```
cloud_push/
├── main.py              # 主入口
├── config.py            # 配置文件（从环境变量读取）
├── news_fetcher.py     # 新闻采集（CPSC/FDA/中文来源）
├── feishu_sender.py   # 飞书卡片发送（Open API）
└── README.md           # 本文档

.github/workflows/
├── daily-morning.yml   # 早间版 GitHub Actions
└── daily-evening.yml  # 晚间版 GitHub Actions
```

---

## 故障排查

### 飞书发送失败（token 获取失败）
→ 检查 `FEISHU_APP_SECRET` 是否正确；确认应用在飞书开放平台状态为「已启用」

### HTML 报告未更新
→ 检查 GitHub Pages 是否指向 `/docs` 目录；检查 Actions 日志是否有 git push 错误

### 新闻采集为空
→ CPSC/FDA 网站可能有反爬；可后续接入 News API（有免费额度）

---

## 后续增强建议

1. **接入 News API**：替换爬虫方案，更稳定（`newsapi.org` 免费 100 次/天）
2. **完善 HTML 模板**：将现有 V4.4 完整 CSS 移植过来
3. **添加失败告警**：GitHub Actions 失败时发飞书 webhook 通知
4. **多来源支持**：增加更多 RSS 源（欧盟 RAPEX、澳洲 ACCC 等）
