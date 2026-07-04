"""
Webhook 服务器 - 接收 iOS 快捷指令发来的 X 视频链接
自动下载视频并转发到 Telegram 群组

工作流程:
  iOS X App → Share Sheet → 快捷指令 → POST 到这个服务器 → 下载视频 → 发到 Telegram

运行: python webhook_server.py
"""

import hashlib
import hmac
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    MAX_VIDEO_SIZE_MB,
    VIDEO_QUALITY,
)
from telegram_sender import TelegramSender

# Webhook 安全密钥 - 防止别人乱调用你的接口
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "change-me-to-a-random-string")

# 服务器端口
PORT = int(os.environ.get("PORT", "8899"))

sender = TelegramSender()


def is_valid_x_url(url: str) -> bool:
    """验证是否为合法的 X/Twitter 链接"""
    parsed = urlparse(url)
    return (
        parsed.scheme in ("http", "https")
        and parsed.hostname in ("x.com", "twitter.com", "www.x.com", "www.twitter.com")
        and re.search(r"/status/\d+", parsed.path) is not None
    )


def extract_tweet_info(url: str) -> dict:
    """从 URL 提取推文信息"""
    match = re.search(r"(?:x\.com|twitter\.com)/(\w+)/status/(\d+)", url)
    if match:
        return {"account": match.group(1), "tweet_id": match.group(2), "url": url}
    return {}


def download_and_send(url: str, caption_text: str = ""):
    """后台线程: 下载视频并发送到 Telegram"""
    info = extract_tweet_info(url)
    if not info:
        print(f"  无效链接: {url}")
        return

    account = info["account"]
    tweet_id = info["tweet_id"]
    clean_url = f"https://x.com/{account}/status/{tweet_id}"

    print(f"\n  处理: @{account} - {clean_url}")

    # 构建 caption
    parts = [f"<b>@{account}</b>"]
    if caption_text:
        safe_text = caption_text.replace("<", "&lt;").replace(">", "&gt;")
        parts.append(safe_text)
    parts.append(f'🔗 <a href="{clean_url}">原文链接</a>')
    caption = "\n\n".join(parts)

    # 下载视频
    tmp_dir = tempfile.mkdtemp(prefix="x2tg_")
    output_path = f"{tmp_dir}/%(id)s.%(ext)s"

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "-f", VIDEO_QUALITY,
                "--max-filesize", f"{MAX_VIDEO_SIZE_MB}M",
                "-o", output_path,
                "--no-playlist",
                clean_url,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        video_path = None
        if result.returncode == 0:
            files = list(Path(tmp_dir).glob("*.*"))
            if files:
                video_path = str(files[0])

        if video_path:
            success = sender.send_video(video_path, caption)
            try:
                os.remove(video_path)
                Path(tmp_dir).rmdir()
            except OSError:
                pass
        else:
            print("  视频下载失败，发送链接")
            success = sender.send_message(caption)

        if success:
            print(f"  ✓ 转发成功")
        else:
            print(f"  ✗ 转发失败")

    except subprocess.TimeoutExpired:
        print("  ✗ 下载超时")
        sender.send_message(caption + "\n\n⚠️ 视频下载超时，请点击链接查看")


def verify_secret(provided_secret: str) -> bool:
    """验证请求密钥"""
    return hmac.compare_digest(provided_secret, WEBHOOK_SECRET)


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/forward":
            self.send_response(404)
            self.end_headers()
            return

        # 读取请求体
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 10000:
            self.send_response(413)
            self.end_headers()
            return

        body = self.rfile.read(content_length).decode("utf-8")

        # 验证密钥
        auth = self.headers.get("X-Webhook-Secret", "")
        if not verify_secret(auth):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error": "unauthorized"}')
            return

        # 解析请求
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            # 支持纯文本 URL
            data = {"url": body.strip()}

        url = data.get("url", "").strip()
        caption = data.get("caption", "")

        if not url:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "missing url"}')
            return

        if not is_valid_x_url(url):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "not a valid X/Twitter URL"}')
            return

        # 在后台处理 (立即返回给 iOS Shortcut)
        thread = threading.Thread(
            target=download_and_send, args=(url, caption), daemon=True
        )
        thread.start()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "processing", "url": url}).encode())

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "X → Telegram 转发服务运行中 ✓".encode("utf-8")
        )

    def log_message(self, format, *args):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {args[0]}")


def main():
    print("=" * 50)
    print("  X → Telegram Webhook 服务器")
    print("=" * 50)

    if WEBHOOK_SECRET == "change-me-to-a-random-string":
        print("\n⚠️  警告: 请设置 WEBHOOK_SECRET 环境变量!")
        print("   export WEBHOOK_SECRET=$(openssl rand -hex 16)")

    if not sender.test_connection():
        print("\n请先配置 config.py 中的 TELEGRAM_BOT_TOKEN")
        return

    print(f"\n服务器端口: {PORT}")
    print(f"接口地址: POST http://your-server:{PORT}/forward")
    print(f"\n等待 iOS 快捷指令请求...\n")

    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.server_close()


if __name__ == "__main__":
    main()
