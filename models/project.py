from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Project:
    """プロジェクトモデル"""
    id: Optional[int]
    name: str
    description: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row):
        """データベース行からインスタンス生成"""
        return cls(
            id=row['id'],
            name=row['name'],
            description=row['description'] or "",
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
