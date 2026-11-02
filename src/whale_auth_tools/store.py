"""Small SQLite persistence layer for questionnaire responses."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import UUID, uuid4

from whale_auth_tools.models import QuestionnaireSubmission, StoredSubmission, SubmissionAccepted


class QuestionnaireStore:
    """Persistence for a single-replica deployment.

    Connections are short-lived so request threads do not share SQLite handles.
    WAL mode permits safe concurrent reads while an insert is committed.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def initialise(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS questionnaire_submissions (
                    id TEXT PRIMARY KEY,
                    submitted_at TEXT NOT NULL,
                    response_json TEXT NOT NULL
                )
                """
            )

    def create(self, submission: QuestionnaireSubmission) -> SubmissionAccepted:
        submission_id = uuid4()
        submitted_at = datetime.now(timezone.utc)
        response = submission.model_dump(
            by_alias=True, exclude={"altcha_payload"}, mode="json"
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO questionnaire_submissions (id, submitted_at, response_json)
                VALUES (?, ?, ?)
                """,
                (
                    str(submission_id),
                    submitted_at.isoformat(),
                    json.dumps(response, separators=(",", ":")),
                ),
            )
        return SubmissionAccepted(id=submission_id, submittedAt=submitted_at)

    def list(self, limit: int) -> list[StoredSubmission]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, submitted_at, response_json
                FROM questionnaire_submissions
                ORDER BY submitted_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_submission(row) for row in rows]

    def delete(self, submission_id: UUID) -> bool:
        with self._connect() as connection:
            deleted = connection.execute(
                "DELETE FROM questionnaire_submissions WHERE id = ?", (str(submission_id),)
            ).rowcount
        return deleted == 1

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path, timeout=10)

    @staticmethod
    def _row_to_submission(row: tuple[str, str, str]) -> StoredSubmission:
        response = json.loads(row[2])
        return StoredSubmission(
            id=UUID(row[0]),
            submittedAt=datetime.fromisoformat(row[1]),
            **response,
        )
