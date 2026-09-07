"""KDE Plasma / Breeze Design System & Stylesheet
Follows KDE Breeze Dark and Light visual guidelines, color metrics, and focus ring semantics.
"""

from __future__ import annotations
from PySide6.QtGui import QPalette, QColor, QFont
from PySide6.QtWidgets import QApplication, QWidget

# KDE Breeze Dark Color Palette
BREEZE_DARK = {
    "bg_window": "#232629",       # Plasma dark window background
    "bg_view": "#31363b",         # Card / view background
    "bg_elevated": "#2a2e32",     # Elevated card / panel
    "bg_hover": "#3c4248",        # Hover highlight
    "bg_active": "#474e56",       # Active / pressed surface
    "fg_text": "#eff0f1",         # Primary readable text
    "fg_secondary": "#bdc3c7",    # Secondary muted text
    "accent": "#3daee9",          # KDE Breeze Blue accent
    "accent_hover": "#2980b9",    # Darker blue
    "accent_subtle": "#1d587a",   # Subtle accent background
    "border": "#474d54",          # Subtle border
    "border_focus": "#3daee9",    # Breeze high-contrast focus ring
    "badge_bg": "#1e3a5f",        # Tag/badge background
    "badge_fg": "#78b9e6",        # Tag text
    "danger": "#ed1515",          # KDE error/danger
    "warning": "#f67400",         # KDE warning
    "success": "#27ae60",         # KDE success
    "orphan_bg": "#43281c",       # Fallback orphan banner
    "orphan_fg": "#f39c12",       # Fallback orphan text
}

def get_breeze_qss() -> str:
    """Returns the full KDE Breeze Dark QSS stylesheet."""
    return f"""
    /* Global KDE Plasma Breeze Base */
    QMainWindow, QDialog, QWidget {{
        background-color: {BREEZE_DARK['bg_window']};
        color: {BREEZE_DARK['fg_text']};
        font-family: "Noto Sans", "Segoe UI", sans-serif;
        font-size: 13px;
    }}

    /* Global Focus Outline for Full Keyboard Accessibility */
    *:focus {{
        outline: none;
        border: 2px solid {BREEZE_DARK['border_focus']};
    }}

    /* Scrollbars - Breeze Flat Minimalist */
    QScrollBar:vertical {{
        background: {BREEZE_DARK['bg_window']};
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {BREEZE_DARK['border']};
        min-height: 24px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {BREEZE_DARK['accent']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* Push Buttons - KDE Flat & Standard */
    QPushButton {{
        background-color: {BREEZE_DARK['bg_view']};
        color: {BREEZE_DARK['fg_text']};
        border: 1px solid {BREEZE_DARK['border']};
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {BREEZE_DARK['bg_hover']};
        border-color: {BREEZE_DARK['accent']};
    }}
    QPushButton:pressed {{
        background-color: {BREEZE_DARK['bg_active']};
    }}
    QPushButton:focus {{
        border: 2px solid {BREEZE_DARK['border_focus']};
    }}
    QPushButton.primary {{
        background-color: {BREEZE_DARK['accent']};
        color: #ffffff;
        border: 1px solid {BREEZE_DARK['accent_hover']};
    }}
    QPushButton.primary:hover {{
        background-color: {BREEZE_DARK['accent_hover']};
    }}
    QPushButton.danger {{
        background-color: #a82020;
        color: #ffffff;
        border: 1px solid #c0392b;
    }}

    /* LineEdit & TextEdit */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {BREEZE_DARK['bg_view']};
        color: {BREEZE_DARK['fg_text']};
        border: 1px solid {BREEZE_DARK['border']};
        border-radius: 4px;
        padding: 6px 10px;
        selection-background-color: {BREEZE_DARK['accent']};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 2px solid {BREEZE_DARK['border_focus']};
        background-color: {BREEZE_DARK['bg_elevated']};
    }}

    /* QComboBox */
    QComboBox {{
        background-color: {BREEZE_DARK['bg_view']};
        color: {BREEZE_DARK['fg_text']};
        border: 1px solid {BREEZE_DARK['border']};
        border-radius: 4px;
        padding: 5px 12px;
        min-width: 6em;
    }}
    QComboBox:hover {{
        border-color: {BREEZE_DARK['accent']};
    }}
    QComboBox:focus {{
        border: 2px solid {BREEZE_DARK['border_focus']};
    }}
    QComboBox QAbstractItemView {{
        background-color: {BREEZE_DARK['bg_elevated']};
        border: 1px solid {BREEZE_DARK['border']};
        color: {BREEZE_DARK['fg_text']};
        selection-background-color: {BREEZE_DARK['accent']};
    }}

    /* Tab Widget - KDE Plasma Breeze Tabs */
    QTabWidget::pane {{
        border: 1px solid {BREEZE_DARK['border']};
        background: {BREEZE_DARK['bg_window']};
        border-radius: 4px;
    }}
    QTabBar::tab {{
        background: {BREEZE_DARK['bg_window']};
        color: {BREEZE_DARK['fg_secondary']};
        border: 1px solid transparent;
        border-bottom: 2px solid transparent;
        padding: 8px 16px;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{
        color: {BREEZE_DARK['accent']};
        border-bottom: 2px solid {BREEZE_DARK['accent']};
        background: {BREEZE_DARK['bg_elevated']};
    }}
    QTabBar::tab:hover:!selected {{
        color: {BREEZE_DARK['fg_text']};
        background: {BREEZE_DARK['bg_hover']};
    }}

    /* QListWidget / QTreeWidget */
    QListWidget, QTreeWidget, QTableView {{
        background-color: {BREEZE_DARK['bg_window']};
        border: 1px solid {BREEZE_DARK['border']};
        border-radius: 4px;
        color: {BREEZE_DARK['fg_text']};
    }}
    QListWidget::item, QTreeWidget::item {{
        padding: 6px;
        border-radius: 4px;
    }}
    QListWidget::item:hover, QTreeWidget::item:hover {{
        background-color: {BREEZE_DARK['bg_hover']};
    }}
    QListWidget::item:selected, QTreeWidget::item:selected {{
        background-color: {BREEZE_DARK['accent_subtle']};
        color: #ffffff;
        border: 1px solid {BREEZE_DARK['accent']};
    }}

    /* Status Bar */
    QStatusBar {{
        background-color: {BREEZE_DARK['bg_elevated']};
        color: {BREEZE_DARK['fg_secondary']};
        border-top: 1px solid {BREEZE_DARK['border']};
    }}

    /* Badges & Pills */
    QLabel.badge {{
        background-color: {BREEZE_DARK['badge_bg']};
        color: {BREEZE_DARK['badge_fg']};
        border-radius: 3px;
        padding: 2px 6px;
        font-size: 11px;
    }}
    QLabel.badge-orphan {{
        background-color: {BREEZE_DARK['orphan_bg']};
        color: {BREEZE_DARK['orphan_fg']};
        border: 1px solid {BREEZE_DARK['orphan_fg']};
        border-radius: 3px;
        padding: 2px 6px;
        font-size: 11px;
        font-weight: bold;
    }}
    QLabel.badge-active {{
        background-color: {BREEZE_DARK['accent_subtle']};
        color: {BREEZE_DARK['accent']};
        border: 1px solid {BREEZE_DARK['accent']};
        border-radius: 3px;
        padding: 2px 6px;
        font-size: 11px;
    }}

    /* Tooltips */
    QToolTip {{
        background-color: {BREEZE_DARK['bg_elevated']};
        color: {BREEZE_DARK['fg_text']};
        border: 1px solid {BREEZE_DARK['border']};
        border-radius: 3px;
        padding: 4px 8px;
    }}

    /* QSplitter Draggable Dividers - KDE Breeze */
    QSplitter::handle {{
        background-color: #31363b;
    }}
    QSplitter::handle:horizontal {{
        width: 6px;
    }}
    QSplitter::handle:vertical {{
        height: 6px;
    }}
    QSplitter::handle:hover {{
        background-color: {BREEZE_DARK['accent']};
    }}
    QSplitter::handle:pressed {{
        background-color: {BREEZE_DARK['accent_hover']};
    }}
    """

def apply_breeze_theme(app: QApplication) -> None:
    """Applies KDE Breeze Palette and Stylesheet to the application."""
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BREEZE_DARK["bg_window"]))
    palette.setColor(QPalette.WindowText, QColor(BREEZE_DARK["fg_text"]))
    palette.setColor(QPalette.Base, QColor(BREEZE_DARK["bg_view"]))
    palette.setColor(QPalette.AlternateBase, QColor(BREEZE_DARK["bg_elevated"]))
    palette.setColor(QPalette.ToolTipBase, QColor(BREEZE_DARK["bg_elevated"]))
    palette.setColor(QPalette.ToolTipText, QColor(BREEZE_DARK["fg_text"]))
    palette.setColor(QPalette.Text, QColor(BREEZE_DARK["fg_text"]))
    palette.setColor(QPalette.Button, QColor(BREEZE_DARK["bg_view"]))
    palette.setColor(QPalette.ButtonText, QColor(BREEZE_DARK["fg_text"]))
    palette.setColor(QPalette.BrightText, QColor(BREEZE_DARK["accent"]))
    palette.setColor(QPalette.Highlight, QColor(BREEZE_DARK["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))

    app.setPalette(palette)
    app.setStyleSheet(get_breeze_qss())

def apply_default_semantics(widget: QWidget, is_default_action: bool = True) -> None:
    """
    Enforces specification rule:
    'All "default values" refer to initial focus / preset options in dialogs, menus, or selectors.'
    """
    if is_default_action:
        widget.setFocus()
        if hasattr(widget, "setDefault"):
            widget.setDefault(True)
