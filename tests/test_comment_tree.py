"""Unit Tests for Comment Tree Algorithm and Orphan Fallback Handling
"""

import unittest
from app.models.comment import CommentNode, build_comment_tree
from app.mock_data import get_mock_comments

class TestCommentTree(unittest.TestCase):

    def test_normal_tree_hierarchy(self):
        raw_comments = [
            {"rpid": 1, "root": 0, "parent": 0, "message": "Root comment 1", "like": 10},
            {"rpid": 2, "root": 1, "parent": 1, "message": "Reply to root 1", "like": 5},
            {"rpid": 3, "root": 1, "parent": 2, "message": "Nested reply to reply 2", "like": 2},
        ]
        tree = build_comment_tree(raw_comments, default_oid=123)
        self.assertEqual(len(tree), 1)
        root = tree[0]
        self.assertEqual(root.rpid, 1)
        self.assertEqual(len(root.children), 1)
        child = root.children[0]
        self.assertEqual(child.rpid, 2)
        self.assertEqual(len(child.children), 1)
        grandchild = child.children[0]
        self.assertEqual(grandchild.rpid, 3)

    def test_orphan_node_fallback(self):
        """
        When parent_id refers to an rpid not in the list (deleted or missing),
        the tree builder must gracefully create a fallback placeholder or attach without throwing!
        """
        raw_comments = [
            {"rpid": 10, "root": 0, "parent": 0, "message": "Normal comment", "like": 10},
            # Orphan: parent 999 does not exist!
            {"rpid": 20, "root": 999, "parent": 999, "message": "Orphan reply to missing 999", "like": 3},
            # Orphan's child
            {"rpid": 21, "root": 999, "parent": 20, "message": "Reply to orphan 20", "like": 1}
        ]
        tree = build_comment_tree(raw_comments, default_oid=123)
        # Tree should not crash, should contain normal root and placeholder root for 999
        self.assertTrue(len(tree) >= 2)
        
        # Find placeholder
        placeholder = next((n for n in tree if n.is_fallback_placeholder), None)
        self.assertIsNotNone(placeholder)
        self.assertEqual(placeholder.rpid, 999)
        self.assertIn("失效", placeholder.fallback_note)
        
        # Verify orphan is attached under placeholder
        self.assertEqual(len(placeholder.children), 1)
        orphan = placeholder.children[0]
        self.assertEqual(orphan.rpid, 20)
        self.assertTrue(orphan.is_orphan)
        self.assertEqual(len(orphan.children), 1)
        self.assertEqual(orphan.children[0].rpid, 21)

    def test_mock_comments_integration(self):
        mock_data = get_mock_comments(88776655)["data"]["replies"]
        tree = build_comment_tree(mock_data, default_oid=88776655)
        self.assertTrue(len(tree) > 0)
        # Check that orphan 3001 is safely captured
        all_rpids = []
        def collect_rpids(node: CommentNode):
            all_rpids.append(node.rpid)
            for ch in node.children:
                collect_rpids(ch)
        for r in tree:
            collect_rpids(r)
        self.assertIn(3001, all_rpids)
        self.assertIn(3002, all_rpids)

if __name__ == "__main__":
    unittest.main()
