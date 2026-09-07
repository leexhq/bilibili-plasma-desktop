"""Video and Recommendation Data Models
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any

@dataclass
class VideoInfo:
    aid: int = 0
    bvid: str = ""
    cid: int = 0
    title: str = ""
    desc: str = ""
    pic: str = ""
    up_id: int = 0
    up_name: str = ""
    up_face: str = ""
    pubdate: int = 0
    duration: int = 0
    view: int = 0
    danmaku: int = 0
    reply: int = 0
    favorite: int = 0
    coin: int = 0
    share: int = 0
    like: int = 0
    ip_location: str = "IP属地: 未知"
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("raw_data", None)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VideoInfo:
        owner = data.get("owner", {})
        stat = data.get("stat", {})
        
        # Parse IP location if available
        location = "IP属地: 未知"
        if "location" in data:
            location = data["location"]
        elif "pub_location" in data:
            location = f"IP属地: {data['pub_location']}"
            
        return cls(
            aid=data.get("aid", 0),
            bvid=data.get("bvid", ""),
            cid=data.get("cid", 0),
            title=data.get("title", "未命名视频"),
            desc=data.get("desc", ""),
            pic=data.get("pic", ""),
            up_id=owner.get("mid", data.get("mid", 0)),
            up_name=owner.get("name", data.get("author", "未知UP主")),
            up_face=owner.get("face", ""),
            pubdate=data.get("pubdate", 0),
            duration=data.get("duration", 0),
            view=stat.get("view", data.get("play", 0)),
            danmaku=stat.get("danmaku", data.get("video_review", 0)),
            reply=stat.get("reply", 0),
            favorite=stat.get("favorite", 0),
            coin=stat.get("coin", 0),
            share=stat.get("share", 0),
            like=stat.get("like", 0),
            ip_location=location,
            raw_data=data
        )

@dataclass
class RecommendationItem:
    aid: int = 0
    bvid: str = ""
    cid: int = 0
    title: str = ""
    pic: str = ""
    up_name: str = ""
    up_id: int = 0
    play_count: int = 0
    danmaku_count: int = 0
    duration: str = "00:00"
    rcmd_reason: str = ""
    ip_location: str = "IP属地: 未知"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RecommendationItem:
        owner = data.get("owner", {})
        stat = data.get("stat", {})
        dur = data.get("duration", 0)
        if isinstance(dur, int):
            m, s = divmod(dur, 60)
            duration_str = f"{m:02d}:{s:02d}"
        else:
            duration_str = str(dur)
            
        rcmd = data.get("rcmd_reason", {}).get("content", "") if isinstance(data.get("rcmd_reason"), dict) else str(data.get("rcmd_reason", ""))
        
        return cls(
            aid=data.get("aid", 0),
            bvid=data.get("bvid", ""),
            cid=data.get("cid", 0),
            title=data.get("title", ""),
            pic=data.get("pic", ""),
            up_name=owner.get("name", data.get("author", "")),
            up_id=owner.get("mid", 0),
            play_count=stat.get("view", 0),
            danmaku_count=stat.get("danmaku", 0),
            duration=duration_str,
            rcmd_reason=rcmd,
            ip_location=data.get("pub_location", "IP属地: 广东")
        )
