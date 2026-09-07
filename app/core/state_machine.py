"""Multi-Identity Context State Machine & Navigation Router
Enforces identity context inheritance across page routing and isolated operations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
import time
from app.core.account_manager import account_manager, Account

@dataclass
class PageContext:
    """Represents the context state of a page/route, including the inherited identity."""
    page_type: str  # 'home', 'video', 'up_space', 'archive', 'search'
    target_id: str  # bvid, up_id, or query string
    identity_id: str  # Active account ID bound to this page context
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def clone(self) -> PageContext:
        return PageContext(
            page_type=self.page_type,
            target_id=self.target_id,
            identity_id=self.identity_id,
            params=dict(self.params),
            timestamp=self.timestamp
        )

class NavigationStateMachine:
    """
    Finite State Machine governing page transitions and identity inheritance.
    Rule: When navigating to a new page, unless an identity is explicitly specified,
    it strictly inherits the active identity of the previous page context.
    """

    def __init__(self):
        self._history_stack: List[PageContext] = []
        self._forward_stack: List[PageContext] = []
        self._current_context: Optional[PageContext] = None

        # Observer callbacks
        self._nav_listeners: List[Callable[[PageContext], None]] = []
        self._identity_listeners: List[Callable[[str, PageContext], None]] = []
        self._follow_event_listeners: List[Callable[[str, int, str, bool], None]] = []

        # Initialize with default root context
        initial_id = account_manager.active_account_id or "acc_main"
        self._current_context = PageContext(
            page_type="video",
            target_id="BV1xx411c7mD",
            identity_id=initial_id,
            params={"title": "【4K60FPS】超清画质示例与深度全键盘交互测试"}
        )
        self._history_stack.append(self._current_context)

    @property
    def current_context(self) -> PageContext:
        return self._current_context

    @property
    def current_identity_id(self) -> str:
        return self._current_context.identity_id if self._current_context else account_manager.active_account_id

    @property
    def current_account(self) -> Account:
        acc = account_manager.get_account(self.current_identity_id)
        if acc:
            return acc
        return account_manager.get_active_account()

    def navigate_to(
        self,
        page_type: str,
        target_id: str,
        identity_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> PageContext:
        """
        Navigates to a new page.
        Context Inheritance: If identity_id is None, inherits current_context.identity_id.
        """
        inherited_id = identity_id if identity_id else self.current_identity_id
        
        new_context = PageContext(
            page_type=page_type,
            target_id=target_id,
            identity_id=inherited_id,
            params=params or {}
        )

        if self._current_context:
            self._history_stack.append(self._current_context)
        self._forward_stack.clear()
        self._current_context = new_context

        # Sync global active account for convenience
        account_manager.set_active_account(inherited_id)

        self._emit_navigation(new_context)
        return new_context

    def navigate_back(self) -> Optional[PageContext]:
        if not self._history_stack:
            return None
        
        if self._current_context:
            self._forward_stack.append(self._current_context)
        
        self._current_context = self._history_stack.pop()
        account_manager.set_active_account(self._current_context.identity_id)
        
        self._emit_navigation(self._current_context)
        return self._current_context

    def navigate_forward(self) -> Optional[PageContext]:
        if not self._forward_stack:
            return None
            
        if self._current_context:
            self._history_stack.append(self._current_context)
            
        self._current_context = self._forward_stack.pop()
        account_manager.set_active_account(self._current_context.identity_id)
        
        self._emit_navigation(self._current_context)
        return self._current_context

    def switch_page_identity(self, identity_id: str) -> None:
        """Dynamically rebinds the identity of the current page."""
        if not self._current_context:
            return
        if self._current_context.identity_id != identity_id:
            self._current_context.identity_id = identity_id
            account_manager.set_active_account(identity_id)
            self._emit_identity_changed(identity_id, self._current_context)

    def execute_isolated_action(
        self,
        action_name: str,
        identity_id: Optional[str] = None,
        callback: Optional[Callable[[Account], Any]] = None
    ) -> Any:
        """
        Executes an action (danmaku, comment, like, follow) under a specified identity,
        without permanently modifying the page's current identity context if they differ.
        """
        effective_id = identity_id or self.current_identity_id
        target_account = account_manager.get_account(effective_id) or account_manager.get_active_account()

        result = None
        if callback:
            result = callback(target_account)
        return result

    def trigger_follow_event(self, up_id: int, up_name: str, is_following: bool = True, identity_id: Optional[str] = None) -> None:
        """
        Triggers real-time follow event.
        Listeners can perform automatic follow completion and pop up a message dialog.
        """
        eff_id = identity_id or self.current_identity_id
        for listener in self._follow_event_listeners:
            try:
                listener(eff_id, up_id, up_name, is_following)
            except Exception as e:
                print(f"[StateMachine] Follow listener error: {e}")

    # Listener registration
    def add_navigation_listener(self, callback: Callable[[PageContext], None]) -> None:
        self._nav_listeners.append(callback)

    def add_identity_listener(self, callback: Callable[[str, PageContext], None]) -> None:
        self._identity_listeners.append(callback)

    def add_follow_listener(self, callback: Callable[[str, int, str, bool], None]) -> None:
        self._follow_event_listeners.append(callback)

    def _emit_navigation(self, context: PageContext) -> None:
        for cb in self._nav_listeners:
            try:
                cb(context)
            except Exception as e:
                print(f"[StateMachine] Nav callback error: {e}")

    def _emit_identity_changed(self, identity_id: str, context: PageContext) -> None:
        for cb in self._identity_listeners:
            try:
                cb(identity_id, context)
            except Exception as e:
                print(f"[StateMachine] Identity callback error: {e}")

# Global state machine instance
state_machine = NavigationStateMachine()
