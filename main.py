import sys
from PySide6.QtWidgets import QApplication
from views import MainWindow


def main():
    """アプリケーションエントリーポイント"""
    app = QApplication(sys.argv)

    # アプリケーション情報
    app.setApplicationName("Gunshart")
    app.setOrganizationName("Gunshart")
    app.setApplicationVersion("1.0.0")

    # メインウィンドウを表示
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
