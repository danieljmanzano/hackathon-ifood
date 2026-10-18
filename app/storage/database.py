from contextlib import contextmanager
from pathlib import Path
import sqlite3

from app.schemas.macro import ConsumptionRecord, FoodDiaryEntry, Session
from app.schemas.reviews import ProcessedReview, Review, UserTastes


class Database:
    """Instância local de persistência SQLite. Serializa transições de estado via transações."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS reviews ("
                "user_id TEXT NOT NULL, simulated INTEGER NOT NULL, merchant_id TEXT NOT NULL, "
                "item_id TEXT NOT NULL, payload TEXT NOT NULL, "
                "PRIMARY KEY(user_id, simulated, merchant_id, item_id))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS processed_reviews ("
                "simulated INTEGER NOT NULL, fingerprint TEXT NOT NULL, payload TEXT NOT NULL, "
                "PRIMARY KEY(simulated, fingerprint))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS user_tastes ("
                "user_id TEXT NOT NULL, simulated INTEGER NOT NULL, payload TEXT NOT NULL, "
                "PRIMARY KEY(user_id, simulated))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS food_diary (user_id TEXT NOT NULL, id TEXT NOT NULL, "
                "payload TEXT NOT NULL, PRIMARY KEY(user_id, id))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS consumption (user_id TEXT NOT NULL, order_id TEXT NOT NULL, "
                "item_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(user_id, order_id, item_id))"
            )

    def food_entries(self, user_id: str) -> list[FoodDiaryEntry]:
        with self.transaction() as connection:
            rows = connection.execute("SELECT payload FROM food_diary WHERE user_id = ?", (user_id,)).fetchall()
        return [FoodDiaryEntry.model_validate_json(row[0]) for row in rows]

    def save_food_entry(self, user_id: str, entry: FoodDiaryEntry):
        with self.transaction() as connection:
            connection.execute("INSERT INTO food_diary VALUES (?, ?, ?) ON CONFLICT(user_id, id) "
                               "DO UPDATE SET payload=excluded.payload", (user_id, entry.id, entry.model_dump_json()))

    def delete_food_entry(self, user_id: str, entry_id: str):
        with self.transaction() as connection:
            connection.execute("DELETE FROM food_diary WHERE user_id = ? AND id = ?", (user_id, entry_id))

    def consumption(self, user_id: str) -> list[ConsumptionRecord]:
        with self.transaction() as connection:
            rows = connection.execute("SELECT payload FROM consumption WHERE user_id = ?", (user_id,)).fetchall()
        return [ConsumptionRecord.model_validate_json(row[0]) for row in rows]

    def replace_consumption(self, user_id: str, entries: list[ConsumptionRecord]):
        with self.transaction() as connection:
            connection.execute("DELETE FROM consumption WHERE user_id = ?", (user_id,))
            connection.executemany("INSERT INTO consumption VALUES (?, ?, ?, ?)",
                                   [(user_id, e.order_id, e.item_id, e.model_dump_json()) for e in entries])

    def processed_reviews(self, simulated: bool) -> dict[str, ProcessedReview]:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT fingerprint, payload FROM processed_reviews WHERE simulated = ?", (simulated,)
            ).fetchall()
        return {key: ProcessedReview.model_validate_json(payload) for key, payload in rows}

    def save_processed_reviews(self, reviews: list[ProcessedReview], simulated: bool):
        if not reviews:
            return
        with self.transaction() as connection:
            connection.executemany(
                "INSERT OR REPLACE INTO processed_reviews VALUES (?, ?, ?)",
                [(simulated, r.fingerprint, r.model_dump_json()) for r in reviews],
            )

    def get_tastes(self, user_id: str, simulated: bool) -> UserTastes | None:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT payload FROM user_tastes WHERE user_id = ? AND simulated = ?", (user_id, simulated)
            ).fetchone()
        return UserTastes.model_validate_json(row[0]) if row else None

    def save_tastes(self, tastes: UserTastes):
        with self.transaction() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO user_tastes VALUES (?, ?, ?)",
                (tastes.user_id, tastes.simulated, tastes.model_dump_json()),
            )

    def reviews(self, simulated: bool) -> list[Review]:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT payload FROM reviews WHERE simulated = ? ORDER BY rowid", (simulated,)
            ).fetchall()
        return [Review.model_validate_json(row[0]) for row in rows]

    def save_review(self, review: Review):
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO reviews VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(user_id, simulated, merchant_id, item_id) "
                "DO UPDATE SET payload=excluded.payload",
                (review.user_id, review.simulated, review.merchant_id, review.item_id,
                 review.model_dump_json()),
            )

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
        row = connection.execute(
            "SELECT payload FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return Session.model_validate_json(row[0]) if row else None

    def save(self, session: Session, connection=None):
        if connection is None:
            with self.transaction() as connection:
                self.save(session, connection)
            return
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
            (session.id, session.model_dump_json()),
        )
