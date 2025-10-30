from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class MemeRepository:
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_schema(self) -> None:
        with self._get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    caption TEXT NOT NULL,
                    image_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_promoted INTEGER NOT NULL DEFAULT 0,
                    is_flagged INTEGER NOT NULL DEFAULT 0,
                    rejection_reason TEXT
                )
                """
            )
            connection.commit()

    def create_meme(self, *, user_id: str, caption: str, image_key: str) -> Dict[str, Any]:
        timestamp = datetime.utcnow().isoformat()
        with self._get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO memes (
                    user_id,
                    caption,
                    image_key,
                    status,
                    created_at,
                    updated_at,
                    is_promoted,
                    is_flagged,
                    rejection_reason
                )
                VALUES (?, ?, ?, 'pending', ?, ?, 0, 0, NULL)
                """,
                (user_id, caption, image_key, timestamp, timestamp),
            )
            connection.commit()
            meme_id = cursor.lastrowid
        return self.get_by_id(meme_id)

    def get_by_id(self, meme_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM memes WHERE id = ?",
                (meme_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_dict(row)

    def list_by_status(self, status: str) -> List[Dict[str, Any]]:
        with self._get_connection() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM memes
                WHERE status = ?
                ORDER BY created_at ASC
                """,
                (status,),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def approve_meme(self, meme_id: int) -> Optional[Dict[str, Any]]:
        timestamp = datetime.utcnow().isoformat()
        with self._get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE memes
                SET status = 'approved',
                    is_promoted = 1,
                    is_flagged = 0,
                    rejection_reason = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (timestamp, meme_id),
            )
            if cursor.rowcount == 0:
                return None
            connection.commit()
        return self.get_by_id(meme_id)

    def reject_meme(self, meme_id: int, *, reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
        timestamp = datetime.utcnow().isoformat()
        with self._get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE memes
                SET status = 'rejected',
                    is_promoted = 0,
                    is_flagged = 1,
                    rejection_reason = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (reason, timestamp, meme_id),
            )
            if cursor.rowcount == 0:
                return None
            connection.commit()
        return self.get_by_id(meme_id)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "caption": row["caption"],
            "image_key": row["image_key"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_promoted": bool(row["is_promoted"]),
            "is_flagged": bool(row["is_flagged"]),
            "rejection_reason": row["rejection_reason"],
        }
