"""
X API 监控模块 (可选 - 需要 X Developer 账号)

如果你有 X API Bearer Token，这个模块比 RSS 方式更可靠。
免费 tier 每月可读取 10,000 条推文。

使用方法:
  在 config.py 中设置 X_BEARER_TOKEN
  在 main.py 中将 XMonitor 替换为 XAPIMonitor
"""

import json
import time
from datetime import datetime, timedelta, timezone

import requests

from config import X_ACCOUNTS, KEYWORDS, DB_FILE
from x_monitor import XMonitor


# 在 config.py 中添加这个配置
X_BEARER_TOKEN = ""  # 你的 X API Bearer Token


class XAPIMonitor(XMonitor):
    """使用 X API v2 获取推文 (更可靠但需要 API 访问)"""

    def __init__(self):
        super().__init__()
        self.bearer_token = X_BEARER_TOKEN
        self.base_url = "https://api.twitter.com/2"
        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}",
        }

    def get_new_video_tweets(self) -> list:
        if not self.bearer_token:
            print("  X_BEARER_TOKEN 未设置，使用 RSS 模式")
            return super().get_new_video_tweets()

        new_videos = []
        for account in X_ACCOUNTS:
            user_id = self._get_user_id(account)
            if not user_id:
                continue

            tweets = self._get_user_tweets(user_id, account)
            for tweet in tweets:
                tweet_id = tweet.get("id")
                if tweet_id and not self.is_sent(tweet_id):
                    if self._tweet_has_video(tweet):
                        if self._matches_keywords(tweet):
                            new_videos.append(tweet)
        return new_videos

    def _get_user_id(self, username: str) -> str | None:
        url = f"{self.base_url}/users/by/username/{username}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()["data"]["id"]
            elif resp.status_code == 429:
                print(f"  API 限速，等待...")
                time.sleep(60)
        except requests.RequestException:
            pass
        return None

    def _get_user_tweets(self, user_id: str, account: str) -> list:
        # 只获取最近 1 小时的推文
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        url = f"{self.base_url}/users/{user_id}/tweets"
        params = {
            "max_results": 10,
            "start_time": since,
            "tweet.fields": "attachments,created_at,text",
            "expansions": "attachments.media_keys",
            "media.fields": "type,url,duration_ms",
        }

        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                tweets_data = data.get("data", [])
                media_map = {}

                # 构建媒体索引
                includes = data.get("includes", {})
                for media in includes.get("media", []):
                    media_map[media["media_key"]] = media

                # 组装推文信息
                tweets = []
                for t in tweets_data:
                    tweet = {
                        "id": t["id"],
                        "url": f"https://x.com/{account}/status/{t['id']}",
                        "text": t.get("text", ""),
                        "account": account,
                        "media": [],
                    }
                    # 附加媒体信息
                    attachments = t.get("attachments", {})
                    for key in attachments.get("media_keys", []):
                        if key in media_map:
                            tweet["media"].append(media_map[key])
                    tweets.append(tweet)

                return tweets
            elif resp.status_code == 429:
                print(f"  API 限速")
                time.sleep(60)
        except requests.RequestException:
            pass
        return []

    def _tweet_has_video(self, tweet: dict) -> bool:
        """通过 API 返回的媒体类型判断"""
        for media in tweet.get("media", []):
            if media.get("type") in ("video", "animated_gif"):
                return True
        # 回退: 用 yt-dlp 检查
        return self._verify_video_with_ytdlp(tweet["url"])
