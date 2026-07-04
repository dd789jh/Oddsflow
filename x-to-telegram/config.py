"""
X to Telegram 自动转发配置
"""

# Telegram Bot 配置
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"  # 从 @BotFather 获取
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID"      # 目标群组 ID (例: -1001234567890)

# 要监控的 X 账户列表 (不带 @)
X_ACCOUNTS = [
    "elaboratecon",
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
