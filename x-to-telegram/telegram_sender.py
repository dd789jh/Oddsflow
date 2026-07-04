"""
Telegram 发送模块
通过 Telegram Bot API 发送视频和消息到群组
"""

import os
from pathlib import Path

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MAX_VIDEO_SIZE_MB


class TelegramSender:
    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
        self.chat_id = TELEGRAM_CHAT_ID

    def send_video(self, video_path: str, caption: str = "") -> bool:
        """发送视频文件到 Telegram 群组"""
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)

        if file_size_mb > MAX_VIDEO_SIZE_MB:
            print(f"  视频太大 ({file_size_mb:.1f}MB > {MAX_VIDEO_SIZE_MB}MB)，跳过")
            return False

        url = f"{self.base_url}/sendVideo"

        with open(video_path, "rb") as video_file:
            data = {
                "chat_id": self.chat_id,
                "caption": caption[:1024],  # Telegram caption 限制
                "parse_mode": "HTML",
            }
            files = {"video": video_file}

            try:
                resp = requests.post(url, data=data, files=files, timeout=120)
                if resp.status_code == 200:
                    print(f"  ✓ 视频发送成功")
                    return True
                else:
                    error = resp.json().get("description", "Unknown error")
                    print(f"  ✗ 发送失败: {error}")

                    # 如果视频发送失败，尝试发送链接
                    if "file is too big" in error.lower():
                        return self.send_message(caption + "\n\n(视频太大，请点击链接观看)")
            except requests.RequestException as e:
                print(f"  ✗ 网络错误: {e}")

        return False

    def send_message(self, text: str) -> bool:
        """发送纯文本消息"""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            resp = requests.post(url, json=data, timeout=30)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def send_video_by_url(self, video_url: str, caption: str = "") -> bool:
        """通过 URL 发送视频 (适用于可直接访问的视频链接)"""
        url = f"{self.base_url}/sendVideo"
        data = {
            "chat_id": self.chat_id,
            "video": video_url,
            "caption": caption[:1024],
            "parse_mode": "HTML",
        }

        try:
            resp = requests.post(url, json=data, timeout=60)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def test_connection(self) -> bool:
        """测试 Bot 连接是否正常"""
        url = f"{self.base_url}/getMe"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                bot_info = resp.json()["result"]
                print(f"Bot 连接成功: @{bot_info['username']}")
                return True
        except requests.RequestException:
            pass
        print("Bot 连接失败，请检查 TELEGRAM_BOT_TOKEN")
        return False
