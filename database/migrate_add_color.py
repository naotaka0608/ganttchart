"""
データベースマイグレーション: tasksテーブルにcolor列を追加

使い方:
    python database/migrate_add_color.py
"""
import sqlite3
from pathlib import Path


def migrate_add_color_column(db_path: str = "gunshart.db"):
    """tasksテーブルにcolor列を追加"""

    # データベースが存在するか確認
    if not Path(db_path).exists():
        print(f"データベースファイル '{db_path}' が見つかりません。")
        print("新規作成される場合は、アプリケーションを起動してください。")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # color列が既に存在するかチェック
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'color' in columns:
            print("✓ color列は既に存在しています。マイグレーション不要です。")
            return

        # color列を追加
        print("tasksテーブルにcolor列を追加中...")
        cursor.execute("ALTER TABLE tasks ADD COLUMN color TEXT DEFAULT NULL")
        conn.commit()
        print("✓ マイグレーション完了！color列が正常に追加されました。")

        # 確認
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"\n現在のtasksテーブルの列: {', '.join(columns)}")

    except sqlite3.Error as e:
        print(f"✗ エラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_add_color_column()
