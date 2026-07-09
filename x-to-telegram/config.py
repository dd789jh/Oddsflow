"""
X to Telegram 自动转发配置

敏感信息 (Token, Chat ID) 存放在 .env 文件中，不会提交到 Git。
"""

import os
from pathlib import Path

# 加载 .env 文件
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# Telegram Bot 配置 (从 .env 读取)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# 要监控的 X 账户列表 (不带 @)
X_ACCOUNTS = [
    "centregoals",
    # 添加更多账户...
]

# 监控关键词 (可选，为空则转发所有视频)
KEYWORDS = []

# 检查间隔 (秒) - 建议 300-600 秒避免被限速
CHECK_INTERVAL = 300

# 视频下载设置
MAX_VIDEO_SIZE_MB = 50  # Telegram 限制 50MB
VIDEO_QUALITY = "best[filesize<50M]/best"

# 数据库文件 (记录已转发的推文，避免重复)
DB_FILE = "sent_posts.json"
