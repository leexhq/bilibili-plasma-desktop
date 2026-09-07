"""Danmaku Engine Models & Parsers
Supports Normal Danmaku, Mode 7 Advanced Code Danmaku, and BAS (Bilibili Advanced Script).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import re
import json

@dataclass
class NormalDanmaku:
    time_offset: float = 0.0  # In seconds
    mode: int = 1  # 1: Rolling, 4: Bottom, 5: Top, 6: Reverse
    font_size: int = 25
    color: int = 0xFFFFFF
    text: str = ""
    timestamp: int = 0
    pool: int = 0
    sender_hash: str = ""
    dmid: int = 0

    @property
    def color_hex(self) -> str:
        return f"#{self.color:06X}"

    @property
    def is_rolling(self) -> bool:
        return self.mode in (1, 2, 3)

    @property
    def is_top(self) -> bool:
        return self.mode == 5

    @property
    def is_bottom(self) -> bool:
        return self.mode == 4

@dataclass
class AdvancedDanmaku:
    """Mode 7 Positioned / 3D Code Danmaku"""
    time_offset: float = 0.0
    text: str = ""
    font_size: int = 25
    color: int = 0xFFFFFF
    start_x: float = 0.5  # 0.0 - 1.0 normalized screen coordinate
    start_y: float = 0.5
    end_x: float = 0.5
    end_y: float = 0.5
    alpha_start: float = 1.0
    alpha_end: float = 1.0
    duration: float = 4.0  # seconds
    rotate_z: float = 0.0  # degrees
    rotate_y: float = 0.0
    delay: float = 0.0

    def get_interpolated_state(self, current_time: float) -> Tuple[float, float, float, float]:
        """Returns (x, y, alpha, rotation) at current playback time."""
        progress = (current_time - self.time_offset) / max(self.duration, 0.01)
        progress = max(0.0, min(1.0, progress))
        
        curr_x = self.start_x + (self.end_x - self.start_x) * progress
        curr_y = self.start_y + (self.end_y - self.start_y) * progress
        curr_alpha = self.alpha_start + (self.alpha_end - self.alpha_start) * progress
        return (curr_x, curr_y, curr_alpha, self.rotate_z)

@dataclass
class BASDanmakuInstruction:
    """Compiled BAS (Bilibili Advanced Script) Execution Unit"""
    time_offset: float = 0.0
    target_id: str = ""
    element_type: str = "text"  # text, rect, button, path
    properties: Dict[str, Any] = field(default_factory=dict)
    motion_keyframes: List[Dict[str, Any]] = field(default_factory=list)
    duration: float = 5.0
    script_raw: str = ""

    def evaluate(self, current_time: float) -> Dict[str, Any]:
        """Calculates animated properties at the given timeline second."""
        elapsed = current_time - self.time_offset
        if elapsed < 0 or elapsed > self.duration:
            return {"visible": False}

        props = dict(self.properties)
        props["visible"] = True
        
        # Calculate motion interpolations if specified
        for motion in self.motion_keyframes:
            m_dur = motion.get("duration", self.duration)
            t = min(1.0, max(0.0, elapsed / max(m_dur, 0.01)))
            for prop_name, (start_val, end_val) in motion.get("tweens", {}).items():
                props[prop_name] = start_val + (end_val - start_val) * t

        return props

class DanmakuParser:
    """Comprehensive parser for Bilibili XML, JSON, Mode 7, and BAS Danmaku scripts."""

    @staticmethod
    def parse_xml_danmaku(p_attr: str, text: str) -> NormalDanmaku | AdvancedDanmaku:
        """Parses <d p="0.5,1,25,16777215,1600000000,0,hash,12345">text</d>"""
        parts = p_attr.split(",")
        if len(parts) < 8:
            return NormalDanmaku(text=text)

        try:
            time_offset = float(parts[0])
            mode = int(parts[1])
            font_size = int(parts[2])
            color = int(parts[3])
            timestamp = int(parts[4])
            pool = int(parts[5])
            sender_hash = parts[6]
            dmid = int(parts[7])

            if mode == 7:
                # Mode 7 advanced positioning
                return DanmakuParser.parse_mode7(text, time_offset, font_size, color)

            return NormalDanmaku(
                time_offset=time_offset,
                mode=mode,
                font_size=font_size,
                color=color,
                text=text,
                timestamp=timestamp,
                pool=pool,
                sender_hash=sender_hash,
                dmid=dmid
            )
        except Exception:
            return NormalDanmaku(text=text)

    @staticmethod
    def parse_mode7(content: str, time_offset: float, font_size: int, color: int) -> AdvancedDanmaku:
        """Parses Mode 7 JSON/array parameters: [x, y, alpha, dur, text, rz, ry, endx, endy, ...]"""
        try:
            arr = json.loads(content)
            if isinstance(arr, list) and len(arr) >= 5:
                start_x = float(arr[0]) if isinstance(arr[0], (int, float)) else 0.5
                start_y = float(arr[1]) if isinstance(arr[1], (int, float)) else 0.5
                alpha_str = str(arr[2]).split("-")
                alpha_start = float(alpha_str[0]) if alpha_str[0] else 1.0
                alpha_end = float(alpha_str[1]) if len(alpha_str) > 1 else alpha_start
                duration = float(arr[3]) if isinstance(arr[3], (int, float)) else 4.0
                danmaku_text = str(arr[4])
                rotate_z = float(arr[5]) if len(arr) > 5 and isinstance(arr[5], (int, float)) else 0.0
                rotate_y = float(arr[6]) if len(arr) > 6 and isinstance(arr[6], (int, float)) else 0.0
                end_x = float(arr[7]) if len(arr) > 7 and isinstance(arr[7], (int, float)) else start_x
                end_y = float(arr[8]) if len(arr) > 8 and isinstance(arr[8], (int, float)) else start_y

                # Normalize 0-1000 scale to 0.0-1.0 if needed
                if start_x > 1.0 or end_x > 1.0:
                    start_x /= 1000.0
                    end_x /= 1000.0
                if start_y > 1.0 or end_y > 1.0:
                    start_y /= 1000.0
                    end_y /= 1000.0

                return AdvancedDanmaku(
                    time_offset=time_offset,
                    text=danmaku_text,
                    font_size=font_size,
                    color=color,
                    start_x=start_x,
                    start_y=start_y,
                    end_x=end_x,
                    end_y=end_y,
                    alpha_start=alpha_start,
                    alpha_end=alpha_end,
                    duration=duration,
                    rotate_z=rotate_z,
                    rotate_y=rotate_y
                )
        except Exception:
            pass

        return AdvancedDanmaku(
            time_offset=time_offset,
            text=content,
            font_size=font_size,
            color=color
        )

    @staticmethod
    def _extract_blocks(text: str, keyword: str) -> List[Tuple[str, str, str]]:
        """Extracts statements like `keyword <identifier> { ... }` with nested brace support."""
        pattern = re.compile(rf'{keyword}\s+([\w\s]+?)\s*\{{', re.MULTILINE)
        results = []
        for match in pattern.finditer(text):
            ident = match.group(1).strip()
            start_pos = match.end()
            depth = 1
            idx = start_pos
            while idx < len(text) and depth > 0:
                if text[idx] == '{':
                    depth += 1
                elif text[idx] == '}':
                    depth -= 1
                idx += 1
            if depth == 0:
                body = text[start_pos:idx-1]
                full_raw = text[match.start():idx]
                results.append((ident, body, full_raw))
        return results

    @staticmethod
    def parse_bas_script(script_text: str, time_offset: float = 0.0) -> List[BASDanmakuInstruction]:
        """
        Parses Bilibili Advanced Script (BAS) syntax.
        Supports declarations (def text / def rect / def button) and property blocks.
        """
        instructions: List[BASDanmakuInstruction] = []
        created_elements: Dict[str, BASDanmakuInstruction] = {}

        # 1. Parse 'def <type> <id> { ... }'
        for ident, body, raw_block in DanmakuParser._extract_blocks(script_text, "def"):
            parts = ident.split()
            if len(parts) >= 2:
                elem_type = parts[0].lower()
                elem_id = parts[1]
            else:
                elem_type = "text"
                elem_id = parts[0]

            props: Dict[str, Any] = {
                "x": 0.5,
                "y": 0.5,
                "color": "#FFFFFF",
                "fontSize": 24,
                "alpha": 1.0,
                "text": ""
            }
            duration = 5.0

            for line in body.split(";"):
                line = line.strip()
                if not line or ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip().strip('"\'')
                if k == "text":
                    props["text"] = v
                elif k in ("x", "y", "alpha"):
                    try:
                        props[k] = float(v.replace("%", "")) / (100.0 if "%" in v else 1.0)
                    except ValueError:
                        pass
                elif k in ("fontSize", "size"):
                    try:
                        props["fontSize"] = int(v.replace("px", ""))
                    except ValueError:
                        pass
                elif k == "color":
                    props["color"] = v
                elif k == "duration":
                    try:
                        duration = float(v.replace("s", ""))
                    except ValueError:
                        pass

            instr = BASDanmakuInstruction(
                time_offset=time_offset,
                target_id=elem_id,
                element_type=elem_type,
                properties=props,
                duration=duration,
                script_raw=raw_block
            )
            created_elements[elem_id] = instr
            instructions.append(instr)

        # 2. Parse 'set <id> { ... }'
        for elem_id, body, _ in DanmakuParser._extract_blocks(script_text, "set"):
            elem_id = elem_id.strip()
            if elem_id in created_elements:
                instr = created_elements[elem_id]
                motion_dict: Dict[str, Any] = {"duration": instr.duration, "tweens": {}}
                
                # Extract key: [start, end] pairs inside motion blocks or direct sets
                tween_pattern = re.compile(r'(\w+)\s*:\s*\[\s*([\d\.\-]+)\s*,\s*([\d\.\-]+)\s*\]')
                for match in tween_pattern.finditer(body):
                    prop_name = match.group(1)
                    s_val = float(match.group(2))
                    e_val = float(match.group(3))
                    motion_dict["tweens"][prop_name] = (s_val, e_val)

                if motion_dict["tweens"]:
                    instr.motion_keyframes.append(motion_dict)

        return instructions

