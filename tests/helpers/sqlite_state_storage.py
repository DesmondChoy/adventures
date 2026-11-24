"""Real SQLite-backed adventure storage repository for behavioral tests.

Executes real SQL against an in-memory SQLite table mirroring Supabase's
`adventures` schema so summary, HTTP, and persistence tests exercise JSON
serialization, reconstruction, and user ownership without mocking internals.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4


class SQLiteAdventureStorage:
    """SQLite drop-in matching the public async StateStorageService contract."""

    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE adventures (
                id TEXT PRIMARY KEY,
                user_id TEXT NULL,
                story_category TEXT NULL,
                lesson_topic TEXT NULL,
                state_data TEXT NOT NULL,
                is_complete INTEGER NOT NULL DEFAULT 0,
                completed_chapter_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    async def store_state(
        self,
        state_data: dict[str, Any],
        adventure_id: str | None = None,
        user_id: UUID | None = None,
        lesson_topic: str | None = None,
        explicit_is_complete: bool | None = None,
        new_adventure_id: str | None = None,
    ) -> str:
        record_id = adventure_id or new_adventure_id or str(uuid4())
        metadata = state_data.get("metadata") or {}
        story_category = metadata.get("story_category")
        topic = lesson_topic or metadata.get("lesson_topic")
        chapters = state_data.get("chapters") or []
        completed_count = len(chapters)
        is_complete = (
            bool(explicit_is_complete)
            if explicit_is_complete is not None
            else any(
                isinstance(ch, dict) and ch.get("chapter_type") == "summary"
                for ch in chapters
            )
        )
        now = datetime.now(timezone.utc).isoformat()
        serialized = json.dumps(state_data)
        user_id_str = str(user_id) if user_id is not None else None

        existing = self._conn.execute(
            "SELECT id, user_id FROM adventures WHERE id = ?", (record_id,)
        ).fetchone()
        if existing is not None:
            if user_id_str is not None and existing["user_id"] != user_id_str:
                raise PermissionError(
                    f"Adventure {record_id} is not owned by user {user_id_str}"
                )
            self._conn.execute(
                """
                UPDATE adventures
                SET state_data = ?, story_category = ?, lesson_topic = ?,
                    is_complete = ?, completed_chapter_count = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    serialized,
                    story_category,
                    topic,
                    int(is_complete),
                    completed_count,
                    now,
                    record_id,
                ),
            )
        else:
            self._conn.execute(
                """
                INSERT INTO adventures (
                    id, user_id, story_category, lesson_topic,
                    state_data, is_complete, completed_chapter_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    user_id_str,
                    story_category,
                    topic,
                    serialized,
                    int(is_complete),
                    completed_count,
                    now,
                ),
            )
        self._conn.commit()
        return record_id

    async def get_adventure_record(self, state_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM adventures WHERE id = ?", (state_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "story_category": row["story_category"],
            "lesson_topic": row["lesson_topic"],
            "state_data": json.loads(row["state_data"]),
            "is_complete": bool(row["is_complete"]),
            "completed_chapter_count": row["completed_chapter_count"],
            "updated_at": row["updated_at"],
        }

    async def get_state(self, state_id: str) -> dict[str, Any] | None:
        record = await self.get_adventure_record(state_id)
        return record["state_data"] if record else None

    async def is_adventure_owned_by_user(
        self, adventure_id: str, user_id: UUID
    ) -> bool:
        record = await self.get_adventure_record(adventure_id)
        return bool(record and record["user_id"] == str(user_id))

    def row_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS count FROM adventures").fetchone()
        return int(row["count"])
