# X → Telegram 自动转发 设置指南

## 快速开始

### 第 1 步: 创建 Telegram Bot

1. 在 Telegram 搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示设置名称
4. 获得 Bot Token (格式: `123456789:ABCdefGHI...`)
5. 把 Bot 添加到你的目标群组，并设为管理员

### 第 2 步: 获取群组 Chat ID

方法 A (推荐):
1. 把 Bot 加入群组
2. 在群组发送任意消息
3. 访问: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. 找到 `"chat": {"id": -100xxxxxxxxxx}` 即为 Chat ID

方法 B:
1. 把 `@RawDataBot` 加入群组
2. 它会自动回复群组信息，包含 Chat ID
3. 记下后移除该 Bot

### 第 3 步: 配置

编辑 `config.py`:

```python
TELEGRAM_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
TELEGRAM_CHAT_ID = "-1001234567890"

X_ACCOUNTS = [
    "elaboratecon",    # 你想监控的 X 账户
    "sportsbetting",
    # 添加更多...
]
```

### 第 4 步: 运行

**方式 A: 直接运行**
```bash
pip install -r requirements.txt
python main.py
```

**方式 B: Docker (推荐用于服务器)**
```bash
docker-compose up -d
```

**方式 C: 使用 systemd (Linux 服务器)**
```bash
sudo cp x-to-telegram.service /etc/systemd/system/
sudo systemctl enable x-to-telegram
sudo systemctl start x-to-telegram
```

## 进阶配置

### 使用 X API (更可靠)

如果你有 X API 访问权限，可以获得更可靠的推文获取:

1. 申请 X Developer 账号: https://developer.twitter.com
2. 创建 App，获取 Bearer Token
3. 在 `config.py` 中添加:
```python
X_BEARER_TOKEN = "your_bearer_token"
```

### 关键词过滤

只转发包含特定关键词的视频:
```python
KEYWORDS = ["赔率", "odds", "足球", "预测"]
```

### 多群组转发

修改 `TELEGRAM_CHAT_ID` 为列表即可转发到多个群组。

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| Bot 连接失败 | 检查 Token 是否正确，Bot 是否在群组中 |
| 没有检测到视频 | RSS 源可能暂时不可用，会自动重试 |
| 视频下载失败 | 确保安装了 yt-dlp 和 ffmpeg |
| 视频太大 | 调整 `MAX_VIDEO_SIZE_MB` 或 `VIDEO_QUALITY` |

## 部署建议

推荐在以下平台运行:
- **VPS** (Vultr/DigitalOcean): $5/月，最稳定
- **Railway.app**: 免费额度可用
- **Render.com**: 有免费 tier
- **本地树莓派**: 零成本运行
