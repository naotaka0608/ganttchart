from PySide6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsRectItem,
                               QGraphicsTextItem, QGraphicsLineItem, QMenu)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QDate, QTimer
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QAction, QCursor
from typing import List, Dict, Optional
from datetime import date, timedelta
from models import Task, TaskDependency


class GanttChartWidget(QGraphicsView):
    """ガントチャート描画ウィジェット"""

    task_clicked = Signal(int)  # タスクID
    task_date_changed = Signal(int, str, str)  # task_id, start_date, end_date
    task_progress_changed = Signal(int, int)  # task_id, progress
    task_edit_requested = Signal(int)  # タスクID
    task_delete_requested = Signal(int)  # タスクID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.tasks: List[Task] = []
        self.dependencies: List[TaskDependency] = []
        self.task_bars: Dict[int, QGraphicsRectItem] = {}  # task_id -> bar
        self.progress_bars: Dict[int, QGraphicsRectItem] = {}  # task_id -> progress_bar

        # 表示モード: 'day', 'week', 'month'
        self.view_mode = 'day'

        # 設定
        self.row_height = 50
        self.day_width = 40
        self.left_margin = 20
        self.top_margin = 70  # 日付ヘッダー用に余白を増やす
        self.min_date: Optional[date] = None
        self.max_date: Optional[date] = None

        # ドラッグ中のアイテム
        self.dragging_item: Optional[QGraphicsRectItem] = None
        self.drag_start_pos: Optional[QPointF] = None
        self.drag_mode: str = None  # 'move', 'resize_left', 'resize_right', 'progress'
        self.resize_edge_margin = 10  # リサイズ可能な端のマージン
        self.original_task_dates = None  # ドラッグ開始時のタスク日付を保存
        self.original_progress = None  # ドラッグ開始時の進捗率を保存
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

    def set_view_mode(self, mode: str):
        """表示モードを設定 ('day', 'week', 'month')"""
        if mode not in ['day', 'week', 'month']:
            return

        self.view_mode = mode

        # モードに応じて幅を調整
        if mode == 'day':
            self.day_width = 40
        elif mode == 'week':
            self.day_width = 30
        elif mode == 'month':
            self.day_width = 10

        # 再描画
        if self.tasks:
            self.scene.clear()
            self.draw_chart()

    def load_tasks(self, tasks: List[Task], dependencies: List[TaskDependency] = None, scroll_to_today: bool = False):
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

        # 必要に応じて今日の位置にスクロール
        if scroll_to_today:
            QTimer.singleShot(10, self.scroll_to_today)

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

    def scroll_to_today(self):
        """今日の日付にスクロール"""
        if not self.min_date or not self.max_date:
            return

        today = date.today()

        # 今日が表示範囲内にあるかチェック
        if today < self.min_date or today > self.max_date:
            return

        # 今日の位置を計算
        days_from_start = (today - self.min_date).days
        x_position = self.left_margin + days_from_start * self.day_width

        # ビューの中央に今日を配置（ビュー幅の40%の位置に表示）
        view_width = self.viewport().width()
        scroll_x = x_position - view_width * 0.4

        # 水平スクロールバーの位置を設定
        self.horizontalScrollBar().setValue(int(scroll_x))

    def draw_chart(self):
        """チャート全体を描画"""
        if not self.tasks or not self.min_date:
            return

        # 背景とグリッド
        self.draw_background()

        # 今日の線を描画
        self.draw_today_line()

        # タスクバー（既にフラット化されたリストが渡される）
        row = 0
        task_rows = {}
        for task in self.tasks:
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

        if self.view_mode == 'day':
            self._draw_background_day()
        elif self.view_mode == 'week':
            self._draw_background_week()
        elif self.view_mode == 'month':
            self._draw_background_month()

    def _draw_background_day(self):
        """日単位の背景を描画"""
        current_date = self.min_date
        x = self.left_margin
        today = date.today()
        last_month = None

        while current_date <= self.max_date:
            # 年月の表示（月が変わった時のみ）
            current_month = current_date.strftime("%Y年%m月")
            if current_month != last_month:
                month_text = QGraphicsTextItem(current_month)
                month_text.setPos(x, 0)
                month_text.setDefaultTextColor(QColor(80, 80, 80))
                font = month_text.font()
                font.setPointSize(10)
                font.setBold(True)
                month_text.setFont(font)
                self.scene.addItem(month_text)
                last_month = current_month

            # 曜日に応じた色を決定
            day_color = QColor(100, 100, 100)  # デフォルト（平日）
            if current_date.weekday() == 5:  # 土曜日
                day_color = QColor(0, 100, 200)
            elif current_date.weekday() == 6:  # 日曜日
                day_color = QColor(200, 0, 0)

            # 日にち（中央揃え）
            day_text = QGraphicsTextItem(current_date.strftime("%d"))
            day_text.setPos(x + 8, 20)  # 年月との余白を増やす、中央に配置
            day_text.setDefaultTextColor(day_color)
            font = day_text.font()
            font.setPointSize(9)
            day_text.setFont(font)
            self.scene.addItem(day_text)

            # 曜日（日本語・中央揃え）
            weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
            weekday_text = QGraphicsTextItem(weekday_names[current_date.weekday()])
            weekday_text.setPos(x + 9, 35)  # 日にちと揃える
            weekday_text.setDefaultTextColor(day_color)  # 日にちと同じ色
            font = weekday_text.font()
            font.setPointSize(8)
            weekday_text.setFont(font)
            self.scene.addItem(weekday_text)

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

    def _draw_background_week(self):
        """週単位の背景を描画"""
        current_date = self.min_date
        # 週の始まり（月曜日）に調整
        days_to_monday = current_date.weekday()
        current_week_start = current_date - timedelta(days=days_to_monday)
        x = self.left_margin

        while current_week_start <= self.max_date:
            week_end = current_week_start + timedelta(days=6)

            # 週の範囲のテキスト
            text_str = f"{current_week_start.strftime('%m/%d')}-{week_end.strftime('%m/%d')}"
            text = QGraphicsTextItem(text_str)
            text.setPos(x, 5)
            text.setDefaultTextColor(QColor(100, 100, 100))
            font = text.font()
            font.setPointSize(9)
            text.setFont(font)
            self.scene.addItem(text)

            # グリッド線（週ごと）
            line = QGraphicsLineItem(x, self.top_margin, x, self.top_margin + 1000)
            line.setPen(QPen(QColor(200, 200, 200), 2))
            line.setOpacity(0.7)
            self.scene.addItem(line)

            # 日ごとの薄いグリッド線
            for day in range(7):
                day_date = current_week_start + timedelta(days=day)
                if day_date > self.max_date:
                    break
                day_x = x + day * self.day_width

                # 薄いグリッド線
                if day > 0:
                    day_line = QGraphicsLineItem(day_x, self.top_margin, day_x, self.top_margin + 1000)
                    day_line.setPen(QPen(QColor(240, 240, 240), 1))
                    day_line.setOpacity(0.3)
                    self.scene.addItem(day_line)

            current_week_start += timedelta(days=7)
            x += 7 * self.day_width

    def _draw_background_month(self):
        """月単位の背景を描画"""
        current_date = self.min_date
        # 月の始まりに調整
        current_month_start = date(current_date.year, current_date.month, 1)
        x = self.left_margin

        while current_month_start <= self.max_date:
            # 月の最終日を取得
            if current_month_start.month == 12:
                next_month = date(current_month_start.year + 1, 1, 1)
            else:
                next_month = date(current_month_start.year, current_month_start.month + 1, 1)
            month_end = next_month - timedelta(days=1)

            # 月のテキスト
            text_str = current_month_start.strftime("%Y/%m")
            text = QGraphicsTextItem(text_str)
            text.setPos(x, 5)
            text.setDefaultTextColor(QColor(100, 100, 100))
            font = text.font()
            font.setPointSize(10)
            text.setFont(font)
            self.scene.addItem(text)

            # グリッド線（月ごと）
            line = QGraphicsLineItem(x, self.top_margin, x, self.top_margin + 1000)
            line.setPen(QPen(QColor(180, 180, 180), 2))
            line.setOpacity(0.8)
            self.scene.addItem(line)

            # 月の日数
            days_in_month = (month_end - current_month_start).days + 1

            # 週ごとの薄いグリッド線
            week_start = current_month_start
            week_x = x
            while week_start <= month_end:
                if week_start > current_month_start:
                    week_line = QGraphicsLineItem(week_x, self.top_margin, week_x, self.top_margin + 1000)
                    week_line.setPen(QPen(QColor(230, 230, 230), 1))
                    week_line.setOpacity(0.4)
                    self.scene.addItem(week_line)

                week_start += timedelta(days=7)
                week_x += 7 * self.day_width

            # 次の月へ
            current_month_start = next_month
            x += days_in_month * self.day_width

    def draw_today_line(self):
        """今日の日付に縦線を描画"""
        if not self.min_date or not self.max_date:
            return

        today = date.today()

        # 今日が表示範囲内にあるかチェック
        if today < self.min_date or today > self.max_date:
            return

        # 今日の位置を計算
        days_from_start = (today - self.min_date).days
        x = self.left_margin + days_from_start * self.day_width

        # 今日の縦線を描画（赤色、太線）
        line = QGraphicsLineItem(x, 0, x, self.top_margin + 1000)
        line.setPen(QPen(QColor(244, 67, 54), 2))  # Material Red
        line.setOpacity(0.7)
        line.setZValue(100)  # 他の要素より前面に表示
        self.scene.addItem(line)

        # 「今日」のラベルを追加（年月の位置に配置）
        today_label = QGraphicsTextItem("今日")
        today_label.setPos(x - 5, 0)  # 年月と同じ高さ
        today_label.setDefaultTextColor(QColor(244, 67, 54))
        font = today_label.font()
        font.setPointSize(9)
        font.setBold(True)
        today_label.setFont(font)
        today_label.setZValue(100)
        self.scene.addItem(today_label)

    def draw_task_bar(self, task: Task, row: int):
        """タスクバーを描画"""
        # 位置計算
        start_x = self.left_margin + (task.start_date - self.min_date).days * self.day_width
        y = self.top_margin + row * self.row_height * 1.35 + 18
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
            progress_bar.setData(0, task.id)  # タスクIDを保存
            progress_bar.setData(1, "progress")  # 進捗バーであることを示す
            self.scene.addItem(progress_bar)
            self.progress_bars[task.id] = progress_bar

        # ベースラインバー（当初予定）
        if task.has_baseline and not task.is_milestone:
            baseline_start_x = self.left_margin + (task.baseline_start_date - self.min_date).days * self.day_width
            baseline_duration = (task.baseline_end_date - task.baseline_start_date).days + 1
            baseline_width = baseline_duration * self.day_width
            baseline_y = y + height + 2  # タスクバーの下に配置
            baseline_height = 4  # 薄いバー

            # ベースラインバー（薄いグレー）
            baseline_bar = QGraphicsRectItem(baseline_start_x, baseline_y, baseline_width, baseline_height)
            baseline_bar.setBrush(QBrush(QColor(150, 150, 150)))
            baseline_bar.setPen(QPen(Qt.PenStyle.NoPen))
            baseline_bar.setOpacity(0.6)
            self.scene.addItem(baseline_bar)

            # 差分の表示（遅延は赤、前倒しは緑）
            if task.end_variance_days != 0:
                # 終了日の差分を視覚化
                if task.end_variance_days > 0:
                    # 遅延（赤）: ベースライン終了日から現在の終了日まで
                    variance_start_x = baseline_start_x + baseline_width
                    variance_width = task.end_variance_days * self.day_width
                    variance_color = QColor(244, 67, 54, 100)  # 半透明の赤
                else:
                    # 前倒し（緑）: 現在の終了日からベースライン終了日まで
                    variance_start_x = start_x + width
                    variance_width = abs(task.end_variance_days) * self.day_width
                    variance_color = QColor(76, 175, 80, 100)  # 半透明の緑

                variance_bar = QGraphicsRectItem(variance_start_x, baseline_y, variance_width, baseline_height)
                variance_bar.setBrush(QBrush(variance_color))
                variance_bar.setPen(QPen(Qt.PenStyle.NoPen))
                self.scene.addItem(variance_bar)

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
        progress_text_offset = 0
        if task.progress > 0:
            progress_text = QGraphicsTextItem(f"{task.progress}%")
            progress_text.setPos(start_x + width + 5, y + 5)
            progress_text.setDefaultTextColor(QColor(100, 100, 100))
            font = progress_text.font()
            font.setPointSize(9)
            progress_text.setFont(font)
            self.scene.addItem(progress_text)
            progress_text_offset = 50  # 進捗率テキストの幅分オフセット

        # 担当者テキスト
        assignee_text_offset = progress_text_offset
        if task.assignee:
            assignee_text = QGraphicsTextItem(f"[{task.assignee}]")
            assignee_text.setPos(start_x + width + 5 + progress_text_offset, y + 5)
            assignee_text.setDefaultTextColor(QColor(100, 100, 100))
            font = assignee_text.font()
            font.setPointSize(9)
            assignee_text.setFont(font)
            self.scene.addItem(assignee_text)
            assignee_text_offset += 80  # 担当者テキストの幅分オフセット

        # 差分テキスト（遅延・前倒し）
        if task.has_baseline and task.end_variance_days != 0:
            if task.end_variance_days > 0:
                variance_text = QGraphicsTextItem(f"+{task.end_variance_days}日遅延")
                variance_color = QColor(244, 67, 54)  # 赤
            else:
                variance_text = QGraphicsTextItem(f"{task.end_variance_days}日前倒し")
                variance_color = QColor(76, 175, 80)  # 緑

            variance_text.setPos(start_x + width + 5 + assignee_text_offset, y + 5)
            variance_text.setDefaultTextColor(variance_color)
            font = variance_text.font()
            font.setPointSize(9)
            font.setBold(True)
            variance_text.setFont(font)
            self.scene.addItem(variance_text)

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
                item_type = item.data(1)

                if task_id:
                    self.task_clicked.emit(task_id)

                    # 進捗バーをクリックした場合
                    if item_type == "progress":
                        self.drag_mode = 'progress'
                        self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor))
                        self.dragging_item = item
                        self.drag_start_pos = scene_pos
                        self.has_moved = False

                        # 元の進捗率を保存
                        task = next((t for t in self._flatten_tasks(self.tasks) if t.id == task_id), None)
                        if task:
                            self.original_progress = task.progress
                    else:
                        # タスクバーをクリックした場合
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

        if self.dragging_item and self.drag_start_pos and (self.original_task_dates or self.original_progress is not None):
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

            elif self.drag_mode == 'progress':
                # 進捗バーをリサイズ
                task_id = self.dragging_item.data(0)
                task_bar = self.task_bars.get(task_id)
                if task_bar:
                    task_bar_rect = task_bar.rect()
                    # 進捗バーの新しい幅を計算
                    new_progress_x = scene_pos.x()
                    # タスクバーの範囲内に制限
                    if new_progress_x < task_bar_rect.x():
                        new_progress_x = task_bar_rect.x()
                    elif new_progress_x > task_bar_rect.x() + task_bar_rect.width():
                        new_progress_x = task_bar_rect.x() + task_bar_rect.width()

                    new_progress_width = new_progress_x - task_bar_rect.x()
                    self.dragging_item.setRect(task_bar_rect.x(), rect.y(), new_progress_width, rect.height())

                    if abs(delta_x) > 3:
                        self.has_moved = True
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
            if self.dragging_item and self.has_moved:
                task_id = self.dragging_item.data(0)

                if task_id:
                    if self.drag_mode == 'progress' and self.original_progress is not None:
                        # 進捗率の更新
                        task_bar = self.task_bars.get(task_id)
                        if task_bar:
                            task_bar_rect = task_bar.rect()
                            progress_rect = self.dragging_item.rect()

                            # 進捗率を計算（0-100%）
                            new_progress = int((progress_rect.width() / task_bar_rect.width()) * 100)
                            new_progress = max(0, min(100, new_progress))  # 0-100の範囲に制限

                            if new_progress != self.original_progress:
                                self.task_progress_changed.emit(task_id, new_progress)

                    elif self.original_task_dates:
                        # 日付の更新
                        rect = self.dragging_item.rect()
                        start_days = round((rect.x() - self.left_margin) / self.day_width)
                        duration_days = round(rect.width() / self.day_width)

                        new_start = self.min_date + timedelta(days=start_days)
                        # duration_daysは(end - start).days + 1なので、end = start + duration - 1
                        new_end = new_start + timedelta(days=duration_days - 1)

                        # 元の日付と異なる場合のみ更新
                        if new_start != self.original_task_dates[0] or new_end != self.original_task_dates[1]:
                            self.task_date_changed.emit(task_id, str(new_start), str(new_end))

            self.dragging_item = None
            self.drag_start_pos = None
            self.drag_mode = None
            self.original_task_dates = None
            self.original_progress = None
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
