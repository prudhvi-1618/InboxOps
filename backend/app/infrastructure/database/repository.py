import aiosqlite
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailDecisionRepository:

    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def get_by_email_id(self, email_id: str) -> Optional[dict]:
        async with self.db.execute(
            "SELECT * FROM email_decisions WHERE email_id = ?", (email_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_task_id_by_thread(self, thread_id: str) -> Optional[str]:
        """Returns the task_id for the first created task in a thread, or None."""
        async with self.db.execute(
            """SELECT task_id FROM email_decisions
               WHERE thread_id = ? AND decision = 'task_created'
               ORDER BY processed_at ASC LIMIT 1""",
            (thread_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["task_id"] if row else None

    async def insert_decision(self, data: dict) -> None:
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        await self.db.execute(
            f"INSERT OR IGNORE INTO email_decisions ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        await self.db.commit()

    async def get_stats(self) -> dict:
        async with self.db.execute("""
            SELECT
                COUNT(*) as processed,
                SUM(CASE WHEN decision='task_created' THEN 1 ELSE 0 END) as created,
                SUM(CASE WHEN decision='task_updated' THEN 1 ELSE 0 END) as updated,
                SUM(CASE WHEN decision='skipped'      THEN 1 ELSE 0 END) as skipped,
                SUM(CASE WHEN decision='error'        THEN 1 ELSE 0 END) as errors
            FROM email_decisions
        """) as cursor:
            row = await cursor.fetchone()
            totals = dict(row) if row else {}

        async with self.db.execute("""
            SELECT category, COUNT(*) as count
            FROM email_decisions
            WHERE decision IN ('task_created','task_updated')
            GROUP BY category
        """) as cursor:
            by_category = [dict(r) for r in await cursor.fetchall()]

        async with self.db.execute("""
            SELECT skipped_reason, COUNT(*) as count
            FROM email_decisions
            WHERE decision = 'skipped'
            GROUP BY skipped_reason
        """) as cursor:
            skip_reasons = [dict(r) for r in await cursor.fetchall()]

        async with self.db.execute("""
            SELECT spam_lookalike_category, COUNT(*) as count
            FROM email_decisions
            WHERE decision = 'skipped' AND spam_lookalike_category IS NOT NULL
            GROUP BY spam_lookalike_category
        """) as cursor:
            spam_lookalikes = [dict(r) for r in await cursor.fetchall()]

        return {
            "totals": totals,
            "by_category": by_category,
            "skip_reasons": skip_reasons,
            "spam_lookalikes": spam_lookalikes,
        }

    async def get_all_for_chat(self) -> list[dict]:
        """Returns full decision log for chat grounding queries."""
        async with self.db.execute(
            "SELECT * FROM email_decisions ORDER BY processed_at DESC"
        ) as cursor:
            return [dict(r) for r in await cursor.fetchall()]

    async def get_thread_update_count(self, thread_id: str) -> int:
        async with self.db.execute(
            "SELECT COUNT(*) as cnt FROM thread_updates WHERE thread_id = ?",
            (thread_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def insert_thread_update(self, thread_id: str, email_id: str, task_id: str, action: str) -> None:
        await self.db.execute(
            "INSERT INTO thread_updates (thread_id, email_id, task_id, action) VALUES (?,?,?,?)",
            (thread_id, email_id, task_id, action),
        )
        await self.db.commit()

    async def get_threads_updated_multiple_times(self) -> list[str]:
        async with self.db.execute("""
            SELECT thread_id FROM thread_updates
            GROUP BY thread_id HAVING COUNT(*) > 1
        """) as cursor:
            return [r["thread_id"] for r in await cursor.fetchall()]

    # ----------------- Tasks CRUD -----------------
    async def create_task(self, data: dict) -> dict:
        task_id = data.get("task_id") or f"tsk_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "task_id": task_id,
            "candidate_id": data["candidate_id"],
            "source_email_id": data["source_email_id"],
            "thread_id": data["thread_id"],
            "title": data["title"],
            "description": data.get("description"),
            "assignee_id": data["assignee_id"],
            "category": data["category"],
            "priority": data["priority"],
            "due_date": data.get("due_date"),
            "deal_value_inr": data.get("deal_value_inr"),
            "company_name": data.get("company_name"),
            "confidence": data.get("confidence", 0.5),
            "created_at": now,
            "updated_at": None,
        }
        cols = ", ".join(record.keys())
        placeholders = ", ".join("?" * len(record))
        await self.db.execute(
            f"INSERT INTO tasks ({cols}) VALUES ({placeholders})",
            list(record.values()),
        )
        await self.db.commit()
        return record

    async def update_task(self, task_id: str, patch_data: dict) -> Optional[dict]:
        existing = await self.get_task(task_id)
        if not existing:
            return None

        clean_patch = {k: v for k, v in patch_data.items() if v is not None}
        if not clean_patch:
            return existing

        clean_patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clauses = ", ".join([f"{k} = ?" for k in clean_patch.keys()])
        values = list(clean_patch.values()) + [task_id]

        await self.db.execute(
            f"UPDATE tasks SET {set_clauses} WHERE task_id = ?",
            values,
        )
        await self.db.commit()
        return await self.get_task(task_id)

    async def get_task(self, task_id: str) -> Optional[dict]:
        async with self.db.execute(
            "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_tasks(self, filters: Optional[dict] = None) -> list[dict]:
        query = "SELECT * FROM tasks"
        params = []
        if filters:
            clauses = []
            for k, v in filters.items():
                if v is not None:
                    clauses.append(f"{k} = ?")
                    params.append(v)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"

        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
