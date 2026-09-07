"""High-Fidelity Mock Data Generator
Provides authentic B站 API responses for offline testing, edge-case validation,
and guaranteed reproduction of orphan comment nodes and BAS danmaku.
"""

from __future__ import annotations
import time
import json
from typing import Dict, Any, List
from app.models.video import RecommendationItem

def get_mock_video_detail(bvid: str = "BV1xx411c7mD") -> Dict[str, Any]:
    return {
        "code": 0,
        "message": "0",
        "ttl": 1,
        "data": {
            "bvid": bvid,
            "aid": 88776655,
            "videos": 1,
            "tid": 208,
            "tname": "科技科学",
            "copyright": 1,
            "pic": "https://i0.hdslb.com/bfs/archive/breeze_kde_demo.jpg",
            "title": "【KDE Breeze / Qt6】构建专业级跨平台桌面架构与被动归档系统实战",
            "pubdate": int(time.time()) - 86400 * 2,
            "ctime": int(time.time()) - 86400 * 2,
            "desc": "本视频深入探讨如何基于 Qt6/PySide6 与 KDE Plasma / Breeze 规范设计专业级桌面客户端。\n涵盖：全键盘焦点控制链、被动式零开销本地数据存档管道、评论树孤儿节点容错机制、以及多身份上下文继承状态机。",
            "state": 0,
            "duration": 754,
            "cid": 12345678,
            "owner": {
                "mid": 998877,
                "name": "KDE_Plasma_Lab",
                "face": "https://i0.hdslb.com/bfs/face/kde_avatar.jpg"
            },
            "stat": {
                "aid": 88776655,
                "view": 528340,
                "danmaku": 12430,
                "reply": 3820,
                "favorite": 48920,
                "coin": 65110,
                "share": 19430,
                "like": 98320,
                "now_rank": 0,
                "his_rank": 12
            },
            "location": "IP属地: 广东",
            "pub_location": "广东"
        }
    }

def get_mock_comments(oid: int = 88776655) -> Dict[str, Any]:
    now = int(time.time())
    return {
        "code": 0,
        "data": {
            "page": {"acount": 120, "count": 120, "num": 1, "size": 20},
            "replies": [
                {
                    "rpid": 1001,
                    "oid": oid,
                    "type": 1,
                    "mid": 80001,
                    "root": 0,
                    "parent": 0,
                    "ctime": now - 3600 * 10,
                    "like": 1420,
                    "member": {
                        "mid": 80001,
                        "uname": "Linux桌面探索者",
                        "avatar": ""
                    },
                    "content": {"message": "KDE Breeze 的色彩规范在暗色主题下的表现力极其出色！全键盘导航在效率工具里完全是刚需。"},
                    "location": "IP属地: 北京",
                    "replies": [
                        {
                            "rpid": 1002,
                            "oid": oid,
                            "type": 1,
                            "mid": 80002,
                            "root": 1001,
                            "parent": 1001,
                            "ctime": now - 3600 * 8,
                            "like": 230,
                            "member": {"mid": 80002, "uname": "ArchMaster", "avatar": ""},
                            "content": {"message": "同意！尤其是 Vim 键位映射（j/k 上下，/ 搜索，g/G 首尾），手完全不用离开键盘。"},
                            "location": "IP属地: 浙江"
                        },
                        {
                            "rpid": 1003,
                            "oid": oid,
                            "type": 1,
                            "mid": 80003,
                            "root": 1001,
                            "parent": 1002,
                            "ctime": now - 3600 * 6,
                            "like": 85,
                            "member": {"mid": 80003, "uname": "QtArchitect", "avatar": ""},
                            "content": {"message": "在 Qt6 里处理深层嵌套焦点链需要专门的 FocusGridManager，做得真扎实！"},
                            "location": "IP属地: 上海"
                        }
                    ]
                },
                {
                    "rpid": 2001,
                    "oid": oid,
                    "type": 1,
                    "mid": 80004,
                    "root": 0,
                    "parent": 0,
                    "ctime": now - 3600 * 5,
                    "like": 890,
                    "member": {"mid": 80004, "uname": "数据库安全员", "avatar": ""},
                    "content": {"message": "被动式零开销本地数据归档思路非常硬核，拦截网络响应直接异步写入 SQLite，既不触发 B 站频控风控，又保证了离线备份完整度。"},
                    "location": "IP属地: 广东",
                    "replies": []
                },
                # Edge Case: Orphan Comment! (parent_id 9999 does NOT exist in payload - deleted/moderated comment)
                {
                    "rpid": 3001,
                    "oid": oid,
                    "type": 1,
                    "mid": 80005,
                    "root": 9999,      # Missing root!
                    "parent": 9999,    # Missing parent!
                    "ctime": now - 3600 * 3,
                    "like": 145,
                    "member": {"mid": 80005, "uname": "容错测试专员", "avatar": ""},
                    "content": {"message": "这是一条引用的原父评论已被删除的孤儿回复。测试评论树算法是否会崩溃或者优雅 Fallback 回退！"},
                    "location": "IP属地: 四川"
                },
                # Second child under the same missing root
                {
                    "rpid": 3002,
                    "oid": oid,
                    "type": 1,
                    "mid": 80006,
                    "root": 9999,
                    "parent": 3001,
                    "ctime": now - 3600 * 2,
                    "like": 42,
                    "member": {"mid": 80006, "uname": "健壮性追问者", "avatar": ""},
                    "content": {"message": "回复上面的孤儿节点：成功挂载在占位父节点下，并清晰显示【原评论已失效】徽标，非常稳！"},
                    "location": "IP属地: 湖北"
                },
                {
                    "rpid": 4001,
                    "oid": oid,
                    "type": 1,
                    "mid": 80007,
                    "root": 0,
                    "parent": 0,
                    "ctime": now - 3600 * 1,
                    "like": 310,
                    "member": {"mid": 80007, "uname": "多身份测试员", "avatar": ""},
                    "content": {"message": "页面路由跳转时能够自动继承上一页面的身份上下文，这个设计在切换小号时体验太丝滑了！"},
                    "location": "IP属地: 江苏"
                }
            ]
        }
    }

def get_mock_recommendations(bvid: str = "BV1xx411c7mD") -> List[RecommendationItem]:
    """Generates standard 40 recommendation items for full interface parity."""
    results = []
    topics = [
        ("Qt6 QGraphicsView 弹幕渲染引擎深度优化", "UP_GraphicsGuru", 998877, 120400, 3200, "15:20", "相似技术推荐"),
        ("KDE Plasma 6 架构演进与现代 C++/Python 生态", "KDE_Plasma_Lab", 998877, 853000, 15400, "22:45", "UP主相关"),
        ("Python 3.13 异步 SQLite 高并发写入最佳实践", "PyBackend_Pro", 889901, 342000, 4820, "18:10", "高赞精选"),
        ("Bilibili BAS 弹幕语法与高级代码弹幕制作全解", "DanmakuMaster", 776655, 239000, 6890, "12:05", "弹幕技术"),
        ("全键盘工作流：从 Vim 到桌面窗口管理器的终极融合", "VimAddict", 665544, 495000, 11200, "28:30", "热门推荐"),
        ("网络代理层被动流量嗅探与本地化时序持久化", "NetSec_Dev", 554433, 189000, 2400, "14:15", "深度解析"),
    ]

    for i in range(1, 41):
        idx = (i - 1) % len(topics)
        title_base, up_name, up_id, play, danmaku, dur, rcmd = topics[idx]
        title = f"[{i:02d}] {title_base}" if i > len(topics) else title_base
        results.append(RecommendationItem(
            aid=90000000 + i,
            bvid=f"BV1rcmd{i:05d}",
            cid=80000000 + i,
            title=title,
            pic=f"https://i0.hdslb.com/bfs/archive/rcmd_{i}.jpg",
            up_name=up_name,
            up_id=up_id,
            play_count=play + i * 137,
            danmaku_count=danmaku + i * 29,
            duration=dur,
            rcmd_reason=rcmd,
            ip_location="IP属地: 广东" if i % 2 == 0 else "IP属地: 北京"
        ))
    return results

def get_mock_danmaku_data() -> List[Dict[str, Any]]:
    """Returns diverse sample danmaku including Normal, Mode 7, and BAS scripts."""
    return [
        {"time": 1.2, "mode": 1, "size": 25, "color": 0xFFFFFF, "text": "KDE Plasma 风格太赏心悦目了！"},
        {"time": 2.5, "mode": 1, "size": 25, "color": 0x3DAEE9, "text": "Breeze Blue 经典强调色"},
        {"time": 3.8, "mode": 5, "size": 28, "color": 0x2ECC71, "text": "【置顶】全键盘导航系统已就绪，按 ? 查看按键指南"},
        {"time": 4.5, "mode": 1, "size": 25, "color": 0xF1C40F, "text": "被动归档已启动，无需额外网络请求！"},
        {"time": 5.2, "mode": 4, "size": 26, "color": 0xE74C3C, "text": "【底部固定】欢迎体验多身份上下文无缝继承"},
        # Mode 7 Advanced Positioned Danmaku
        {
            "time": 6.0,
            "mode": 7,
            "size": 32,
            "color": 0x00FFCC,
            "text": json.dumps([0.1, 0.2, "1.0-0.2", 4.5, "【Mode 7】高级坐标代码弹幕测试 (0.1, 0.2) -> (0.8, 0.2)", 0, 0, 0.8, 0.2])
        },
        # BAS (Bilibili Advanced Script) Script Danmaku
        {
            "time": 8.0,
            "mode": 8,
            "size": 24,
            "color": 0xFF00FF,
            "text": """
            def text bas_title {
                text: "✨ BAS 动态脚本弹幕演示 ✨";
                x: 0.5;
                y: 0.15;
                fontSize: 30;
                color: "#FFDD57";
                alpha: 1.0;
                duration: 6.0s;
            }
            set bas_title {
                motion: {
                    alpha: [1.0, 0.0];
                    x: [0.5, 0.5];
                }
            }
            """
        },
        {"time": 9.5, "mode": 1, "size": 25, "color": 0xFFFFFF, "text": "孤儿评论节点已自动 Fallback 修复，UI 不崩溃"},
        {"time": 11.0, "mode": 1, "size": 25, "color": 0x3DAEE9, "text": "按 j / k 滚动评论，按 Enter 快速回复"}
    ]
