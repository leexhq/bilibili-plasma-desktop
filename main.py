"""Application Entry Point for Bilibili KDE Plasma / Breeze Desktop Client
"""

from __future__ import annotations
import sys
import argparse
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.ui.theme import apply_breeze_theme
from app.ui.main_window import BilibiliMainWindow
from app.core.storage import archive_writer
from app.core.config import config_instance

def main() -> None:
    parser = argparse.ArgumentParser(description="Bilibili KDE Plasma / Breeze Desktop Client")
    parser.add_argument("--bvid", type=str, default="BV1xx411c7mD", help="Initial BVID to load")
    parser.add_argument("--offline", action="store_true", help="Force offline resilience mode")
    parser.add_argument("--test-run", action="store_true", help="Initialize and exit immediately for CI verification")
    args = parser.parse_args()

    # Qt Application Setup
    app = QApplication(sys.argv)
    app.setApplicationName("BilibiliPlasmaClient")
    app.setOrganizationName("KDE_Plasma_Lab")
    app.setApplicationVersion(config_instance.get("version", "1.0.0"))

    # Apply KDE Plasma / Breeze Dark Theme
    apply_breeze_theme(app)

    # Instantiate Main Window
    window = BilibiliMainWindow()
    if args.bvid:
        window.video_view.load_video(args.bvid)

    if args.test_run:
        print("[CI] Application initialized successfully. Exiting for test run.")
        archive_writer.stop()
        sys.exit(0)

    window.show()

    try:
        exit_code = app.exec()
    finally:
        # Graceful shutdown of async SQLite worker thread
        print("[Shutdown] Stopping AsyncArchiveWriter background worker...")
        archive_writer.stop()

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
