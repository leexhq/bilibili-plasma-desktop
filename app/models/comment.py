"""Comment Model and Robust Tree Reconstruction Algorithm
Handles nested comment hierarchies, orphan nodes, and deleted parent fallback.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class CommentNode:
    rpid: int
    oid: int = 0
    type: int = 1
    mid: int = 0
    member_name: str = ""
    member_avatar: str = ""
    content: str = ""
    ctime: int = 0
    like_count: int = 0
    root_id: int = 0
    parent_id: int = 0
    location: str = "IP属地: 未知"
    children: List[CommentNode] = field(default_factory=list)
    is_orphan: bool = False
    is_fallback_placeholder: bool = False
    fallback_note: str = ""
    raw_json: Dict[str, Any] = field(default_factory=dict)

    @property
    def formatted_time(self) -> str:
        if self.ctime <= 0:
            return "未知时间"
        try:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.ctime))
        except Exception:
            return str(self.ctime)

    def add_child(self, child: CommentNode) -> None:
        self.children.append(child)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], default_oid: int = 0) -> CommentNode:
        member = data.get("member", {})
        content_info = data.get("content", {})
        message = content_info.get("message", "") if isinstance(content_info, dict) else str(data.get("message", ""))
        
        # IP location parsing
        loc = "IP属地: 未知"
        if "location" in data:
            loc = data["location"]
        elif "reply_control" in data and isinstance(data["reply_control"], dict):
            rc_loc = data["reply_control"].get("location")
            if rc_loc:
                loc = rc_loc if "IP属地" in rc_loc else f"IP属地: {rc_loc}"

        return cls(
            rpid=int(data.get("rpid", 0)),
            oid=int(data.get("oid", default_oid)),
            type=int(data.get("type", 1)),
            mid=int(member.get("mid", data.get("mid", 0))),
            member_name=member.get("uname", data.get("uname", "未知用户")),
            member_avatar=member.get("avatar", data.get("avatar", "")),
            content=message,
            ctime=int(data.get("ctime", data.get("pubtime", 0))),
            like_count=int(data.get("like", 0)),
            root_id=int(data.get("root", 0)),
            parent_id=int(data.get("parent", 0)),
            location=loc,
            raw_json=data
        )

def build_comment_tree(raw_comments: List[Dict[str, Any]], default_oid: int = 0) -> List[CommentNode]:
    """
    Reconstructs flat or semi-nested comments into a full hierarchical tree.
    Robustness / Fallback Guarantee:
    - If a parent node (parent_id) is deleted or missing from the payload, 
      creates a synthetic placeholder parent or safely attaches as orphan 
      with '原评论已失效' badge, preventing any UI crashes or rendering breaks.
    """
    nodes: Dict[int, CommentNode] = {}
    parsed_nodes: List[CommentNode] = []
    
    # Pass 1: Parse all nodes and expand any inline replies from Bilibili API
    def extract_node(item: Dict[str, Any]) -> None:
        node = CommentNode.from_dict(item, default_oid=default_oid)
        nodes[node.rpid] = node
        parsed_nodes.append(node)
        
        # Bilibili API often nests first 3 replies in item['replies']
        nested_replies = item.get("replies")
        if isinstance(nested_replies, list):
            for reply_item in nested_replies:
                if isinstance(reply_item, dict) and reply_item.get("rpid") not in nodes:
                    extract_node(reply_item)

    for item in raw_comments:
        if isinstance(item, dict):
            extract_node(item)

    root_nodes: List[CommentNode] = []
    placeholder_nodes: Dict[int, CommentNode] = {}

    # Pass 2: Connect parent-child relationships and handle orphans
    for node in parsed_nodes:
        # If it's a top-level comment
        if (node.root_id == 0 and node.parent_id == 0) or (node.rpid == node.root_id):
            if node not in root_nodes:
                root_nodes.append(node)
            continue

        parent_id = node.parent_id if node.parent_id != 0 else node.root_id
        
        # Case A: Parent is present
        if parent_id in nodes:
            nodes[parent_id].add_child(node)
        # Case B: Parent is a previously created placeholder
        elif parent_id in placeholder_nodes:
            placeholder_nodes[parent_id].add_child(node)
        else:
            # Case C: Orphan node - parent missing (deleted, censored, or unpaginated)
            # Create a graceful fallback placeholder
            is_parent_root = (node.root_id == 0 or node.root_id == parent_id)
            placeholder = CommentNode(
                rpid=parent_id,
                oid=node.oid,
                type=node.type,
                mid=0,
                member_name="[系统提示]",
                member_avatar="",
                content="[原评论已失效或被删除]",
                ctime=node.ctime - 1 if node.ctime > 1 else 0,
                like_count=0,
                root_id=node.root_id,
                parent_id=0 if is_parent_root else node.root_id,
                location="系统状态",
                is_fallback_placeholder=True,
                fallback_note="原评论已失效"
            )
            placeholder_nodes[parent_id] = placeholder
            
            # Attach node to placeholder
            node.is_orphan = True
            node.fallback_note = "原回复引用的父评论已失效"
            placeholder.add_child(node)

            # Determine where placeholder should be placed
            if is_parent_root:
                root_nodes.append(placeholder)
            elif node.root_id in nodes:
                nodes[node.root_id].add_child(placeholder)
            else:
                # Root is also missing; place placeholder at root level
                root_nodes.append(placeholder)

    # Sort root nodes: higher likes or newer first
    root_nodes.sort(key=lambda x: (x.like_count, x.ctime), reverse=True)
    return root_nodes
