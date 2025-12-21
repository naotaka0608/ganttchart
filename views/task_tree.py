from PySide6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog,
                               QMessageBox, QHeaderView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QDropEvent
from typing import Dict, List, Optional
from models import Task


class TaskTreeWidget(QTreeWidget):
    """タスクツリービューウィジェット"""

    task_selected = Signal(int)  # タスクID
    task_updated = Signal()
    task_deleted = Signal(int)
    task_add_root_requested = Signal()
    task_add_child_requested = Signal(int)  # parent_id
    task_edit_requested = Signal(int)  # task_id
    task_set_baseline_requested = Signal(int)  # task_id
    task_clear_baseline_requested = Signal(int)  # task_id
    task_order_changed = Signal()  # タスク順序変更

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_map: Dict[int, QTreeWidgetItem] = {}  # task_id -> QTreeWidgetItem
        self.setup_ui()

    def setup_ui(self):
        """UI初期化"""
        self.setHeaderLabels(["タスク名", "進捗率", "開始日", "終了日", "担当者"])
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 60)
        self.setColumnWidth(2, 90)
        self.setColumnWidth(3, 90)
        self.setColumnWidth(4, 100)

        # ドラッグ&ドロップ有効化
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)

        # 右クリックメニュー
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # アイテム選択イベント
        self.itemClicked.connect(self.on_item_clicked)

        # 展開/折りたたみイベント
        self.itemExpanded.connect(self.on_item_expanded)
        self.itemCollapsed.connect(self.on_item_collapsed)

    def load_tasks(self, tasks: List[Task]):
        """タスクリストをツリーに読み込み"""
        self.clear()
        self.task_map.clear()

        # childrenリストをクリア（重複を防ぐ）
        for task in tasks:
            task.children = []

        # 親子関係を構築
        root_tasks = [t for t in tasks if t.parent_id is None]
        task_dict = {t.id: t for t in tasks}

        # 子タスクを親に追加
        for task in tasks:
            if task.parent_id and task.parent_id in task_dict:
                task_dict[task.parent_id].add_child(task)

        # ツリーに追加
        for task in root_tasks:
            self._add_task_item(task, None)

    def _add_task_item(self, task: Task, parent_item: Optional[QTreeWidgetItem]) -> QTreeWidgetItem:
        """タスクアイテムをツリーに追加"""
        if parent_item:
            item = QTreeWidgetItem(parent_item)
        else:
            item = QTreeWidgetItem(self)

        # タスク情報を設定
        milestone_prefix = "◆ " if task.is_milestone else ""
        item.setText(0, f"{milestone_prefix}{task.name}")
        item.setText(1, f"{task.progress}%")
        item.setText(2, task.start_date.strftime("%Y-%m-%d"))
        item.setText(3, task.end_date.strftime("%Y-%m-%d"))
        item.setText(4, task.assignee or "")

        # タスクIDをデータとして保存
        item.setData(0, Qt.ItemDataRole.UserRole, task.id)

        # 展開状態を設定
        item.setExpanded(task.is_expanded)

        # マップに追加
        self.task_map[task.id] = item

        # 子タスクを追加
        for child in task.children:
            self._add_task_item(child, item)

        return item

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """アイテムクリック時"""
        task_id = item.data(0, Qt.ItemDataRole.UserRole)
        if task_id:
            self.task_selected.emit(task_id)

    def on_item_expanded(self, item: QTreeWidgetItem):
        """アイテム展開時"""
        task_id = item.data(0, Qt.ItemDataRole.UserRole)
        if task_id:
            # データベースに展開状態を保存
            self.task_updated.emit()

    def on_item_collapsed(self, item: QTreeWidgetItem):
        """アイテム折りたたみ時"""
        task_id = item.data(0, Qt.ItemDataRole.UserRole)
        if task_id:
            # データベースに折りたたみ状態を保存
            self.task_updated.emit()

    def show_context_menu(self, position):
        """右クリックメニュー表示"""
        item = self.itemAt(position)

        menu = QMenu(self)

        # 新規タスク追加
        add_root_action = QAction("ルートタスク追加", self)
        add_root_action.triggered.connect(self.add_root_task)
        menu.addAction(add_root_action)

        if item:
            task_id = item.data(0, Qt.ItemDataRole.UserRole)

            # 子タスク追加
            add_child_action = QAction("子タスク追加", self)
            add_child_action.triggered.connect(lambda: self.add_child_task(task_id))
            menu.addAction(add_child_action)

            menu.addSeparator()

            # 編集
            edit_action = QAction("編集", self)
            edit_action.triggered.connect(lambda: self.edit_task(task_id))
            menu.addAction(edit_action)

            menu.addSeparator()

            # ベースライン設定
            set_baseline_action = QAction("ベースライン設定", self)
            set_baseline_action.triggered.connect(lambda: self.set_baseline(task_id))
            menu.addAction(set_baseline_action)

            # ベースラインクリア
            clear_baseline_action = QAction("ベースラインクリア", self)
            clear_baseline_action.triggered.connect(lambda: self.clear_baseline(task_id))
            menu.addAction(clear_baseline_action)

            menu.addSeparator()

            # 削除
            delete_action = QAction("削除", self)
            delete_action.triggered.connect(lambda: self.delete_task(task_id))
            menu.addAction(delete_action)

        menu.exec(self.viewport().mapToGlobal(position))

    def add_root_task(self):
        """ルートタスク追加"""
        self.task_add_root_requested.emit()

    def add_child_task(self, parent_id: int):
        """子タスク追加"""
        self.task_add_child_requested.emit(parent_id)

    def edit_task(self, task_id: int):
        """タスク編集"""
        self.task_edit_requested.emit(task_id)

    def set_baseline(self, task_id: int):
        """ベースライン設定"""
        self.task_set_baseline_requested.emit(task_id)

    def clear_baseline(self, task_id: int):
        """ベースラインクリア"""
        self.task_clear_baseline_requested.emit(task_id)

    def delete_task(self, task_id: int):
        """タスク削除"""
        reply = QMessageBox.question(
            self,
            "確認",
            "このタスクを削除しますか？\n子タスクも削除されます。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.task_deleted.emit(task_id)

    def update_task_item(self, task: Task):
        """タスクアイテムを更新"""
        if task.id in self.task_map:
            item = self.task_map[task.id]
            milestone_prefix = "◆ " if task.is_milestone else ""
            item.setText(0, f"{milestone_prefix}{task.name}")
            item.setText(1, f"{task.progress}%")
            item.setText(2, task.start_date.strftime("%Y-%m-%d"))
            item.setText(3, task.end_date.strftime("%Y-%m-%d"))
            item.setText(4, task.assignee or "")

    def get_selected_task_id(self) -> Optional[int]:
        """選択中のタスクIDを取得"""
        item = self.currentItem()
        if item:
            return item.data(0, Qt.ItemDataRole.UserRole)
        return None

    def dropEvent(self, event: QDropEvent):
        """ドロップイベント - タスクの順序変更を処理"""
        # 元のドロップ処理を実行
        super().dropEvent(event)

        # 順序変更シグナルを発火
        self.task_order_changed.emit()

    def get_task_order(self) -> List[tuple]:
        """現在のタスク順序を取得 [(task_id, parent_id, sort_order), ...]"""
        order_list = []

        def traverse_items(parent_item, parent_id):
            """アイテムを再帰的に走査して順序を取得"""
            if parent_item is None:
                # ルートレベル
                count = self.topLevelItemCount()
                for i in range(count):
                    item = self.topLevelItem(i)
                    task_id = item.data(0, Qt.ItemDataRole.UserRole)
                    order_list.append((task_id, None, i))
                    # 子アイテムを処理
                    traverse_items(item, task_id)
            else:
                # 子レベル
                count = parent_item.childCount()
                for i in range(count):
                    item = parent_item.child(i)
                    task_id = item.data(0, Qt.ItemDataRole.UserRole)
                    order_list.append((task_id, parent_id, i))
                    # 子アイテムを処理
                    traverse_items(item, task_id)

        traverse_items(None, None)
        return order_list
