import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple


class DatabaseManager:
    """SQLiteデータベース管理クラス"""

    def __init__(self, db_path: str = "gunshart.db"):
        self.db_path = db_path
        self.connection = None
        self.initialize_database()

    def initialize_database(self):
        """データベース初期化"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

        # スキーマファイルを読み込んで実行
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, 'r', encoding='utf-8') as f:
            self.connection.executescript(f.read())
        self.connection.commit()

        # マイグレーション: color列が存在しない場合は追加
        self._migrate_add_color_column()
        # マイグレーション: assignee列が存在しない場合は追加
        self._migrate_add_assignee_column()

    def _migrate_add_color_column(self):
        """マイグレーション: tasksテーブルにcolor列を追加"""
        cursor = self.connection.cursor()
        try:
            # color列が既に存在するかチェック
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'color' not in columns:
                # color列を追加
                cursor.execute("ALTER TABLE tasks ADD COLUMN color TEXT DEFAULT NULL")
                self.connection.commit()
        except sqlite3.Error:
            # エラーが発生しても続行（テーブルが存在しない場合など）
            pass

    def _migrate_add_assignee_column(self):
        """マイグレーション: tasksテーブルにassignee列を追加"""
        cursor = self.connection.cursor()
        try:
            # assignee列が既に存在するかチェック
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'assignee' not in columns:
                # assignee列を追加
                cursor.execute("ALTER TABLE tasks ADD COLUMN assignee TEXT DEFAULT NULL")
                self.connection.commit()
        except sqlite3.Error:
            # エラーが発生しても続行（テーブルが存在しない場合など）
            pass

    def close(self):
        """データベース接続をクローズ"""
        if self.connection:
            self.connection.close()

    # プロジェクト関連メソッド
    def create_project(self, name: str, description: str = "") -> int:
        """新規プロジェクト作成"""
        cursor = self.connection.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description)
        )
        self.connection.commit()
        return cursor.lastrowid

    def get_all_projects(self) -> List[sqlite3.Row]:
        """全プロジェクト取得"""
        cursor = self.connection.execute("SELECT * FROM projects ORDER BY created_at DESC")
        return cursor.fetchall()

    def get_project(self, project_id: int) -> Optional[sqlite3.Row]:
        """プロジェクト取得"""
        cursor = self.connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        return cursor.fetchone()

    def update_project(self, project_id: int, name: str, description: str = ""):
        """プロジェクト更新"""
        self.connection.execute(
            "UPDATE projects SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (name, description, project_id)
        )
        self.connection.commit()

    def delete_project(self, project_id: int):
        """プロジェクト削除"""
        self.connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.connection.commit()

    # タスク関連メソッド
    def create_task(self, project_id: int, name: str, start_date: str, end_date: str,
                   parent_id: Optional[int] = None, description: str = "",
                   progress: int = 0, is_milestone: bool = False, color: Optional[str] = None,
                   assignee: Optional[str] = None) -> int:
        """新規タスク作成"""
        cursor = self.connection.execute(
            """INSERT INTO tasks (project_id, parent_id, name, description, start_date, end_date, progress, is_milestone, color, assignee)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, parent_id, name, description, start_date, end_date, progress, is_milestone, color, assignee)
        )
        self.connection.commit()
        return cursor.lastrowid

    def get_tasks_by_project(self, project_id: int) -> List[sqlite3.Row]:
        """プロジェクトの全タスク取得"""
        cursor = self.connection.execute(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY sort_order, id",
            (project_id,)
        )
        return cursor.fetchall()

    def get_task(self, task_id: int) -> Optional[sqlite3.Row]:
        """タスク取得"""
        cursor = self.connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return cursor.fetchone()

    def update_task(self, task_id: int, **kwargs):
        """タスク更新"""
        allowed_fields = ['name', 'description', 'start_date', 'end_date', 'progress',
                         'is_milestone', 'is_expanded', 'parent_id', 'sort_order', 'color', 'assignee']

        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if updates:
            values.append(task_id)
            query = f"UPDATE tasks SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            self.connection.execute(query, values)
            self.connection.commit()

    def delete_task(self, task_id: int):
        """タスク削除"""
        self.connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.connection.commit()

    def get_child_tasks(self, parent_id: int) -> List[sqlite3.Row]:
        """子タスク取得"""
        cursor = self.connection.execute(
            "SELECT * FROM tasks WHERE parent_id = ? ORDER BY sort_order, id",
            (parent_id,)
        )
        return cursor.fetchall()

    # 依存関係関連メソッド
    def create_dependency(self, predecessor_id: int, successor_id: int,
                         dependency_type: str = "FS") -> int:
        """タスク依存関係作成"""
        try:
            cursor = self.connection.execute(
                "INSERT INTO task_dependencies (predecessor_id, successor_id, dependency_type) VALUES (?, ?, ?)",
                (predecessor_id, successor_id, dependency_type)
            )
            self.connection.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return -1  # 既に存在する場合

    def get_task_dependencies(self, task_id: int) -> Tuple[List[sqlite3.Row], List[sqlite3.Row]]:
        """タスクの依存関係取得（先行タスク、後続タスク）"""
        # 先行タスク
        predecessors = self.connection.execute(
            """SELECT t.*, td.dependency_type
               FROM tasks t
               JOIN task_dependencies td ON t.id = td.predecessor_id
               WHERE td.successor_id = ?""",
            (task_id,)
        ).fetchall()

        # 後続タスク
        successors = self.connection.execute(
            """SELECT t.*, td.dependency_type
               FROM tasks t
               JOIN task_dependencies td ON t.id = td.successor_id
               WHERE td.predecessor_id = ?""",
            (task_id,)
        ).fetchall()

        return predecessors, successors

    def delete_dependency(self, predecessor_id: int, successor_id: int):
        """依存関係削除"""
        self.connection.execute(
            "DELETE FROM task_dependencies WHERE predecessor_id = ? AND successor_id = ?",
            (predecessor_id, successor_id)
        )
        self.connection.commit()

    def get_all_dependencies(self, project_id: int) -> List[sqlite3.Row]:
        """プロジェクトの全依存関係取得"""
        cursor = self.connection.execute(
            """SELECT td.*
               FROM task_dependencies td
               JOIN tasks t ON td.predecessor_id = t.id
               WHERE t.project_id = ?""",
            (project_id,)
        )
        return cursor.fetchall()
