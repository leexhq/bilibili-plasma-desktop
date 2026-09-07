"""Generates high-resolution pixel-perfect screenshots of the application
for inclusion in README.md and documentation.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from app.ui.theme import apply_breeze_theme
from app.ui.main_window import BilibiliMainWindow
from app.ui.views.account_dialog import AccountManagerDialog
from app.ui.keyboard import KeyboardShortcutHelpDialog

def capture_screenshots():
    out_dir = Path("assets/screenshots")
    out_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    apply_breeze_theme(app)

    # 1. Main Window with Player, Danmaku, Recommendations, and Comments
    win = BilibiliMainWindow()
    win.show()
    app.processEvents()

    # Wait for layout to settle
    def step1_capture_main():
        print("Capturing 01_main_player_breeze.png...")
        pixmap = win.grab()
        pixmap.save(str(out_dir / "01_main_player_breeze.png"))

        # 2. Capture Detached Standalone Window
        win.video_view._detach_player()
        app.processEvents()
        
        QTimer.singleShot(200, step2_capture_detached)

    def step2_capture_detached():
        print("Capturing 02_detached_pip_window.png...")
        if win.video_view.detached_window:
            win.video_view.detached_window.resize(1024, 620)
            app.processEvents()
            pixmap = win.video_view.detached_window.grab()
            pixmap.save(str(out_dir / "02_detached_pip_window.png"))
        
        # Restore player back to main window
        win.video_view._reembed_player()
        app.processEvents()

        # 3. Switch to UP Space View (Multi-Identity Matrix)
        print("Capturing 03_multi_identity_matrix.png...")
        win._on_navigate_to_up_space(998877, "KDE_Plasma_Lab")
        app.processEvents()

        QTimer.singleShot(200, step3_capture_up_space)

    def step3_capture_up_space():
        pixmap = win.grab()
        pixmap.save(str(out_dir / "03_multi_identity_matrix.png"))

        # 4. Switch to Passive Archive Inspector
        print("Capturing 04_passive_archive_inspector.png...")
        win.open_archive_view()
        app.processEvents()

        QTimer.singleShot(200, step4_capture_archive)

    def step4_capture_archive():
        pixmap = win.grab()
        pixmap.save(str(out_dir / "04_passive_archive_inspector.png"))

        # 5. Account Manager Dialog
        print("Capturing 05_account_manager_dialog.png...")
        acc_dlg = AccountManagerDialog()
        acc_dlg.show()
        app.processEvents()
        pixmap = acc_dlg.grab()
        pixmap.save(str(out_dir / "05_account_manager_dialog.png"))
        acc_dlg.close()

        # 6. Keyboard Shortcuts Help Dialog
        print("Capturing 06_keyboard_shortcuts_help.png...")
        help_dlg = KeyboardShortcutHelpDialog()
        help_dlg.show()
        app.processEvents()
        pixmap = help_dlg.grab()
        pixmap.save(str(out_dir / "06_keyboard_shortcuts_help.png"))
        help_dlg.close()

        print("All screenshots successfully captured!")
        win.close()
        app.quit()

    QTimer.singleShot(500, step1_capture_main)
    app.exec()

if __name__ == "__main__":
    capture_screenshots()
