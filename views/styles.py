"""アプリケーション全体のスタイル定義"""

MAIN_STYLE = """
QMainWindow {
    background-color: #f5f5f5;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    spacing: 8px;
    padding: 8px;
}

QToolBar QToolButton {
    background-color: #2196F3;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}

QToolBar QToolButton:hover {
    background-color: #1976D2;
}

QToolBar QToolButton:pressed {
    background-color: #0D47A1;
}

QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e0e0e0;
    color: #666666;
    font-size: 12px;
}

/* ツリービュー */
QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    font-size: 13px;
}

QTreeWidget::item {
    padding: 8px;
    border-bottom: 1px solid #f5f5f5;
}

QTreeWidget::item:hover {
    background-color: #f5f5f5;
}

QTreeWidget::item:selected {
    background-color: #E3F2FD;
    color: #1976D2;
}

QHeaderView::section {
    background-color: #fafafa;
    color: #666666;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #e0e0e0;
    font-weight: 600;
    font-size: 12px;
}

/* ダイアログ */
QDialog {
    background-color: #ffffff;
}

QLabel {
    color: #333333;
    font-size: 13px;
}

QLineEdit, QTextEdit, QSpinBox, QDateEdit {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 8px;
    font-size: 13px;
    color: #333333;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDateEdit:focus {
    border: 2px solid #2196F3;
    padding: 7px;
}

QCheckBox {
    color: #333333;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #e0e0e0;
    border-radius: 3px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #2196F3;
    border-color: #2196F3;
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMiAxMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMSA1TDQgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIGZpbGw9Im5vbmUiLz48L3N2Zz4=);
}

/* ボタン */
QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:pressed {
    background-color: #0D47A1;
}

QPushButton:disabled {
    background-color: #e0e0e0;
    color: #999999;
}

/* ダイアログボタン */
QDialogButtonBox QPushButton {
    min-width: 80px;
}

/* スプリッター */
QSplitter::handle {
    background-color: #e0e0e0;
    width: 1px;
}

QSplitter::handle:hover {
    background-color: #2196F3;
    width: 2px;
}

/* メニュー */
QMenu {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 3px;
}

QMenu::item:selected {
    background-color: #E3F2FD;
    color: #1976D2;
}

QMenu::separator {
    height: 1px;
    background-color: #e0e0e0;
    margin: 4px 0px;
}

/* スクロールバー */
QScrollBar:vertical {
    background-color: #f5f5f5;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #c0c0c0;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a0a0a0;
}

QScrollBar:horizontal {
    background-color: #f5f5f5;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #c0c0c0;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #a0a0a0;
}

QScrollBar::add-line, QScrollBar::sub-line {
    border: none;
    background: none;
}
"""
