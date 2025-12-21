from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsRectItem,
                               QGraphicsTextItem, QGraphicsLineItem, QMenu)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QDate
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QAction, QCursor
from typing import List, Dict, Optional
from datetime import date, timedelta
from models import Task, TaskDependency


class GanttChartWidget(QGraphicsView):
    """ガントチャート描画ウィジェット"""

    task_clicked = Signal(int)  # タスクID
    task_date_changed = Signal(int, str, str)  # task_id, start_date, end_date
    task_edit_requested = Signal(int)  # タスクID
    task_delete_requested = Signal(int)  # タスクID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.tasks: List[Task] = []
        self.dependencies: List[TaskDependency] = []
        self.task_bars: Dict[int, QGraphicsRectItem] = {}  # task_id -> bar

        # 設定
        self.row_height = 50
        self.day_width = 40
        self.left_margin = 20
        self.top_margin = 35
        self.min_date: Optional[date] = None
        self.max_date: Optional[date] = None

        # ドラッグ中のアイテム
        self.dragging_item: Optional[QGraphicsRectItem] = None
        self.drag_start_pos: Optional[QPointF] = None
        self.drag_mode: str = None  # 'move', 'resize_left', 'resize_right'
        self.resize_edge_margin = 10  # リサイズ可能な端のマージン
        self.original_task_dates = None  # ドラッグ開始時のタスク日付を保存
        self.has_moved = False  # マウスが実際に移動したかを追跡

        self.setup_ui()

    def setup_ui(self):
        """UI初期化"""
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)  # 手動でドラッグ処理

        # 背景色を設定
        self.setBackgroundBrush(QBrush(QColor(250, 250, 250)))

        # 右クリックメニュー
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def load_tasks(self, tasks: List[Task], dependencies: List[TaskDependency] = None):
        """タスクをガントチャートに読み込み"""
        self.tasks = tasks
        self.dependencies = dependencies or []
        self.task_bars.clear()

        if not tasks:
            self.scene.clear()
            return

        # 日付範囲を計算
        self.calculate_date_range()

        # シーンをクリアして再描画
        self.scene.clear()
        self.draw_chart()

    def calculate_date_range(self):
        """日付範囲を計算"""
        if not self.tasks:
            return

        dates = []
        for task in self.tasks:
            dates.append(task.start_date)
            dates.append(task.end_date)

        self.min_date = min(dates)
        self.max_date = max(dates)

        # 余白を追加
        self.min_date -= timedelta(days=3)
        self.max_date += timedelta(days=3)

    def draw_chart(self):
        """チャート全体を描画"""
        if not self.tasks or not self.min_date:
            return

        # 背景とグリッド
        self.draw_background()

        # タスクバー
        row = 0
        task_rows = {}
        for task in self._flatten_tasks(self.tasks):
            task_rows[task.id] = row
            self.draw_task_bar(task, row)
            row += 1

        # 依存関係の矢印
        for dep in self.dependencies:
            if dep.predecessor_id in task_rows and dep.successor_id in task_rows:
                self.draw_dependency_arrow(
                    dep.predecessor_id,
                    dep.successor_id,
                    task_rows
                )

        # シーンサイズを調整（最小サイズを設定）
        total_days = (self.max_date - self.min_date).days
        scene_width = max(self.left_margin + total_days * self.day_width + 100, 2000)
        scene_height = max(self.top_margin + row * self.row_height + 100, 1000)
        self.scene.setSceneRect(0, 0, scene_width, scene_height)

    def _flatten_tasks(self, tasks: List[Task]) -> List[Task]:
        """タスクツリーをフラット化"""
        result = []
        for task in tasks:
            result.append(task)
            if task.children:
                result.extend(self._flatten_tasks(task.children))
        return result

    def draw_background(self):
        """背景とグリッドを描画"""
        if not self.min_date:
            return

        # 日付ヘッダー
        current_date = self.min_date
        x = self.left_margin

        while current_date <= self.max_date:
            # 日付テキスト
            text = QGraphicsTextItem(current_date.strftime("%m/%d"))
            text.setPos(x, 5)
            text.setDefaultTextColor(QColor(100, 100, 100))
            font = text.font()
            font.setPointSize(10)
            text.setFont(font)
            self.scene.addItem(text)

            # グリッド線
            line = QGraphicsLineItem(x, self.top_margin, x, self.top_margin + 1000)
            line.setPen(QPen(QColor(230, 230, 230), 1))
            line.setOpacity(0.5)
            self.scene.addItem(line)

            # 週末を強調
            if current_date.weekday() >= 5:  # 土日
                rect = QGraphicsRectItem(x, self.top_margin, self.day_width, 1000)
                rect.setBrush(QBrush(QColor(245, 245, 250)))
                rect.setPen(QPen(Qt.PenStyle.NoPen))
                rect.setOpacity(0.5)
                self.scene.addItem(rect)

            current_date += timedelta(days=1)
            x += self.day_width

    def draw_task_bar(self, task: Task, row: int):
        """タスクバーを描画"""
        # 位置計算
        start_x = self.left_margin + (task.start_date - self.min_date).days * self.day_width
        y = self.top_margin + row * self.row_height + 5
        width = task.duration_days * self.day_width
        height = self.row_height - 10

        # バーの色（カスタム色または進捗率に応じた色）
        if task.color:
            # カスタム色が設定されている場合はそれを使用
            color = QColor(task.color)
        elif task.is_milestone:
            # マイルストーン: 赤系
            color = QColor(244, 67, 54)  # Material Red
        else:
            # 進捗率に応じた色
            if task.progress == 100:
                color = QColor(76, 175, 80)  # Material Green
            elif task.progress > 0:
                color = QColor(33, 150, 243)  # Material Blue
            else:
                color = QColor(158, 158, 158)  # Material Grey

        # タスクバー
        bar = QGraphicsRectItem(start_x, y, width, height)
        bar.setBrush(QBrush(color))
        bar.setPen(QPen(Qt.PenStyle.NoPen))  # 枠線なし
        bar.setData(0, task.id)  # タスクIDを保存
        bar.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, False)
        bar.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.scene.addItem(bar)
        self.task_bars[task.id] = bar

        # 進捗バー
        if task.progress > 0 and not task.is_milestone:
            progress_width = width * (task.progress / 100)
            progress_bar = QGraphicsRectItem(start_x, y, progress_width, height)
            # 進捗バーは少し暗い色
            darker_color = color.darker(120)
            progress_bar.setBrush(QBrush(darker_color))
            progress_bar.setPen(QPen(Qt.PenStyle.NoPen))
            progress_bar.setOpacity(0.7)
            self.scene.addItem(progress_bar)

        # タスク名
        text = QGraphicsTextItem(task.name)
        text.setPos(start_x + 5, y + 5)
        text.setDefaultTextColor(QColor(255, 255, 255))
        font = text.font()
        font.setPointSize(10)
        font.setBold(True)
        text.setFont(font)
        self.scene.addItem(text)

        # 進捗率テキスト
        if task.progress > 0:
            progress_text = QGraphicsTextItem(f"{task.progress}%")
            progress_text.setPos(start_x + width + 5, y + 5)
            progress_text.setDefaultTextColor(QColor(100, 100, 100))
            font = progress_text.font()
            font.setPointSize(9)
            progress_text.setFont(font)
            self.scene.addItem(progress_text)

    def draw_dependency_arrow(self, predecessor_id: int, successor_id: int, task_rows: Dict[int, int]):
        """依存関係の矢印を描画"""
        if predecessor_id not in self.task_bars or successor_id not in self.task_bars:
            return

        pred_bar = self.task_bars[predecessor_id]
        succ_bar = self.task_bars[successor_id]

        # 矢印の開始点と終了点
        start_x = pred_bar.rect().right()
        start_y = pred_bar.rect().center().y()
        end_x = succ_bar.rect().left()
        end_y = succ_bar.rect().center().y()

        # 線を描画（モダンなスタイル）
        pen = QPen(QColor(156, 39, 176), 2)  # Material Purple
        pen.setStyle(Qt.PenStyle.DashLine)

        # 矢印（簡易的に直線）
        line = QGraphicsLineItem(start_x, start_y, end_x, end_y)
        line.setPen(pen)
        line.setOpacity(0.6)
        self.scene.addItem(line)

    def mousePressEvent(self, event):
        """マウスプレス"""
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            item = self.scene.itemAt(scene_pos, self.transform())

            if item and isinstance(item, QGraphicsRectItem):
                task_id = item.data(0)
                if task_id:
                    self.task_clicked.emit(task_id)

                    # ドラッグモード判定
                    rect = item.rect()
                    local_x = scene_pos.x() - rect.x()

                    if local_x < self.resize_edge_margin:
                        # 左端リサイズ
                        self.drag_mode = 'resize_left'
                        self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
                    elif local_x > rect.width() - self.resize_edge_margin:
                        # 右端リサイズ
                        self.drag_mode = 'resize_right'
                        self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
                    else:
                        # 移動
                        self.drag_mode = 'move'
                        self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

                    self.dragging_item = item
                    self.drag_start_pos = scene_pos
                    self.has_moved = False  # リセット

                    # 元のタスク日付を保存
                    task = next((t for t in self._flatten_tasks(self.tasks) if t.id == task_id), None)
                    if task:
                        self.original_task_dates = (task.start_date, task.end_date)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """マウス移動"""
        scene_pos = self.mapToScene(event.pos())

        if self.dragging_item and self.drag_start_pos and self.original_task_dates:
            delta_x = scene_pos.x() - self.drag_start_pos.x()

            # 少しでも動いたらフラグを立てる（3ピクセル以上の移動）
            if abs(delta_x) > 3:
                self.has_moved = True

            # バーの位置を視覚的に更新（スムーズ）
            rect = self.dragging_item.rect()

            if self.drag_mode == 'move':
                # タスク全体を移動
                new_x = rect.x() + delta_x
                self.dragging_item.setRect(new_x, rect.y(), rect.width(), rect.height())
                self.drag_start_pos = scene_pos

            elif self.drag_mode == 'resize_left':
                # 左端をリサイズ
                new_x = rect.x() + delta_x
                new_width = rect.width() - delta_x
                if new_width > self.day_width:  # 最小1日
                    self.dragging_item.setRect(new_x, rect.y(), new_width, rect.height())
                    self.drag_start_pos = scene_pos

            elif self.drag_mode == 'resize_right':
                # 右端をリサイズ
                new_width = rect.width() + delta_x
                if new_width > self.day_width:  # 最小1日
                    self.dragging_item.setRect(rect.x(), rect.y(), new_width, rect.height())
                    self.drag_start_pos = scene_pos
        else:
            # ホバー時のカーソル変更
            item = self.scene.itemAt(scene_pos, self.transform())
            if item and isinstance(item, QGraphicsRectItem) and item.data(0):
                rect = item.rect()
                local_x = scene_pos.x() - rect.x()

                if local_x < self.resize_edge_margin or local_x > rect.width() - self.resize_edge_margin:
                    self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
                else:
                    self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """マウスリリース"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 実際にドラッグした場合のみ更新
            if self.dragging_item and self.original_task_dates and self.has_moved:
                task_id = self.dragging_item.data(0)
                if task_id:
                    # 最終的なバーの位置から日付を計算
                    rect = self.dragging_item.rect()
                    start_days = round((rect.x() - self.left_margin) / self.day_width)
                    end_days = round((rect.x() + rect.width() - self.left_margin) / self.day_width)

                    new_start = self.min_date + timedelta(days=start_days)
                    new_end = self.min_date + timedelta(days=end_days)

                    # 元の日付と異なる場合のみ更新
                    if new_start != self.original_task_dates[0] or new_end != self.original_task_dates[1]:
                        self.task_date_changed.emit(task_id, str(new_start), str(new_end))

            self.dragging_item = None
            self.drag_start_pos = None
            self.drag_mode = None
            self.original_task_dates = None
            self.has_moved = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        super().mouseReleaseEvent(event)

    def show_context_menu(self, position):
        """右クリックメニュー表示"""
        scene_pos = self.mapToScene(position)
        item = self.scene.itemAt(scene_pos, self.transform())

        if item and isinstance(item, QGraphicsRectItem):
            task_id = item.data(0)
            if task_id:
                menu = QMenu(self)

                # 編集
                edit_action = QAction("編集", self)
                edit_action.triggered.connect(lambda: self.task_edit_requested.emit(task_id))
                menu.addAction(edit_action)

                # 削除
                delete_action = QAction("削除", self)
                delete_action.triggered.connect(lambda: self.task_delete_requested.emit(task_id))
                menu.addAction(delete_action)

                menu.exec(self.mapToGlobal(position))

    def get_visible_tasks(self) -> List[Task]:
        """表示中のタスクを取得"""
        return self._flatten_tasks(self.tasks)
