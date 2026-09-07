"""Multi-Account Identity Manager
Supports SESSDATA / Cookie quick import, account isolation, and multi-identity follow aggregation.
"""

from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

@dataclass
class Account:
    id: str
    name: str
    mid: int
    avatar: str = ""
    sessdata: str = ""
    bili_jct: str = ""
    buvid3: str = ""
    level: int = 6
    is_vip: bool = False
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> Account:
        return cls(
            id=data.get("id", "user"),
            name=data.get("name", "未命名账户"),
            mid=data.get("mid", 0),
            avatar=data.get("avatar", ""),
            sessdata=data.get("sessdata", ""),
            bili_jct=data.get("bili_jct", ""),
            buvid3=data.get("buvid3", ""),
            level=data.get("level", 6),
            is_vip=data.get("is_vip", False),
            tags=data.get("tags", [])
        )

    def get_cookie_header(self) -> str:
        cookies = []
        if self.sessdata:
            cookies.append(f"SESSDATA={self.sessdata}")
        if self.bili_jct:
            cookies.append(f"bili_jct={self.bili_jct}")
        if self.buvid3:
            cookies.append(f"buvid3={self.buvid3}")
        if self.mid:
            cookies.append(f"DedeUserID={self.mid}")
        return "; ".join(cookies)

class AccountManager:
    def __init__(self, storage_path: str = "data/accounts.json"):
        p = Path(storage_path)
        if not p.is_absolute():
            from app.core.config import get_base_dir
            p = get_base_dir() / p
        self.storage_path = p
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.accounts: Dict[str, Account] = {}
        self.active_account_id: str = ""
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("accounts", []):
                        acc = Account.from_dict(item)
                        self.accounts[acc.id] = acc
                    self.active_account_id = data.get("active_account_id", "")
            except Exception as e:
                print(f"[AccountManager] Failed to load accounts: {e}")

        # Ensure default preset accounts if empty for instant out-of-the-box readiness
        if not self.accounts:
            self._create_default_preset_accounts()

        if self.active_account_id not in self.accounts and self.accounts:
            self.active_account_id = next(iter(self.accounts.keys()))

    def _create_default_preset_accounts(self) -> None:
        presets = [
            Account(
                id="acc_main",
                name="主身份 (ArchUser)",
                mid=10001,
                avatar="https://i0.hdslb.com/bfs/face/member/noface.jpg",
                sessdata="mock_sessdata_archuser_10001",
                bili_jct="mock_csrf_token_main",
                level=6,
                is_vip=True,
                tags=["主号", "开发", "KDE"]
            ),
            Account(
                id="acc_sub_dev",
                name="备用身份 (PlasmaHacker)",
                mid=20002,
                avatar="https://i0.hdslb.com/bfs/face/member/noface.jpg",
                sessdata="mock_sessdata_plasma_20002",
                bili_jct="mock_csrf_token_sub",
                level=5,
                is_vip=False,
                tags=["小号", "技术测试"]
            ),
            Account(
                id="acc_anon",
                name="匿名追番身份 (BreezeWatcher)",
                mid=30003,
                avatar="https://i0.hdslb.com/bfs/face/member/noface.jpg",
                sessdata="mock_sessdata_breeze_30003",
                bili_jct="mock_csrf_token_anon",
                level=4,
                is_vip=False,
                tags=["动漫", "观影"]
            )
        ]
        for acc in presets:
            self.accounts[acc.id] = acc
        self.active_account_id = presets[0].id
        self.save()

    def save(self) -> None:
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({
                    "active_account_id": self.active_account_id,
                    "accounts": [acc.to_dict() for acc in self.accounts.values()]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AccountManager] Failed to save accounts: {e}")

    def get_account(self, account_id: str) -> Optional[Account]:
        return self.accounts.get(account_id)

    def get_active_account(self) -> Account:
        if self.active_account_id in self.accounts:
            return self.accounts[self.active_account_id]
        if self.accounts:
            return next(iter(self.accounts.values()))
        return Account(id="guest", name="访客", mid=0)

    def set_active_account(self, account_id: str) -> bool:
        if account_id in self.accounts:
            self.active_account_id = account_id
            self.save()
            return True
        return False

    def import_from_cookie(self, cookie_str: str, name: Optional[str] = None) -> Account:
        """
        Parses cookie string containing SESSDATA, bili_jct, DedeUserID.
        """
        pairs = {}
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                pairs[k.strip()] = v.strip()

        sessdata = pairs.get("SESSDATA", "")
        bili_jct = pairs.get("bili_jct", "")
        buvid3 = pairs.get("buvid3", "")
        mid_str = pairs.get("DedeUserID", "")
        mid = int(mid_str) if mid_str.isdigit() else 100000 + len(self.accounts) + 1
        
        account_id = f"acc_{mid}"
        acc_name = name or pairs.get("uname") or f"用户_{mid}"

        account = Account(
            id=account_id,
            name=acc_name,
            mid=mid,
            sessdata=sessdata,
            bili_jct=bili_jct,
            buvid3=buvid3,
            level=6,
            tags=["导入账户"]
        )
        self.accounts[account_id] = account
        self.save()
        return account

    def remove_account(self, account_id: str) -> bool:
        if account_id in self.accounts:
            del self.accounts[account_id]
            if self.active_account_id == account_id:
                self.active_account_id = next(iter(self.accounts.keys())) if self.accounts else ""
            self.save()
            return True
        return False

    def list_all_accounts(self) -> List[Account]:
        return list(self.accounts.values())

account_manager = AccountManager()
