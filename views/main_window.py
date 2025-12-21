from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QSplitter, QToolBar, QStatusBar, QDialog,
                               QDialogButtonBox, QFormLayout, QLineEdit,
                               QDateEdit, QSpinBox, QCheckBox, QTextEdit,
                               QMessageBox, QMenu, QPushButton, QColorDialog)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QAction, QColor
from datetime import date, timedelta
from typing import Optional

from database import DatabaseManager
from models import Task, Project
from .task_tree import TaskTreeWidget
from .gantt_chart import GanttChartWidget
from .styles import MAIN_STYLE


class TaskDialog(QDialog):
    """タスク編集ダイアログ"""

    def __init__(self, parent=None, task: Optional[Task] = None, parent_task: Optional[Task] = None):
        super().__init__(parent)
        self.task = task
        self.parent_task = parent_task
        self.selected_color = None
        if task and task.color:
            self.selected_color = task.color
        self.setup_ui()

    def setup_ui(self):
        """UI初期化"""
        self.setWindowTitle("タスク編集" if self.task else "新規タスク")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        # タスク名
        self.name_edit = QLineEdit()
        if self.task:
            self.name_edit.setText(self.task.name)
        layout.addRow("タスク名:", self.name_edit)

        # 説明
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        if self.task:
            self.description_edit.setPlainText(self.task.description)
        layout.addRow("説明:", self.description_edit)

        # 開始日
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        if self.task:
            self.start_date_edit.setDate(QDate(self.task.start_date.year,
                                               self.task.start_date.month,
                                               self.task.start_date.day))
        else:
            self.start_date_edit.setDate(QDate.currentDate())
        layout.addRow("開始日:", self.start_date_edit)

        # 終了日
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        if self.task:
            self.end_date_edit.setDate(QDate(self.task.end_date.year,
                                            self.task.end_date.month,
                                            self.task.end_date.day))
        else:
            self.end_date_edit.setDate(QDate.currentDate().addDays(7))
        layout.addRow("終了日:", self.end_date_edit)

        # 進捗率
        self.progress_spin = QSpinBox()
        self.progress_spin.setRange(0, 100)
        self.progress_spin.setSuffix("%")
        if self.task:
            self.progress_spin.setValue(self.task.progress)
        layout.addRow("進捗率:", self.progress_spin)

        # マイルストーン
        self.milestone_check = QCheckBox("マイルストーン")
        if self.task:
            self.milestone_check.setChecked(self.task.is_milestone)
        layout.addRow("", self.milestone_check)

        # 色選択
        color_layout = QHBoxLayout()
        self.color_button = QPushButton("色を選択")
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_button)

        self.color_preview = QWidget()
        self.color_preview.setFixedSize(50, 25)
        self.update_color_preview()
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()

        layout.addRow("タスクバーの色:", color_layout)

        # 担当者
        self.assignee_edit = QLineEdit()
        if self.task:
            self.assignee_edit.setText(self.task.assignee or "")
        layout.addRow("担当者:", self.assignee_edit)

        # ボタン
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def choose_color(self):
        """色選択ダイアログを開く"""
        current_color = QColor(self.selected_color) if self.selected_color else QColor(33, 150, 243)
        color = QColorDialog.getColor(current_color, self, "タスクバーの色を選択")
        if color.isValid():
            self.selected_color = color.name()
            self.update_color_preview()

    def update_color_preview(self):
        """色プレビューを更新"""
        if self.selected_color:
            self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #ccc;")
        else:
            self.color_preview.setStyleSheet("background-color: transparent; border: 1px solid #ccc;")

    def get_task_data(self):
        """入力データを取得"""
        return {
            'name': self.name_edit.text(),
            'description': self.description_edit.toPlainText(),
            'start_date': self.start_date_edit.date().toPython(),
            'end_date': self.end_date_edit.date().toPython(),
            'progress': self.progress_spin.value(),
            'is_milestone': self.milestone_check.isChecked(),
            'color': self.selected_color,
            'assignee': self.assignee_edit.text() or None
        }


class MainWindow(QMainWindow):
    """メインウィンドウ"""

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.current_project: Optional[Project] = None
        self.current_tasks = []
        self.setup_ui()
        self.load_or_create_project()

    def setup_ui(self):
        """UI初期化"""
        self.setWindowTitle("Gunshart - ガントチャートアプリ")
        self.setGeometry(100, 100, 1200, 700)

        # スタイル適用
        self.setStyleSheet(MAIN_STYLE)

        # ツールバー
        self.create_toolbar()

        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # レイアウト
        layout = QHBoxLayout(central_widget)

        # スプリッター（左右分割）
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左側：タスクツリー
        self.task_tree = TaskTreeWidget()
        self.task_tree.task_selected.connect(self.on_task_selected)
        self.task_tree.task_deleted.connect(self.on_task_deleted)
        self.task_tree.task_add_root_requested.connect(self.add_new_task)
        self.task_tree.task_add_child_requested.connect(self.add_child_task)
        self.task_tree.task_edit_requested.connect(self.edit_task)
        self.task_tree.task_set_baseline_requested.connect(self.set_baseline)
        self.task_tree.task_clear_baseline_requested.connect(self.clear_baseline)
        splitter.addWidget(self.task_tree)

        # 右側：ガントチャート
        self.gantt_chart = GanttChartWidget()
        self.gantt_chart.task_clicked.connect(self.on_task_selected)
        self.gantt_chart.task_date_changed.connect(self.on_task_date_changed)
        self.gantt_chart.task_progress_changed.connect(self.on_task_progress_changed)
        self.gantt_chart.task_edit_requested.connect(self.edit_task)
        self.gantt_chart.task_delete_requested.connect(self.on_task_deleted)
        splitter.addWidget(self.gantt_chart)

        # スプリッター比率
        splitter.setSizes([300, 900])

        layout.addWidget(splitter)

        # ステータスバー
        self.statusBar().showMessage("準備完了")

    def create_toolbar(self):
        """ツールバー作成"""
        toolbar = QToolBar("メインツールバー")
        self.addToolBar(toolbar)

        # 新規タスク
        new_task_action = QAction("新規タスク", self)
        new_task_action.triggered.connect(self.add_new_task)
        toolbar.addAction(new_task_action)

        toolbar.addSeparator()

        # 表示モード切替
        day_view_action = QAction("日表示", self)
        day_view_action.triggered.connect(lambda: self.change_view_mode('day'))
        toolbar.addAction(day_view_action)

        week_view_action = QAction("週表示", self)
        week_view_action.triggered.connect(lambda: self.change_view_mode('week'))
        toolbar.addAction(week_view_action)

        month_view_action = QAction("月表示", self)
        month_view_action.triggered.connect(lambda: self.change_view_mode('month'))
        toolbar.addAction(month_view_action)

        toolbar.addSeparator()

        # 更新
        refresh_action = QAction("更新", self)
        refresh_action.triggered.connect(self.refresh_view)
        toolbar.addAction(refresh_action)

    def load_or_create_project(self):
        """プロジェクトを読み込みまたは作成"""
        projects = self.db.get_all_projects()

        if projects:
            # 最初のプロジェクトを読み込み
            self.current_project = Project.from_db_row(projects[0])
        else:
            # デフォルトプロジェクトを作成
            project_id = self.db.create_project("デフォルトプロジェクト", "ガントチャートプロジェクト")
            self.current_project = self.db.get_project(project_id)
            self.current_project = Project.from_db_row(self.current_project)

            # サンプルタスクを作成
            self.create_sample_tasks()

        self.refresh_view()

    def create_sample_tasks(self):
        """サンプルタスクを作成"""
        if not self.current_project:
            return

        today = date.today()

        # タスク1
        task1_id = self.db.create_task(
            self.current_project.id,
            "プロジェクト計画",
            str(today),
            str(today + timedelta(days=5)),
            progress=100
        )

        # タスク2
        task2_id = self.db.create_task(
            self.current_project.id,
            "設計フェーズ",
            str(today + timedelta(days=6)),
            str(today + timedelta(days=15)),
            progress=60
        )

        # タスク2の子タスク
        self.db.create_task(
            self.current_project.id,
            "要件定義",
            str(today + timedelta(days=6)),
            str(today + timedelta(days=9)),
            parent_id=task2_id,
            progress=100
        )

        self.db.create_task(
            self.current_project.id,
            "基本設計",
            str(today + timedelta(days=10)),
            str(today + timedelta(days=15)),
            parent_id=task2_id,
            progress=50
        )

        # タスク3
        task3_id = self.db.create_task(
            self.current_project.id,
            "実装フェーズ",
            str(today + timedelta(days=16)),
            str(today + timedelta(days=30)),
            progress=20
        )

        # マイルストーン
        self.db.create_task(
            self.current_project.id,
            "リリース",
            str(today + timedelta(days=31)),
            str(today + timedelta(days=31)),
            progress=0,
            is_milestone=True
        )

        # 依存関係
        self.db.create_dependency(task1_id, task2_id, "FS")
        self.db.create_dependency(task2_id, task3_id, "FS")

    def refresh_view(self):
        """ビューを更新"""
        if not self.current_project:
            return

        # タスクを読み込み
        task_rows = self.db.get_tasks_by_project(self.current_project.id)
        self.current_tasks = [Task.from_db_row(row) for row in task_rows]

        # 階層構造を構築（childrenリストをクリア）
        for task in self.current_tasks:
            task.children = []

        # 親子関係を構築
        task_dict = {t.id: t for t in self.current_tasks}
        root_tasks = []
        for task in self.current_tasks:
            if task.parent_id and task.parent_id in task_dict:
                task_dict[task.parent_id].add_child(task)
            elif task.parent_id is None:
                root_tasks.append(task)

        # 依存関係を読み込み
        from models import TaskDependency
        dep_rows = self.db.get_all_dependencies(self.current_project.id)
        dependencies = [TaskDependency.from_db_row(row) for row in dep_rows]

        # ツリービューを更新
        self.task_tree.load_tasks(self.current_tasks)

        # ガントチャートを更新（ルートタスクのみ渡す）
        self.gantt_chart.load_tasks(root_tasks, dependencies)

        self.statusBar().showMessage(f"タスク数: {len(self.current_tasks)}")

    def add_new_task(self, parent_id: Optional[int] = None):
        """新規タスク追加"""
        dialog = TaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_task_data()

            task_id = self.db.create_task(
                self.current_project.id,
                data['name'],
                str(data['start_date']),
                str(data['end_date']),
                parent_id=parent_id,
                description=data['description'],
                progress=data['progress'],
                is_milestone=data['is_milestone'],
                color=data['color'],
                assignee=data['assignee']
            )

            self.refresh_view()
            self.statusBar().showMessage(f"タスク '{data['name']}' を追加しました")

    def add_child_task(self, parent_id: int):
        """子タスク追加"""
        self.add_new_task(parent_id=parent_id)

    def change_view_mode(self, mode: str):
        """表示モードを変更"""
        self.gantt_chart.set_view_mode(mode)
        mode_name = {'day': '日', 'week': '週', 'month': '月'}
        self.statusBar().showMessage(f"表示モード: {mode_name.get(mode, mode)}")

    def edit_task(self, task_id: int):
        """タスク編集"""
        task = next((t for t in self.current_tasks if t.id == task_id), None)
        if not task:
            return

        dialog = TaskDialog(self, task=task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_task_data()

            self.db.update_task(
                task_id,
                name=data['name'],
                description=data['description'],
                start_date=str(data['start_date']),
                end_date=str(data['end_date']),
                progress=data['progress'],
                is_milestone=data['is_milestone'],
                color=data['color'],
                assignee=data['assignee']
            )

            self.refresh_view()
            self.statusBar().showMessage(f"タスク '{data['name']}' を更新しました")

    def on_task_selected(self, task_id: int):
        """タスク選択時"""
        task = next((t for t in self.current_tasks if t.id == task_id), None)
        if task:
            self.statusBar().showMessage(
                f"選択: {task.name} ({task.start_date} ～ {task.end_date})"
            )

    def on_task_date_changed(self, task_id: int, start_date: str, end_date: str):
        """タスクの日付変更時（ドラッグ&ドロップ）"""
        self.db.update_task(
            task_id,
            start_date=start_date,
            end_date=end_date
        )
        self.refresh_view()
        task = next((t for t in self.current_tasks if t.id == task_id), None)
        if task:
            self.statusBar().showMessage(f"タスク '{task.name}' の日付を更新しました")

    def on_task_progress_changed(self, task_id: int, progress: int):
        """タスクの進捗率変更時（ドラッグ&ドロップ）"""
        self.db.update_task(
            task_id,
            progress=progress
        )
        self.refresh_view()
        task = next((t for t in self.current_tasks if t.id == task_id), None)
        if task:
            self.statusBar().showMessage(f"タスク '{task.name}' の進捗率を{progress}%に更新しました")

    def set_baseline(self, task_id: int):
        """ベースライン設定"""
        self.db.set_baseline(task_id)
        self.refresh_view()
        task = next((t for t in self.current_tasks if t.id == task_id), None)
        if task:
            self.statusBar().showMessage(f"タスク '{task.name}' のベースラインを設定しました")

    def clear_baseline(self, task_id: int):
        """ベースラインクリア"""
        self.db.clear_baseline(task_id)
        self.refresh_view()
        task = next((t for t in self.current_tasks if t.id == task_id), None)
        if task:
            self.statusBar().showMessage(f"タスク '{task.name}' のベースラインをクリアしました")

    def on_task_deleted(self, task_id: int):
        """タスク削除時"""
        self.db.delete_task(task_id)
        self.refresh_view()
        self.statusBar().showMessage("タスクを削除しました")

    def closeEvent(self, event):
        """ウィンドウクローズ時"""
        self.db.close()
        event.accept()
