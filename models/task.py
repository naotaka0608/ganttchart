from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List


@dataclass
class Task:
    """タスクモデル"""
    id: Optional[int]
    project_id: int
    name: str
    start_date: date
    end_date: date
    parent_id: Optional[int] = None
    description: str = ""
    progress: int = 0
    is_milestone: bool = False
    is_expanded: bool = True
    sort_order: int = 0
    color: Optional[str] = None
    assignee: Optional[str] = None
    baseline_start_date: Optional[date] = None
    baseline_end_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # UI用（データベースには保存しない）
    children: List['Task'] = field(default_factory=list)

    @classmethod
    def from_db_row(cls, row):
        """データベース行からインスタンス生成"""
        # sqlite3.Rowの列名をチェック（オプション列の安全な読み込み）
        color = None
        assignee = None
        baseline_start_date = None
        baseline_end_date = None

        try:
            color = row['color']
        except (KeyError, IndexError):
            pass  # color列が存在しない場合はNoneのまま

        try:
            assignee = row['assignee']
        except (KeyError, IndexError):
            pass  # assignee列が存在しない場合はNoneのまま

        try:
            if row['baseline_start_date']:
                baseline_start_date = date.fromisoformat(row['baseline_start_date'])
        except (KeyError, IndexError):
            pass  # baseline_start_date列が存在しない場合はNoneのまま

        try:
            if row['baseline_end_date']:
                baseline_end_date = date.fromisoformat(row['baseline_end_date'])
        except (KeyError, IndexError):
            pass  # baseline_end_date列が存在しない場合はNoneのまま

        return cls(
            id=row['id'],
            project_id=row['project_id'],
            parent_id=row['parent_id'],
            name=row['name'],
            description=row['description'] or "",
            start_date=date.fromisoformat(row['start_date']),
            end_date=date.fromisoformat(row['end_date']),
            progress=row['progress'],
            is_milestone=bool(row['is_milestone']),
            is_expanded=bool(row['is_expanded']),
            sort_order=row['sort_order'],
            color=color,
            assignee=assignee,
            baseline_start_date=baseline_start_date,
            baseline_end_date=baseline_end_date,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )

    @property
    def duration_days(self) -> int:
        """タスクの期間（日数）"""
        return (self.end_date - self.start_date).days + 1

    @property
    def has_baseline(self) -> bool:
        """ベースラインが設定されているか"""
        return self.baseline_start_date is not None and self.baseline_end_date is not None

    @property
    def start_variance_days(self) -> int:
        """開始日の差分（日数）正の値=遅延、負の値=前倒し"""
        if not self.has_baseline:
            return 0
        return (self.start_date - self.baseline_start_date).days

    @property
    def end_variance_days(self) -> int:
        """終了日の差分（日数）正の値=遅延、負の値=前倒し"""
        if not self.has_baseline:
            return 0
        return (self.end_date - self.baseline_end_date).days

    def add_child(self, child: 'Task'):
        """子タスクを追加"""
        self.children.append(child)

    def sort_children(self):
        """子タスクをsort_orderでソートし、再帰的に孫タスクもソート"""
        self.children.sort(key=lambda t: t.sort_order)
        for child in self.children:
            child.sort_children()


@dataclass
class TaskDependency:
    """タスク依存関係モデル"""
    id: Optional[int]
    predecessor_id: int
    successor_id: int
    dependency_type: str = "FS"  # FS, SS, FF, SF

    @classmethod
    def from_db_row(cls, row):
        """データベース行からインスタンス生成"""
        return cls(
            id=row['id'],
            predecessor_id=row['predecessor_id'],
            successor_id=row['successor_id'],
            dependency_type=row['dependency_type']
        )
