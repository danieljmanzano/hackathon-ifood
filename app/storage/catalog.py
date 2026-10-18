"""Catálogo observado, fila e reservas de uso. Transações suportam reinícios e vários workers."""

import hashlib
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class CatalogStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS observed_products (
                    id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, payload TEXT NOT NULL, seen REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS nutrition_jobs (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
                    attempts INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0,
                    lease REAL NOT NULL DEFAULT 0, reason TEXT NOT NULL DEFAULT '');
                CREATE INDEX IF NOT EXISTS nutrition_jobs_due ON nutrition_jobs(state, next_at);
                CREATE TABLE IF NOT EXISTS nutrition_usage (
                    day TEXT PRIMARY KEY, calls INTEGER NOT NULL DEFAULT 0, products INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS nutrition_product_usage (
                    day TEXT NOT NULL, product TEXT NOT NULL, calls INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(day, product));
                CREATE TABLE IF NOT EXISTS nutrition_search_jobs (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
                    lease REAL NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS synthetic_catalog_reviews (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            """)

    @contextmanager
    def connection(self):
        with sqlite3.connect(self.path, timeout=10) as db:
            db.row_factory = sqlite3.Row
            yield db

    @staticmethod
    def day():
        return datetime.now(timezone.utc).date().isoformat()

    def observe(self, candidate, fingerprint):
        identity = hashlib.sha256(
            f"{candidate.simulated}:{candidate.merchant_id}:{candidate.item_id}".encode()
        ).hexdigest()
        with self.connection() as db:
            previous = db.execute(
                "SELECT fingerprint FROM observed_products WHERE id=?", (identity,)
            ).fetchone()
            if previous and previous["fingerprint"] != fingerprint:
                db.execute(
                    "UPDATE nutrition_jobs SET state='superseded' WHERE id=? AND state!='running'",
                    (previous["fingerprint"],),
                )
            db.execute(
                "INSERT OR REPLACE INTO observed_products VALUES (?, ?, ?, ?)",
                (identity, fingerprint, candidate.model_dump_json(), time.time()),
            )

    def enqueue(self, candidate, fingerprint):
        with self.connection() as db:
            db.execute(
                "INSERT OR IGNORE INTO nutrition_jobs(id,payload) VALUES (?,?)",
                (fingerprint, candidate.model_dump_json()),
            )

    def claim(self, timeout, max_attempts):
        now = time.time()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE nutrition_jobs SET state='queued' WHERE state='running' AND lease < ?",
                (now,),
            )
            row = db.execute(
                "SELECT * FROM nutrition_jobs WHERE state IN ('queued','deferred','error') "
                "AND next_at <= ? AND attempts < ? ORDER BY next_at,rowid LIMIT 1",
                (now, max_attempts),
            ).fetchone()
            if not row:
                return None
            db.execute(
                "UPDATE nutrition_jobs SET state='running', lease=? WHERE id=?",
                (now + timeout + 60, row["id"]),
            )
            return dict(row)

    def finish(self, key, state, reason="", delay=0, attempted=True):
        with self.connection() as db:
            db.execute(
                "UPDATE nutrition_jobs SET state=?,reason=?,next_at=?,lease=0,attempts=attempts+? WHERE id=?",
                (state, reason, time.time() + delay, int(attempted), key),
            )

    def reserve(self, product, max_calls, max_products, per_product):
        """Reserva ANTES do HTTP: erros, retries e fallback também consomem a cota. max_calls/max_products None = sem limite."""
        day = self.day()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO nutrition_usage(day) VALUES (?)", (day,))
            usage = db.execute("SELECT * FROM nutrition_usage WHERE day=?", (day,)).fetchone()
            row = db.execute(
                "SELECT calls FROM nutrition_product_usage WHERE day=? AND product=?",
                (day, product),
            ).fetchone()
            calls = row["calls"] if row else 0
            if (max_calls is not None and usage["calls"] >= max_calls) or (
                max_products is not None and not row and usage["products"] >= max_products
            ):
                return "daily_limit"
            if calls >= per_product:
                return "product_limit"
            db.execute(
                "UPDATE nutrition_usage SET calls=calls+1,products=products+? WHERE day=?",
                (int(row is None), day),
            )
            db.execute(
                "INSERT INTO nutrition_product_usage VALUES (?,?,1) "
                "ON CONFLICT(day,product) DO UPDATE SET calls=calls+1",
                (day, product),
            )
        return None

    def status(self):
        with self.connection() as db:
            usage = db.execute(
                "SELECT calls,products FROM nutrition_usage WHERE day=?", (self.day(),)
            ).fetchone()
            states = {
                r["state"]: r["n"]
                for r in db.execute("SELECT state,count(*) AS n FROM nutrition_jobs GROUP BY state")
            }
            count = db.execute("SELECT count(*) FROM observed_products").fetchone()[0]
            searches = {
                r["state"]: r["n"]
                for r in db.execute(
                    "SELECT state,count(*) AS n FROM nutrition_search_jobs GROUP BY state"
                )
            }
        return {
            "day_utc": self.day(),
            "calls": usage["calls"] if usage else 0,
            "products_processed": usage["products"] if usage else 0,
            "observed_products": count,
            "jobs": states,
            "searches": searches,
        }

    def synthetic_reviews(self, reviews):
        from app.schemas.reviews import Review

        result = []
        with self.connection() as db:
            for review in reviews:
                db.execute(
                    "INSERT OR IGNORE INTO synthetic_catalog_reviews VALUES (?,?)",
                    (review.id, review.model_dump_json()),
                )
                row = db.execute(
                    "SELECT payload FROM synthetic_catalog_reviews WHERE id=?", (review.id,)
                ).fetchone()
                result.append(Review.model_validate_json(row["payload"]))
        return result

    def saved_synthetic_reviews(self, user_id):
        from app.schemas.reviews import Review

        with self.connection() as db:
            rows = db.execute(
                "SELECT payload FROM synthetic_catalog_reviews ORDER BY id"
            ).fetchall()
        reviews = [Review.model_validate_json(r["payload"]) for r in rows]
        return [
            r for r in reviews if r.user_id == user_id or r.user_id.startswith("catalog-demo-user-")
        ]

    def enqueue_search(self, key, payload):
        import json

        with self.connection() as db:
            db.execute(
                "INSERT OR IGNORE INTO nutrition_search_jobs(id,payload) VALUES (?,?)",
                (key, json.dumps(payload, ensure_ascii=False)),
            )

    def claim_search(self, lease_seconds):
        import json

        now = time.time()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM nutrition_search_jobs WHERE state='queued' OR "
                "(state='running' AND lease < ?) ORDER BY rowid LIMIT 1",
                (now,),
            ).fetchone()
            if row is None:
                return None
            db.execute(
                "UPDATE nutrition_search_jobs SET state='running',lease=? WHERE id=?",
                (now + lease_seconds, row["id"]),
            )
        return json.loads(row["payload"])

    def save_search(self, key, payload, done=False, lease_seconds=600):
        import json

        with self.connection() as db:
            db.execute(
                "UPDATE nutrition_search_jobs SET payload=?,state=?,lease=? WHERE id=?",
                (
                    json.dumps(payload, ensure_ascii=False),
                    "done" if done else "running",
                    time.time() + lease_seconds,
                    key,
                ),
            )

    def recover_searches(self):
        # O protótipo executa um único processo da API. Ao reiniciar, os snapshots permitem retomar.
        with self.connection() as db:
            db.execute(
                "UPDATE nutrition_search_jobs SET state='queued',lease=0 WHERE state='running'"
            )
