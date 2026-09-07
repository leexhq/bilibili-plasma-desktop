"""Unit Tests for Multi-Identity Context State Machine & Inheritance
"""

import unittest
from app.core.state_machine import NavigationStateMachine, PageContext
from app.core.account_manager import AccountManager, Account

class TestStateMachine(unittest.TestCase):
    def setUp(self):
        self.fsm = NavigationStateMachine()

    def test_identity_context_inheritance(self):
        # Step 1: Set page 1 with identity A
        self.fsm.switch_page_identity("acc_main")
        self.assertEqual(self.fsm.current_identity_id, "acc_main")

        # Step 2: Navigate to video page without specifying identity -> Must inherit 'acc_main'
        ctx2 = self.fsm.navigate_to("video", "BV12345678")
        self.assertEqual(ctx2.identity_id, "acc_main")
        self.assertEqual(self.fsm.current_identity_id, "acc_main")

        # Step 3: Switch identity on page 2 to 'acc_sub_dev'
        self.fsm.switch_page_identity("acc_sub_dev")
        self.assertEqual(self.fsm.current_identity_id, "acc_sub_dev")

        # Step 4: Navigate to UP Space page -> Must inherit 'acc_sub_dev'
        ctx3 = self.fsm.navigate_to("up_space", "998877")
        self.assertEqual(ctx3.identity_id, "acc_sub_dev")
        self.assertEqual(self.fsm.current_identity_id, "acc_sub_dev")

        # Step 5: Navigate back -> Must restore page 2 with 'acc_sub_dev'
        back_ctx = self.fsm.navigate_back()
        self.assertIsNotNone(back_ctx)
        self.assertEqual(back_ctx.target_id, "BV12345678")
        self.assertEqual(back_ctx.identity_id, "acc_sub_dev")

    def test_isolated_action_execution(self):
        self.fsm.switch_page_identity("acc_main")
        
        executed_by = []
        def mock_action(acc: Account):
            executed_by.append(acc.id)
            return f"Action done by {acc.id}"

        # Execute under isolated identity 'acc_anon' without affecting current page identity
        res = self.fsm.execute_isolated_action("send_danmaku", identity_id="acc_anon", callback=mock_action)
        self.assertEqual(executed_by[0], "acc_anon")
        self.assertEqual(res, "Action done by acc_anon")
        # Current page identity remains 'acc_main'
        self.assertEqual(self.fsm.current_identity_id, "acc_main")

    def test_follow_listener_trigger(self):
        captured_events = []
        def on_follow(identity_id: str, up_id: int, up_name: str, is_following: bool):
            captured_events.append((identity_id, up_id, up_name, is_following))

        self.fsm.add_follow_listener(on_follow)
        self.fsm.trigger_follow_event(998877, "KDE_Plasma_Lab", True, identity_id="acc_main")

        self.assertEqual(len(captured_events), 1)
        self.assertEqual(captured_events[0], ("acc_main", 998877, "KDE_Plasma_Lab", True))

if __name__ == "__main__":
    unittest.main()
