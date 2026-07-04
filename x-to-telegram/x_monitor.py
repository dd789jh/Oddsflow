"""
X (Twitter) 视频监控模块
使用 yt-dlp 提取视频，支持多种数据源获取推文列表
"""

import json
import re
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from config import X_ACCOUNTS, KEYWORDS, VIDEO_QUALITY, MAX_VIDEO_SIZE_MB, DB_FILE


class XMonitor:
    def __init__(self):
        self.sent_posts = self._load_sent_posts()

    def _load_sent_posts(self):
        db_path = Path(DB_FILE)
        if db_path.exists():
            return json.loads(db_path.read_text())
        return []

    def _save_sent_posts(self):
        Path(DB_FILE).write_text(json.dumps(self.sent_posts, indent=2))

    def mark_as_sent(self, tweet_id: str):
        if tweet_id not in self.sent_posts:
            self.sent_posts.append(tweet_id)
            # 只保留最近 1000 条记录
            if len(self.sent_posts) > 1000:
                self.sent_posts = self.sent_posts[-1000:]
            self._save_sent_posts()

    def is_sent(self, tweet_id: str) -> bool:
        return tweet_id in self.sent_posts

    def get_new_video_tweets(self) -> list:
        """
        获取账户新推文中包含视频的内容。
        使用 RSS 桥接或 Nitter 实例获取。
        """
        new_videos = []
        for account in X_ACCOUNTS:
            tweets = self._fetch_tweets_rss(account)
            for tweet in tweets:
                tweet_id = tweet.get("id")
                if tweet_id and not self.is_sent(tweet_id):
                    if self._has_video(tweet):
                        if self._matches_keywords(tweet):
                            new_videos.append(tweet)
        return new_videos

    def _fetch_tweets_rss(self, account: str) -> list:
        """
        通过多个源尝试获取推文:
        1. RSSHub (自建或公共实例)
        2. Nitter RSS
        3. 直接解析 (备选)
        """
        tweets = []

        # 方法 1: RSSHub
        rsshub_urls = [
            f"https://rsshub.app/twitter/user/{account}",
            f"https://rsshub.rssforever.com/twitter/user/{account}",
        ]
        for url in rsshub_urls:
            try:
                resp = requests.get(url, timeout=15, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; XToTelegram/1.0)"
                })
                if resp.status_code == 200:
                    tweets = self._parse_rss(resp.text, account)
                    if tweets:
                        return tweets
            except requests.RequestException:
                continue

        # 方法 2: Nitter 实例
        nitter_instances = [
            f"https://nitter.privacydev.net/{account}/rss",
            f"https://nitter.poast.org/{account}/rss",
        ]
        for url in nitter_instances:
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    tweets = self._parse_nitter_rss(resp.text, account)
                    if tweets:
                        return tweets
            except requests.RequestException:
                continue

        return tweets

    def _parse_rss(self, xml_text: str, account: str) -> list:
        """简单解析 RSS XML (不引入 xml 库的大依赖)"""
        tweets = []
        items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
        for item in items[:20]:
            link_match = re.search(r'<link>(.*?)</link>', item)
            title_match = re.search(r'<title>(.*?)</title>', item)
            desc_match = re.search(r'<description>(.*?)</description>', item, re.DOTALL)

            if link_match:
                link = link_match.group(1).strip()
                tweet_id = self._extract_tweet_id(link)
                if tweet_id:
                    tweets.append({
                        "id": tweet_id,
                        "url": link,
                        "text": title_match.group(1) if title_match else "",
                        "description": desc_match.group(1) if desc_match else "",
                        "account": account,
                    })
        return tweets

    def _parse_nitter_rss(self, xml_text: str, account: str) -> list:
        """解析 Nitter RSS"""
        tweets = []
        items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
        for item in items[:20]:
            link_match = re.search(r'<link>(.*?)</link>', item)
            title_match = re.search(r'<title>(.*?)</title>', item)
            desc_match = re.search(r'<description>(.*?)</description>', item, re.DOTALL)

            if link_match:
                link = link_match.group(1).strip()
                # Nitter 链接转换为 X 链接
                link = link.replace("nitter.privacydev.net", "x.com")
                link = link.replace("nitter.poast.org", "x.com")
                tweet_id = self._extract_tweet_id(link)
                if tweet_id:
                    tweets.append({
                        "id": tweet_id,
                        "url": f"https://x.com/{account}/status/{tweet_id}",
                        "text": title_match.group(1) if title_match else "",
                        "description": desc_match.group(1) if desc_match else "",
                        "account": account,
                    })
        return tweets

    def _extract_tweet_id(self, url: str) -> str:
        """从 URL 中提取推文 ID"""
        match = re.search(r'/status/(\d+)', url)
        return match.group(1) if match else ""

    def _has_video(self, tweet: dict) -> bool:
        """判断推文是否包含视频"""
        desc = tweet.get("description", "").lower()
        # RSS 中视频的常见标记
        video_indicators = ["video", "mp4", "pic.twitter.com", "video_thumb"]
        if any(indicator in desc for indicator in video_indicators):
            return True
        # 通过 yt-dlp 验证是否有视频
        return self._verify_video_with_ytdlp(tweet["url"])

    def _verify_video_with_ytdlp(self, url: str) -> bool:
        """用 yt-dlp 检查 URL 是否包含可下载的视频"""
        try:
            result = subprocess.run(
                ["yt-dlp", "--dump-json", "--no-download", url],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return info.get("duration", 0) > 0
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass
        return False

    def _matches_keywords(self, tweet: dict) -> bool:
        """检查推文是否匹配关键词 (为空则全部匹配)"""
        if not KEYWORDS:
            return True
        text = f"{tweet.get('text', '')} {tweet.get('description', '')}".lower()
        return any(kw.lower() in text for kw in KEYWORDS)

    def download_video(self, tweet_url: str) -> str | None:
        """下载视频，返回本地文件路径"""
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
                    tweet_url,
                ],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                # 找到下载的文件
                files = list(Path(tmp_dir).glob("*.*"))
                if files:
                    return str(files[0])
        except subprocess.TimeoutExpired:
            pass

        return None
