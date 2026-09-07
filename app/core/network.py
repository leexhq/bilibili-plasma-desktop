"""Passive Response Interceptor & Network Pipeline
Enforces the Zero-Extra-Network-Request Principle: all data archiving occurs
passively inside the response interception layer with zero duplicate queries.
"""

from __future__ import annotations
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
import requests

from app.core.config import config_instance
from app.core.storage import archive_writer, archive_db
from app.core.account_manager import account_manager, Account
from app.core.state_machine import state_machine
from app.models.video import VideoInfo, RecommendationItem
from app.models.comment import CommentNode, build_comment_tree

class PassiveResponseInterceptor:
    """
    Passive interception pipeline. Inspects every incoming network response
    and passes data to the async SQLite archive writer without any duplicate network traffic.
    """

    def __init__(self):
        self.stream_recording_enabled = config_instance.get("archiving.stream_recording.enabled", True)
        self.metadata_archiving_enabled = config_instance.get("archiving.metadata_archiving.enabled", True)
        self.comments_archiving_enabled = config_instance.get("archiving.comments_archiving.enabled", True)
        self.active_recording_handles: Dict[str, Any] = {}

    def intercept_video_view(self, resp_data: Dict[str, Any], caller_account_id: str) -> VideoInfo:
        """Passively extracts and archives video metadata and timeseries logs."""
        data_body = resp_data.get("data", resp_data)
        video_info = VideoInfo.from_dict(data_body)

        if self.metadata_archiving_enabled:
            archive_writer.enqueue("video", video_info.to_dict())

        return video_info

    def intercept_comments(self, resp_data: Dict[str, Any], oid: int) -> List[CommentNode]:
        """Passively extracts and archives comments stream into SQLite."""
        data_body = resp_data.get("data", resp_data)
        raw_replies = data_body.get("replies", [])
        if raw_replies is None:
            raw_replies = []

        # Convert to robust comment tree
        tree = build_comment_tree(raw_replies, default_oid=oid)

        if self.comments_archiving_enabled:
            def collect_all_nodes(nodes: List[CommentNode]) -> List[Dict[str, Any]]:
                flat = []
                for n in nodes:
                    flat.append({
                        "rpid": n.rpid,
                        "oid": n.oid,
                        "type": n.type,
                        "mid": n.mid,
                        "member_name": n.member_name,
                        "root_id": n.root_id,
                        "parent_id": n.parent_id,
                        "ctime": n.ctime,
                        "content": n.content,
                        "like_count": n.like_count,
                        "location": n.location,
                        "is_orphan": n.is_orphan,
                        "raw_json": n.raw_json
                    })
                    if n.children:
                        flat.extend(collect_all_nodes(n.children))
                return flat

            all_extracted = collect_all_nodes(tree)
            archive_writer.enqueue("comments_batch", {"comments": all_extracted})

        return tree

    def intercept_follow_action(self, account_id: str, up_id: int, up_name: str, is_following: bool) -> None:
        """Passively intercepts follow mutations and notifies listeners."""
        payload = {
            "account_id": account_id,
            "up_id": up_id,
            "up_name": up_name,
            "is_following": is_following,
            "follow_time": int(time.time())
        }
        archive_writer.enqueue("follow", payload)
        state_machine.trigger_follow_event(up_id, up_name, is_following, identity_id=account_id)

    def intercept_stream_chunk(self, context: Dict[str, Any], chunk_data: bytes) -> None:
        """
        Passively writes captured video stream chunks to local disk
        according to configured template path.
        """
        if not self.stream_recording_enabled:
            return

        bvid = context.get("bvid", "unknown_bvid")
        dir_tpl = config_instance.get("archiving.stream_recording.dir_template", "data/recordings/{upid}_{bvid}")
        file_tpl = config_instance.get("archiving.stream_recording.filename_template", "{bvid}_{cid}_{title}_{timestamp}.flv")
        
        target_dir = config_instance.format_path(dir_tpl, context)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / config_instance.format_path(file_tpl, context).name

        try:
            with open(target_file, "ab") as f:
                f.write(chunk_data)
        except Exception as e:
            print(f"[StreamArchiver] Failed to write chunk to {target_file}: {e}")

import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import threading

class StreamProxyHandler(BaseHTTPRequestHandler):
    """
    Local HTTP Proxy handler that:
    1. Forwards requests to B站 CDN with required Referer/User-Agent headers (bypassing 403 Forbidden).
    2. Supports HTTP 206 Partial Content Range requests for instant scrubbing.
    3. Passively intercepts video chunks and saves to local disk (Zero-Extra-Network-Request Principle).
    """

    def log_message(self, format, *args):
        pass  # Suppress terminal log noise

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/stream":
            query = urllib.parse.parse_qs(parsed.query)
            key = query.get("key", [""])[0]
            stream_info = local_stream_proxy.get_stream_info(key)
            if not stream_info:
                self.send_error(404, "Stream key not found")
                return

            cdn_url = stream_info.get("url", "")
            context = stream_info.get("context", {})
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com"
            }
            if stream_info.get("cookie"):
                headers["Cookie"] = stream_info["cookie"]
            if "Range" in self.headers:
                headers["Range"] = self.headers["Range"]

            try:
                resp = requests.get(cdn_url, headers=headers, stream=True, timeout=10)
                self.send_response(resp.status_code)
                for h in ["Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"]:
                    if h in resp.headers:
                        self.send_header(h, resp.headers[h])
                self.end_headers()

                is_range_start_zero = ("Range" not in self.headers) or ("bytes=0-" in self.headers.get("Range", ""))

                for chunk in resp.iter_content(chunk_size=65536):
                    if chunk:
                        try:
                            self.wfile.write(chunk)
                        except (BrokenPipeError, ConnectionResetError):
                            break
                        # Passive Archiving: record stream chunk during playback
                        if is_range_start_zero:
                            bili_client.interceptor.intercept_stream_chunk(context, chunk)
            except Exception as e:
                pass
            return

        self.send_error(404)

class LocalStreamProxy:
    """Singleton local reverse proxy serving QMediaPlayer with injected headers."""

    def __init__(self):
        self.streams: Dict[str, Dict[str, Any]] = {}
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), StreamProxyHandler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="LocalStreamProxyThread")
        self.thread.start()

    def register_stream(self, key: str, cdn_url: str, context: Dict[str, Any], cookie: str = "") -> str:
        self.streams[key] = {
            "url": cdn_url,
            "context": context,
            "cookie": cookie
        }
        return f"http://127.0.0.1:{self.port}/stream?key={urllib.parse.quote(key)}"

    def get_stream_info(self, key: str) -> Optional[Dict[str, Any]]:
        return self.streams.get(key)

local_stream_proxy = LocalStreamProxy()

class BiliApiClient:
    """
    High-level API client with multi-identity injection, passive interception,
    and graceful offline disaster recovery fallback.
    """

    def __init__(self, interceptor: Optional[PassiveResponseInterceptor] = None):
        self.interceptor = interceptor or PassiveResponseInterceptor()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 KDE Plasma/Breeze",
            "Referer": "https://www.bilibili.com"
        })

    def _get_headers_for_account(self, account_id: Optional[str] = None) -> Dict[str, str]:
        eff_id = account_id or state_machine.current_identity_id
        acc = account_manager.get_account(eff_id) or account_manager.get_active_account()
        headers = {}
        cookie = acc.get_cookie_header()
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def fetch_video_detail(self, bvid: str, account_id: Optional[str] = None) -> VideoInfo:
        """Fetches video details. Passive interceptor captures response to SQLite."""
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
        headers = self._get_headers_for_account(account_id)

        try:
            resp = self.session.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    return self.interceptor.intercept_video_view(data, account_id or state_machine.current_identity_id)
        except Exception as e:
            print(f"[BiliApiClient] Network error fetching video {bvid}: {e}. Falling back to archive/offline.")

        # Offline Fallback: load from SQLite archive if available
        archived_list = archive_db.get_archived_videos(limit=10)
        for row in archived_list:
            if row["bvid"] == bvid:
                raw = json.loads(row["raw_json"]) if row.get("raw_json") else {}
                raw["bvid"] = row["bvid"]
                raw["title"] = row["title"]
                raw["desc"] = row["desc"]
                raw["location"] = row["ip_location"]
                return VideoInfo.from_dict(raw)

        # High-fidelity mock fallback for reliable offline / disaster recovery
        from app.mock_data import get_mock_video_detail
        mock_data = get_mock_video_detail(bvid)
        return self.interceptor.intercept_video_view(mock_data, account_id or state_machine.current_identity_id)

    def fetch_play_stream_url(self, bvid: str, cid: int, qn: int = 32, account_id: Optional[str] = None) -> Optional[str]:
        """
        Fetches the playable progressive MP4/FLV stream URL and registers it with
        the LocalStreamProxy. The proxy injects Referer/User-Agent and intercepts chunks
        for passive stream recording to disk.
        """
        eff_id = account_id or state_machine.current_identity_id
        acc = account_manager.get_account(eff_id) or account_manager.get_active_account()
        cookie = acc.get_cookie_header()
        
        url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn={qn}&fnval=0&fnver=0&fourk=0"
        headers = self._get_headers_for_account(eff_id)
        
        try:
            resp = self.session.get(url, headers=headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    durl = data.get("data", {}).get("durl", [])
                    if durl and "url" in durl[0]:
                        cdn_url = durl[0]["url"]
                        key = f"{bvid}_{cid}_{qn}"
                        context = {
                            "bvid": bvid,
                            "cid": cid,
                            "upid": 0,
                            "title": "stream"
                        }
                        proxy_url = local_stream_proxy.register_stream(key, cdn_url, context, cookie=cookie)
                        return proxy_url
        except Exception as e:
            print(f"[BiliApiClient] Failed to fetch playurl for {bvid}: {e}")

        return None

    def fetch_comments(self, oid: int, account_id: Optional[str] = None) -> List[CommentNode]:
        """Fetches comments for video oid. Passively intercepted and persisted."""
        url = f"https://api.bilibili.com/x/v2/reply?type=1&oid={oid}&sort=1"
        headers = self._get_headers_for_account(account_id)

        try:
            resp = self.session.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    return self.interceptor.intercept_comments(data, oid=oid)
        except Exception as e:
            print(f"[BiliApiClient] Network error fetching comments: {e}. Falling back to archive/mock.")

        # Check SQLite archive
        archived = archive_db.get_archived_comments_for_oid(oid)
        if archived:
            raw_list = [json.loads(r["raw_json"]) if r.get("raw_json") else r for r in archived]
            return build_comment_tree(raw_list, default_oid=oid)

        from app.mock_data import get_mock_comments
        mock_resp = get_mock_comments(oid)
        return self.interceptor.intercept_comments(mock_resp, oid=oid)

    def fetch_recommendations(self, bvid: str) -> List[RecommendationItem]:
        """Fetches 40 recommendation items."""
        url = f"https://api.bilibili.com/x/web-interface/archive/related?bvid={bvid}"
        try:
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    items = data.get("data", [])
                    return [RecommendationItem.from_dict(item) for item in items[:40]]
        except Exception as e:
            print(f"[BiliApiClient] Network error fetching recommendations: {e}")

        from app.mock_data import get_mock_recommendations
        return get_mock_recommendations(bvid)

    def perform_follow(self, up_id: int, up_name: str, is_following: bool, account_id: Optional[str] = None) -> bool:
        """Executes follow/unfollow action with identity isolation and offline queuing."""
        eff_id = account_id or state_machine.current_identity_id
        acc = account_manager.get_account(eff_id) or account_manager.get_active_account()

        # Offline / disaster recovery mode support
        if not acc.sessdata or acc.sessdata.startswith("mock_"):
            # Local simulation & offline persistence
            self.interceptor.intercept_follow_action(eff_id, up_id, up_name, is_following)
            archive_db.add_offline_action("follow", eff_id, {
                "up_id": up_id,
                "up_name": up_name,
                "is_following": is_following
            })
            return True

        url = "https://api.bilibili.com/x/relation/modify"
        act = 1 if is_following else 2
        data = {
            "fid": up_id,
            "act": act,
            "re_src": 11,
            "csrf": acc.bili_jct
        }
        headers = self._get_headers_for_account(eff_id)
        try:
            resp = self.session.post(url, data=data, headers=headers, timeout=5)
            if resp.status_code == 200 and resp.json().get("code") == 0:
                self.interceptor.intercept_follow_action(eff_id, up_id, up_name, is_following)
                return True
        except Exception as e:
            print(f"[BiliApiClient] Follow request failed ({e}), queued into offline disaster storage.")
            archive_db.add_offline_action("follow", eff_id, {
                "up_id": up_id,
                "up_name": up_name,
                "is_following": is_following
            })
            self.interceptor.intercept_follow_action(eff_id, up_id, up_name, is_following)
            return True
        return False

# Global API client instance
bili_client = BiliApiClient()
