"""Koyu ve açık tema tanımları (Catppuccin Mocha paleti)."""

KOYU_TEMA = """
QMainWindow, QDialog, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QFrame#sol_panel {
    background-color: #181825;
    border-right: 1px solid #313244;
}

QPushButton#menu_btn {
    background-color: transparent;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
}
QPushButton#menu_btn:hover {
    background-color: #313244;
}
QPushButton#menu_btn:checked {
    background-color: #45475a;
    color: #89b4fa;
    font-weight: bold;
}

QPushButton#cikis_btn {
    background-color: transparent;
    color: #f38ba8;
    border: 1px solid #f38ba8;
    border-radius: 6px;
    padding: 8px 16px;
    text-align: left;
    font-size: 13px;
    margin-top: 4px;
}
QPushButton#cikis_btn:hover {
    background-color: #f38ba822;
}

QLabel#baslik {
    color: #89b4fa;
    font-size: 18px;
    font-weight: bold;
}
QLabel#alt_baslik {
    color: #a6adc8;
    font-size: 12px;
}

QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #b4befe;
}
QPushButton:pressed {
    background-color: #7287fd;
}
QPushButton:disabled {
    background-color: #45475a;
    color: #6c7086;
}

QPushButton#btn_iptal {
    background-color: #45475a;
    color: #cdd6f4;
}
QPushButton#btn_iptal:hover {
    background-color: #585b70;
}

QPushButton#btn_tehlike {
    background-color: #f38ba8;
    color: #1e1e2e;
}
QPushButton#btn_tehlike:hover {
    background-color: #eba0ac;
}

QPushButton#btn_basari {
    background-color: #a6e3a1;
    color: #1e1e2e;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 6px 10px;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {
    border: 1px solid #89b4fa;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
    border: 1px solid #45475a;
}

QTableView, QTableWidget {
    background-color: #181825;
    color: #cdd6f4;
    gridline-color: #313244;
    border: 1px solid #313244;
    selection-background-color: #313244;
    selection-color: #89b4fa;
    alternate-background-color: #1e1e2e;
}
QTableView::item:selected, QTableWidget::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}
QHeaderView::section {
    background-color: #181825;
    color: #a6adc8;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #313244;
    font-weight: bold;
}
QHeaderView::section:hover {
    background-color: #313244;
}

QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 8px 18px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
    background-color: #1e1e2e;
}
QTabBar::tab:hover {
    background-color: #313244;
}

QScrollBar:vertical {
    background: #181825;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #181825;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QGroupBox {
    border: 1px solid #313244;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    color: #a6adc8;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QRadioButton, QCheckBox {
    color: #cdd6f4;
    spacing: 6px;
}
QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #45475a;
    border-radius: 3px;
    background-color: #313244;
}
QRadioButton::indicator {
    border-radius: 8px;
}
QRadioButton::indicator:checked, QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

QMessageBox {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QMessageBox QPushButton {
    min-width: 80px;
}

QSplitter::handle {
    background-color: #313244;
}

QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}

QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px;
}

QLabel#kpi_kart {
    background-color: #313244;
    border-radius: 8px;
    padding: 12px;
}
QLabel#uyari_etiket {
    color: #f38ba8;
    font-weight: bold;
}
QLabel#basari_etiket {
    color: #a6e3a1;
}
"""

ACIK_TEMA = """
QMainWindow, QDialog, QWidget {
    background-color: #f8f8f8;
    color: #1a1a1a;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}
QFrame#sol_panel {
    background-color: #e8e8e8;
    border-right: 1px solid #cccccc;
}
QPushButton#menu_btn {
    background-color: transparent;
    color: #1a1a1a;
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
    text-align: left;
}
QPushButton#menu_btn:hover { background-color: #dddddd; }
QPushButton#menu_btn:checked {
    background-color: #cccccc;
    color: #1d6fa4;
    font-weight: bold;
}
QPushButton#cikis_btn {
    background-color: transparent;
    color: #cc3333;
    border: 1px solid #cc3333;
    border-radius: 6px;
    padding: 8px 16px;
    text-align: left;
    font-size: 13px;
    margin-top: 4px;
}
QPushButton#cikis_btn:hover { background-color: #cc333322; }
QLabel#baslik { color: #1d6fa4; font-size: 18px; font-weight: bold; }
QPushButton {
    background-color: #1d6fa4;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: bold;
}
QPushButton:hover { background-color: #2980b9; }
QPushButton#btn_iptal { background-color: #aaaaaa; color: #ffffff; }
QPushButton#btn_tehlike { background-color: #d32f2f; color: #ffffff; }
QPushButton#btn_basari { background-color: #388e3c; color: #ffffff; }
QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #cccccc;
    border-radius: 5px;
    padding: 6px 10px;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid #1d6fa4; }
QTableView, QTableWidget {
    background-color: #ffffff;
    color: #1a1a1a;
    gridline-color: #e0e0e0;
    alternate-background-color: #f5f5f5;
    selection-background-color: #cce5ff;
    selection-color: #1a1a1a;
}
QHeaderView::section {
    background-color: #e8e8e8;
    color: #444444;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #cccccc;
    font-weight: bold;
}
QTabBar::tab { background-color: #e8e8e8; color: #444; padding: 8px 18px; border: none; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #1d6fa4; border-bottom: 2px solid #1d6fa4; background-color: #f8f8f8; }
QGroupBox { border: 1px solid #cccccc; border-radius: 6px; margin-top: 10px; padding-top: 8px; color: #444; font-weight: bold; }
QScrollBar:vertical { background: #f0f0f0; width: 10px; }
QScrollBar::handle:vertical { background: #aaaaaa; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QStatusBar { background-color: #e8e8e8; color: #555555; border-top: 1px solid #cccccc; }
QLabel#uyari_etiket { color: #d32f2f; font-weight: bold; }
QLabel#basari_etiket { color: #388e3c; }
"""


def tema_al(tema_adi: str) -> str:
    if tema_adi == "acik":
        return ACIK_TEMA
    return KOYU_TEMA
