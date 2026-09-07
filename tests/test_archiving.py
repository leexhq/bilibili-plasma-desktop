"""Unit Tests for SQLite Passive Interception, Async Archiving, and Dynamic Timeseries Logs
"""

import unittest
import os
import time
from app.core.storage import SQLiteArchiveDatabase, AsyncArchiveWriter
from app.core.network import PassiveResponseInterceptor
from app.mock_data import get_mock_video_detail, get_mock_comments

class TestPassiveArchiving(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "data/test_archive.db"
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass
        self.db = SQLiteArchiveDatabase(self.test_db_path)
        self.writer = AsyncArchiveWriter(self.db)
        self.interceptor = PassiveResponseInterceptor()

    def tearDown(self):
        self.writer.stop()
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_passive_video_and_timeseries_archiving(self):
        raw_video_resp = get_mock_video_detail("BV1test123")
        video_info = self.interceptor.intercept_video_view(raw_video_resp, caller_account_id="acc_main")
        
        # Directly write to test db
        self.db.upsert_video(video_info.to_dict())

        # Verify saved in SQLite
        saved_videos = self.db.get_archived_videos(limit=10)
        self.assertEqual(len(saved_videos), 1)
        self.assertEqual(saved_videos[0]["bvid"], "BV1test123")
        self.assertEqual(saved_videos[0]["title"], video_info.title)

        # Verify timeseries log entry created
        ts_entries = self.db.get_timeseries("BV1test123")
        self.assertEqual(len(ts_entries), 1)
        self.assertEqual(ts_entries[0]["target_type"], "video")
        self.assertEqual(ts_entries[0]["like_count"], video_info.like)

    def test_passive_comments_archiving(self):
        mock_comments_resp = get_mock_comments(88776655)
        tree = self.interceptor.intercept_comments(mock_comments_resp, oid=88776655)
        self.assertTrue(len(tree) > 0)

        # Insert batch into SQLite
        for node in tree:
            self.db.upsert_comment({
                "rpid": node.rpid,
                "oid": node.oid,
                "type": node.type,
                "mid": node.mid,
                "member_name": node.member_name,
                "root_id": node.root_id,
                "parent_id": node.parent_id,
                "ctime": node.ctime,
                "content": node.content,
                "like_count": node.like_count,
                "location": node.location,
                "is_orphan": node.is_orphan
            })

        archived = self.db.get_archived_comments_for_oid(88776655)
        self.assertTrue(len(archived) >= len(tree))

    def test_multi_identity_follow_matrix(self):
        self.db.record_follow_status("acc_main", 998877, "KDE_Plasma_Lab", True, follow_time=1700000000)
        self.db.record_follow_status("acc_sub", 998877, "KDE_Plasma_Lab", False, follow_time=1700000100)

        matrix = self.db.get_up_follows_matrix(998877)
        self.assertEqual(len(matrix), 2)
        acc_dict = {row["account_id"]: row for row in matrix}
        self.assertEqual(acc_dict["acc_main"]["is_following"], 1)
        self.assertEqual(acc_dict["acc_main"]["follow_time"], 1700000000)
        self.assertEqual(acc_dict["acc_sub"]["is_following"], 0)

if __name__ == "__main__":
    unittest.main()
