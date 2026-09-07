"""Unit Tests for Danmaku Engine: Normal, Mode 7 Advanced Code, and BAS Scripts
"""

import unittest
from app.models.danmaku import DanmakuParser, NormalDanmaku, AdvancedDanmaku, BASDanmakuInstruction

class TestDanmakuParser(unittest.TestCase):
    def test_normal_xml_danmaku(self):
        p_attr = "12.5,1,25,16777215,1600000000,0,abcd1234,987654"
        text = "Hello Qt6 KDE Plasma!"
        dm = DanmakuParser.parse_xml_danmaku(p_attr, text)
        self.assertIsInstance(dm, NormalDanmaku)
        self.assertEqual(dm.time_offset, 12.5)
        self.assertEqual(dm.mode, 1)
        self.assertEqual(dm.font_size, 25)
        self.assertEqual(dm.text, "Hello Qt6 KDE Plasma!")
        self.assertTrue(dm.is_rolling)

    def test_mode7_advanced_danmaku(self):
        p_attr = "15.0,7,28,65535,1600000000,0,hash,1111"
        payload = '[0.2, 0.3, "1.0-0.5", 5.0, "Positioned Danmaku", 15, 0, 0.8, 0.7]'
        dm = DanmakuParser.parse_xml_danmaku(p_attr, payload)
        self.assertIsInstance(dm, AdvancedDanmaku)
        self.assertEqual(dm.time_offset, 15.0)
        self.assertEqual(dm.start_x, 0.2)
        self.assertEqual(dm.start_y, 0.3)
        self.assertEqual(dm.end_x, 0.8)
        self.assertEqual(dm.end_y, 0.7)
        self.assertEqual(dm.text, "Positioned Danmaku")

        # Test interpolation
        x, y, alpha, rot = dm.get_interpolated_state(17.5) # halfway (2.5s into 5.0s)
        self.assertAlmostEqual(x, 0.5)
        self.assertAlmostEqual(y, 0.5)
        self.assertAlmostEqual(alpha, 0.75)

    def test_bas_script_parser(self):
        script = """
        def text title {
            text: "KDE Plasma 6";
            x: 0.5;
            y: 0.2;
            fontSize: 32;
            color: #3DAEE9;
            alpha: 1.0;
            duration: 4s;
        }
        set title {
            motion: {
                alpha: [1.0, 0.0];
                y: [0.2, 0.4];
            }
        }
        """
        instructions = DanmakuParser.parse_bas_script(script, time_offset=10.0)
        self.assertEqual(len(instructions), 1)
        instr = instructions[0]
        self.assertEqual(instr.target_id, "title")
        self.assertEqual(instr.element_type, "text")
        self.assertEqual(instr.properties["text"], "KDE Plasma 6")
        self.assertEqual(instr.duration, 4.0)
        self.assertEqual(len(instr.motion_keyframes), 1)

        # Evaluate at t=10.0 (start)
        eval_start = instr.evaluate(10.0)
        self.assertTrue(eval_start["visible"])
        self.assertEqual(eval_start["y"], 0.2)
        self.assertEqual(eval_start["alpha"], 1.0)

        # Evaluate at t=12.0 (midway)
        eval_mid = instr.evaluate(12.0)
        self.assertAlmostEqual(eval_mid["y"], 0.3)
        self.assertAlmostEqual(eval_mid["alpha"], 0.5)

        # Evaluate after duration (invisible)
        eval_end = instr.evaluate(15.0)
        self.assertFalse(eval_end["visible"])

if __name__ == "__main__":
    unittest.main()
