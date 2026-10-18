from contextlib import contextmanager
from pathlib import Path
import sqlite3

from ..schemas import Session


class Database:
    """One local app instance. Transactions serialize state transitions across workers."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    @contextmanager
    def transaction(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, session_id: str, connection=None) -> Session | None:
        if connection is None:
            with self.transaction() as connection:
                return self.get(session_id, connection)
        row = connection.execute("SELECT payload FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return Session.model_validate_json(row[0]) if row else None

    def save(self, session: Session, connection=None):
        if connection is None:
            with self.transaction() as connection:
                self.save(session, connection)
            return
        connection.execute("INSERT INTO sessions VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                           (session.id, session.model_dump_json()))
