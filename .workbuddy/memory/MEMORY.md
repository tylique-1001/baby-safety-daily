# 婴儿安全资讯日报 · 项目约定

## 推送目标
- 接收用户：ZLTang（飞书 open_id: ou_e61d62d0f233b8c91fc56ea461f88f0c）
- 推送方式：飞书 IM（lark-cli bot身份发送Markdown消息）+ CloudStudio公网链接
- 完整报告通过 CloudStudio 部署获得公网 URL（如 https://xxx.app.codebuddy.work）
- 飞书消息包含摘要 + 完整报告公网链接

## 年龄段策略
- 2026-06-19 ~ 2027-04-02：重点关注 1-2 岁
- 2027-04-02 ~ 2028-04-02：重点关注 2-3 岁
- 2028-04-02 ~ 2029-04-02：重点关注 2-3 岁
- 规则："重点关注"不是"只推荐"，各年龄段内容均应覆盖

## 覆盖类别（13类）
1. 喂养器具 2. 洗护用品 3. 服饰寝具 4. 婴幼儿食品 5. 食具类
6. 启智玩具 7. 家具类 8. 电子电器 9. 纸尿裤/尿布
10. 出行安全 11. 家居安全 12. 宝宝药箱/健康 13. 其他用品

## 输出文件
- HTML报告：outputs/daily-reports/YYYY-MM-DD-婴儿安全日报.html
- Markdown版本：outputs/wechat-articles/YYYY-MM-DD-婴儿安全日报.md

## 自动化（双推送）
- 早间版 ID: automation-1781880617553 → 每日 9:30 全量采集推送
- 晚间版 ID: automation-1781886693385 → 每日 18:30 增量更新推送
- 有效期：2026-06-19 ~ 2029-04-02

## 设计规范（V4.4 "Lumin" — 2026-06-20 最终版）

### HTML 报告
- 设计系统：Pro v4 "Lumin"
- 主色：--coral #FF5E62 / --red #DC2626 / --amber #D97706 / --blue #3B82F6
- 背景：--bg #FAFAF9
- 关键特性：reading progress bar、粘性导航+TOC（**滚动高亮当前锚点**）、glassmorphism统计卡、入场动画(cardIn)、数字计数器+迷你进度条、Back-to-Top、Web Share API FAB、贴士图标光晕、**品类芯片可点击筛选**（无内容品类自动半透明）、**新闻卡片折叠/展开**（点击标题栏收起正文，箭头旋转动画）、**滚动位置恢复 v3**（卡片锚点`scrollIntoView` + mousedown 最早保存 + `setTimeout`揭示不依赖 rAF；每条源链接返回精确恢复，无闪屏）、**新闻源链接截断**（≤3全展示，>3展示前3 + "+N更多来源"可展开/收起）
- 打印样式已内置（@media print）

### 飞书卡片
- 版本：V9 珊瑚画廊·信息均衡版
- header：🛡️ emoji + carmine 模板
- 结构：概况引语 → 三栏统计（每栏含简短解释）→ 紧急（结构化分行+三标签）→ 重要提醒（**含简短描述body字段**，编号+来源日期+风险说明）→ 品类覆盖（"N类活跃·M类暂无新增"）→ 贴士（独立 grey 卡）→ CTA导语+primary按钮
- CTA："📖 查看完整图文日报"
- 脚本：scripts/feishu_card_v7.py（实际运行 V9 逻辑）

## 🔗 链接铁律（最高优先级，每次执行必检）

> **飞书按钮 / HTML source-tag / Markdown 中的每一条链接，必须是具体原文 URL，绝对禁止使用官网首页。**

### 红线（违反直接阻断发送）
| ❌ 禁止（官网首页/导航页） | ✅ 必须（具体文章/召回页） |
|---|---|
| `fda.gov/safety/recalls/` | `fda.gov/food/outbreaks/.../index.html` |
| `cpsc.gov/` 或 `cpsc.gov/Recalls/` | `cpsc.gov/Recalls/2026/LiKee-...` |
| `cctv.com/` | `cctv.com/2026/06/19/ARTI-xxx.html` |
| `samr.gov.cn/` | `samrdprc.org.cn/aqjy/.../article.html` |
| `cdc.gov/` | `cdc.gov/botulism/outbreaks/.../index.html` |
| `nhtsa.gov/` | `nhtsa.gov/recalls?nhtsaId=xxx` |

### 硬验证机制
- **脚本层**：`scripts/feishu_card_v7.py` 内置 `validate_all_urls()` —— 发送前自动扫描，发现首页 URL 直接 `sys.exit(1)` 并报错
- **自动化层**：生成卡片/HTML 后、发送前，必须用 grep 扫描所有 URL，确认无一命中首页模式
- **路径深度规则**：URL 至少要有 2 级以上具体路径（如 `/article/id`），仅有 `/news/`、`/food/` 这类一级目录视为不合格

### 多源策略
- 每条新闻有多个来源时，创建多个按钮/链接，每个对应一个具体原文 URL
- HTML 中源链接展示规则：≤3 个全部展示，>3 个展示前 3 个 + "+N 更多来源 ▼" 展开按钮
- 优先选取官方源（FDA/CPSC/CDC/市场监管总局），辅以媒体报道备份

### 🔙 阅读位置恢复 v3（无闪屏，每链接必恢复）
- HTML 所有外部链接（source-tag）必须带 `target="_blank" rel="noopener"`
- **`<head>` 同步预处理**（`<style>` 之前）：读 sessionStorage 的 `{y, ci}` JSON，若有效 → 给 `<html>` 加 `scroll-restoring` class
- **CSS**：`html.scroll-restoring{visibility:hidden}` — 整页隐藏
- **四通道保存**（优先级从高到低）：
  1. `mousedown` 捕获阶段（桌面端最早，导航前必触发）
  2. `touchstart` 被动监听（移动端手指按下）
  3. `pagehide`（页面离开前兜底）
  4. `scroll` debounce 200ms（日常滚动）
- **保存内容**：`{ y: scrollY像素值, ci: 当前视口卡片data-index }` — 卡片锚点 + 像素双保险
- **恢复策略**：
  - 策略A：卡片锚点 `scrollIntoView({block:'start', behavior:'instant'})` + `scrollBy(0,-80)` — 不受页面高度变化影响
  - 策略B：像素 `scrollTo(0, y)` — 兜底
- **揭示**：`setTimeout(fn, 80)` — 不依赖 rAF（hidden 页面 rAF 可能被节流）
- **双触发**：body 末尾立即执行 + `window.onload` 再次执行
- **3秒兜底**：强制去 class 显示页面
- **bfcache**：`pageshow` 中 `e.persisted=true` → 仅去 class（浏览器原生恢复）
- **绝对禁止**：rAF 循环恢复（hidden 页面不可靠）；`scrollRestoration='manual'`（不应干扰 bfcache）

## 🛡️ 推送前质量关卡（不可跳过）

> **每次推送（早间+晚间）在 `present_files` 和飞书发送之前，必须逐项验证以下 6 条。任何一项不通过 → 修正后从头重新检查，禁止带病发送。**

| # | 检查项 | 验证命令 |
|---|--------|----------|
| 1 | URL 全是原文（非首页） | `python3 scripts/feishu_card_v7.py` exit=0 + grep HTML 扫描 |
| 2 | HTML 含滚动恢复 v3 | `grep -c '__ds' HTML文件` > 0 |
| 3 | HTML 含源截断代码 | `grep -c 'has-more' HTML文件` > 0 |
| 4 | source-tag 有 target=_blank | `grep -c 'target="_blank"' HTML文件` > 0 |
| 5 | 飞书卡片脚本无报错 | `python3 scripts/feishu_card_v7.py` exit code = 0 |
| 6 | CloudStudio 可访问 | `curl` 返回 HTTP 200 |

### 自动化 prompt 要求
- 早间版 (automation-1781880617553) 和晚间版 (automation-1781886693385) 的 prompt 中**均已自包含完整代码**（不依赖"参见另一个"）
- 晚间版 prompt 包含完整的滚动恢复 v3 + 源截断代码块，可直接复制粘贴
- 两个 prompt 的末尾都包含上述 6 项质量关卡

## 新闻来源要求
- 必须有真实来源链接（遵循上述链接铁律）
- 每条标注严重程度：🔴紧急(severity danger) 🟡重要(severity prevent)
- 每条含🩺症状 + 🛡️预防 + ✅行动 三标签
