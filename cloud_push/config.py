"""
云端推送配置文件
部署时通过 GitHub Secrets 注入，无需提交到代码仓库
"""

import os

# ===== 飞书 Bot 凭证（从 GitHub Secrets 读取）=====
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
FEISHU_USER_OPEN_ID = os.environ.get("FEISHU_USER_OPEN_ID", "ou_e61d62d0f233b8c91fc56ea461f88f0c")

# ===== CloudStudio 部署配置 =====
# HTML 报告部署到 CloudStudio 后获得的固定域名前缀
# 完整 URL 格式: https://<CLOUDSTUDIO_SUBDOMAIN>.app.codebuddy.work
CLOUDSTUDIO_SUBDOMAIN = os.environ.get("CLOUDSTUDIO_SUBDOMAIN", "")

# ===== 推送时间配置 =====
# 早间版：北京时间 09:30
# 晚间版：北京时间 18:30

# ===== 年龄段配置（自动根据日期计算）=====
import datetime

def get_age_stage(date=None):
    """根据日期返回当前重点关注年龄段"""
    if date is None:
        date = datetime.date.today()
    if date < datetime.date(2027, 4, 2):
        return "1-2岁"
    elif date < datetime.date(2028, 4, 2):
        return "2-3岁"
    else:
        return "2-3岁"

def get_date_range(date=None):
    """返回搜索时间范围（最近7天）"""
    if date is None:
        date = datetime.date.today()
    start = date - datetime.timedelta(days=7)
    return start, date
