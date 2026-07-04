"""
X → Telegram 自动转发主程序

功能:
- 定时监控指定 X 账户的新视频推文
- 自动下载视频
- 转发到 Telegram 群组

使用方法:
1. 安装依赖: pip install -r requirements.txt
2. 安装 yt-dlp: pip install yt-dlp
3. 配置 config.py (Bot Token, Chat ID, 监控账户)
4. 运行: python main.py
"""

import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from config import CHECK_INTERVAL, X_ACCOUNTS
from x_monitor import XMonitor
from telegram_sender import TelegramSender


def cleanup_file(filepath: str):
    """清理临时文件"""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            parent = Path(filepath).parent
            if parent.exists() and not list(parent.iterdir()):
                parent.rmdir()
    except OSError:
        pass


def format_caption(tweet: dict) -> str:
    """格式化 Telegram 消息标题"""
    account = tweet.get("account", "unknown")
    text = tweet.get("text", "")
    url = tweet.get("url", "")

    # 清理 HTML 实体
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")

    # 截断过长文本
    if len(text) > 500:
        text = text[:500] + "..."

    caption = f"<b>@{account}</b>\n\n{text}\n\n🔗 <a href=\"{url}\">原文链接</a>"
    return caption


def run_once(monitor: XMonitor, sender: TelegramSender):
    """执行一次检查"""
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{now}] 检查更新中... (监控 {len(X_ACCOUNTS)} 个账户)")

    new_videos = monitor.get_new_video_tweets()

    if not new_videos:
        print("  没有新视频")
        return

    print(f"  发现 {len(new_videos)} 个新视频")

    for tweet in new_videos:
        tweet_id = tweet["id"]
        tweet_url = tweet["url"]
        account = tweet.get("account", "")

        print(f"\n  处理: @{account} - {tweet_url}")

        # 下载视频
        video_path = monitor.download_video(tweet_url)

        if video_path:
            # 发送到 Telegram
            caption = format_caption(tweet)
            success = sender.send_video(video_path, caption)
            cleanup_file(video_path)
        else:
            # 下载失败，发送链接
            print("  视频下载失败，发送链接")
            caption = format_caption(tweet)
            success = sender.send_message(caption)

        if success:
            monitor.mark_as_sent(tweet_id)
            print(f"  ✓ 已转发 tweet {tweet_id}")
        else:
            print(f"  ✗ 转发失败 tweet {tweet_id}")

        # 避免发送太快
        time.sleep(3)


def main():
    print("=" * 50)
    print("  X → Telegram 自动转发")
    print("=" * 50)
    print(f"\n监控账户: {', '.join(X_ACCOUNTS)}")
    print(f"检查间隔: {CHECK_INTERVAL} 秒")
    print()

    sender = TelegramSender()
    if not sender.test_connection():
        print("\n请先配置 config.py 中的 TELEGRAM_BOT_TOKEN")
        sys.exit(1)

    monitor = XMonitor()

    # 优雅退出
    def signal_handler(sig, frame):
        print("\n\n正在退出...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\n开始监控... (Ctrl+C 退出)\n")

    while True:
        try:
            run_once(monitor, sender)
        except Exception as e:
            print(f"\n  错误: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
