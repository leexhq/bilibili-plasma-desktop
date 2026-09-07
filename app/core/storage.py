"""SQLite Passive Archive Database Engine & Async Writer
Provides high-performance, non-blocking asynchronous persistence for
passively intercepted videos, comments, and dynamic timeseries logs.
"""

from __future__ import annotations
import sqlite3
import json
import time
import queue
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import config_instance

class SQLiteArchiveDatabase:
    """Manages SQLite schema and synchronous database operations."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = config_instance.get("archiving.db_path", "data/archive.db")
        p = Path(db_path)
        if not p.is_absolute():
            from app.core.config import get_base_dir
            p = get_base_dir() / p
        self.db_path = p
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Video Metadata Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                bvid TEXT PRIMARY KEY,
                aid INTEGER,
                cid INTEGER,
                title TEXT,
                desc TEXT,
                up_id INTEGER,
                up_name TEXT,
                duration INTEGER,
                pubdate INTEGER,
                ip_location TEXT,
                updated_at INTEGER,
                raw_json TEXT
            );
            """)

            # 2. Comment Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                rpid INTEGER PRIMARY KEY,
                oid INTEGER,
                type INTEGER,
                mid INTEGER,
                member_name TEXT,
                root_id INTEGER,
                parent_id INTEGER,
                ctime INTEGER,
                content TEXT,
                like_count INTEGER,
                ip_location TEXT,
                is_orphan INTEGER DEFAULT 0,
                archived_at INTEGER,
                raw_json TEXT
            );
            """)

            # 3. Dynamic Timeseries Log Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS timeseries_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT, -- 'video' or 'comment'
                target_id TEXT,   -- bvid/aid or rpid
                timestamp INTEGER,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                coin_count INTEGER DEFAULT 0,
                favorite_count INTEGER DEFAULT 0,
                reply_count INTEGER DEFAULT 0,
                share_count INTEGER DEFAULT 0
            );
            """)

            # 4. Multi-Identity Follow Relations Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_follows (
                account_id TEXT,
                up_id INTEGER,
                up_name TEXT,
                follow_time INTEGER,
                is_following INTEGER DEFAULT 1,
                PRIMARY KEY (account_id, up_id)
            );
            """)

            # 5. Offline Disaster Recovery Action Queue
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                account_id TEXT,
                payload TEXT,
                created_at INTEGER,
                status TEXT DEFAULT 'pending'
            );
            """)

            # Create indices for fast lookup
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_oid ON comments(oid);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_root ON comments(root_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ts_target ON timeseries_log(target_id, timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_follows_up ON user_follows(up_id);")
            conn.commit()

    def upsert_video(self, video_data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            bvid = video_data.get("bvid", "")
            aid = video_data.get("aid", 0)
            cid = video_data.get("cid", 0)
            title = video_data.get("title", "")
            desc = video_data.get("desc", "")
            up_id = video_data.get("up_id", 0)
            up_name = video_data.get("up_name", "")
            duration = video_data.get("duration", 0)
            pubdate = video_data.get("pubdate", 0)
            ip_loc = video_data.get("ip_location", "")
            raw_json = json.dumps(video_data.get("raw_data", {}), ensure_ascii=False)
            now = int(time.time())

            cursor.execute("""
            INSERT INTO videos (bvid, aid, cid, title, desc, up_id, up_name, duration, pubdate, ip_location, updated_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(bvid) DO UPDATE SET
                title=excluded.title,
                desc=excluded.desc,
                up_name=excluded.up_name,
                ip_location=excluded.ip_location,
                updated_at=excluded.updated_at,
                raw_json=excluded.raw_json;
            """, (bvid, aid, cid, title, desc, up_id, up_name, duration, pubdate, ip_loc, now, raw_json))

            # Record timeseries log for video
            cursor.execute("""
            INSERT INTO timeseries_log (target_type, target_id, timestamp, view_count, like_count, coin_count, favorite_count, reply_count, share_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                "video",
                bvid,
                now,
                video_data.get("view", 0),
                video_data.get("like", 0),
                video_data.get("coin", 0),
                video_data.get("favorite", 0),
                video_data.get("reply", 0),
                video_data.get("share", 0)
            ))
            conn.commit()

    def upsert_comment(self, comment_data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            rpid = comment_data.get("rpid", 0)
            oid = comment_data.get("oid", 0)
            c_type = comment_data.get("type", 1)
            mid = comment_data.get("mid", 0)
            name = comment_data.get("member_name", "")
            root_id = comment_data.get("root_id", 0)
            parent_id = comment_data.get("parent_id", 0)
            ctime = comment_data.get("ctime", 0)
            content = comment_data.get("content", "")
            like_count = comment_data.get("like_count", 0)
            ip_loc = comment_data.get("location", "")
            is_orphan = 1 if comment_data.get("is_orphan", False) else 0
            now = int(time.time())
            raw_json = json.dumps(comment_data.get("raw_json", {}), ensure_ascii=False)

            cursor.execute("""
            INSERT INTO comments (rpid, oid, type, mid, member_name, root_id, parent_id, ctime, content, like_count, ip_location, is_orphan, archived_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rpid) DO UPDATE SET
                like_count=excluded.like_count,
                content=excluded.content,
                is_orphan=excluded.is_orphan,
                raw_json=excluded.raw_json;
            """, (rpid, oid, c_type, mid, name, root_id, parent_id, ctime, content, like_count, ip_loc, is_orphan, now, raw_json))

            # Record comment timeseries log
            cursor.execute("""
            INSERT INTO timeseries_log (target_type, target_id, timestamp, like_count)
            VALUES (?, ?, ?, ?);
            """, ("comment", str(rpid), now, like_count))
            conn.commit()

    def record_follow_status(self, account_id: str, up_id: int, up_name: str, is_following: bool, follow_time: Optional[int] = None) -> None:
        if follow_time is None:
            follow_time = int(time.time())
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO user_follows (account_id, up_id, up_name, follow_time, is_following)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(account_id, up_id) DO UPDATE SET
                is_following=excluded.is_following,
                follow_time=excluded.follow_time,
                up_name=excluded.up_name;
            """, (account_id, up_id, up_name, follow_time, 1 if is_following else 0))
            conn.commit()

    def get_up_follows_matrix(self, up_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT account_id, up_id, up_name, follow_time, is_following
            FROM user_follows
            WHERE up_id = ?;
            """, (up_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_archived_videos(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos ORDER BY updated_at DESC LIMIT ?;", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_archived_comments_for_oid(self, oid: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM comments WHERE oid = ? ORDER BY ctime DESC;", (oid,))
            return [dict(row) for row in cursor.fetchall()]

    def get_timeseries(self, target_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM timeseries_log WHERE target_id = ? ORDER BY timestamp ASC;", (target_id,))
            return [dict(row) for row in cursor.fetchall()]

    def add_offline_action(self, action_type: str, account_id: str, payload: Dict[str, Any]) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO offline_queue (action_type, account_id, payload, created_at, status)
            VALUES (?, ?, ?, ?, 'pending');
            """, (action_type, account_id, json.dumps(payload, ensure_ascii=False), int(time.time())))
            conn.commit()
            return cursor.lastrowid

    def get_pending_offline_actions(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM offline_queue WHERE status = 'pending' ORDER BY created_at ASC;")
            results = []
            for row in cursor.fetchall():
                item = dict(row)
                item["payload"] = json.loads(item["payload"])
                results.append(item)
            return results

    def mark_offline_action_done(self, action_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE offline_queue SET status = 'completed' WHERE id = ?;", (action_id,))
            conn.commit()


class AsyncArchiveWriter:
    """
    Background worker pipeline ensuring zero extra network requests and 
    zero main-thread blocking when archiving intercepted payloads.
    """

    def __init__(self, db: SQLiteArchiveDatabase):
        self.db = db
        self.queue: queue.Queue = queue.Queue()
        self._running = True
        self._worker_thread = threading.Thread(target=self._run_loop, daemon=True, name="ArchiveWriterWorker")
        self._worker_thread.start()

    def enqueue(self, task_type: str, payload: Dict[str, Any]) -> None:
        self.queue.put((task_type, payload))

    def _run_loop(self) -> None:
        while self._running:
            try:
                task_type, payload = self.queue.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                if task_type == "video":
                    self.db.upsert_video(payload)
                elif task_type == "comment":
                    self.db.upsert_comment(payload)
                elif task_type == "comments_batch":
                    for c in payload.get("comments", []):
                        self.db.upsert_comment(c)
                elif task_type == "follow":
                    self.db.record_follow_status(
                        account_id=payload["account_id"],
                        up_id=payload["up_id"],
                        up_name=payload.get("up_name", ""),
                        is_following=payload.get("is_following", True),
                        follow_time=payload.get("follow_time")
                    )
            except Exception as e:
                print(f"[AsyncArchiveWriter] Error writing to SQLite: {e}")
            finally:
                self.queue.task_done()

    def stop(self) -> None:
        self._running = False
        self._worker_thread.join(timeout=2.0)

# Global storage instance
archive_db = SQLiteArchiveDatabase()
archive_writer = AsyncArchiveWriter(archive_db)
