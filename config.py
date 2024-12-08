import os
import re
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# GitHub相关配置
GITHUB_API = "https://api.github.com"

def parse_github_url(url_or_path):
    """解析GitHub URL或路径,返回owner和repo信息"""
    # 处理完整URL格式
    url_pattern = r"https?://github\.com/([^/]+)/([^/]+)"
    # 处理@格式
    path_pattern = r"@(?:https?://github\.com/)?([^/]+)/([^/]+)"
    # 处理owner/repo格式
    simple_pattern = r"([^/]+)/([^/]+)"
    
    for pattern in [url_pattern, path_pattern, simple_pattern]:
        match = re.match(pattern, url_or_path.strip())
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2)
            }
    return None

# 要监控的仓库列表
REPOS_CONFIG = [
    {
        "name": "gradient-bot", # 显示名称
        **parse_github_url("@https://github.com/fanyilun0/github-monitor-bot")
    },
    # 也支持以下格式:
    # {"name": "repo2", **parse_github_url("owner2/repo2")}
    # {"name": "repo3", **parse_github_url("https://github.com/owner3/repo3")}
]

# Webhook配置
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# 应用名称
APP_NAME = "GitHub Monitor"

# 代理配置
PROXY_URL = 'http://localhost:7890'
USE_PROXY = False
ALWAYS_NOTIFY = True
SHOW_DETAIL = True

# 时间配置
INTERVAL = 28800  # 8小时检查一次
TIME_OFFSET = 0

