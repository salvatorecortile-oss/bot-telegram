"""
Database SQLite del bot notizie (file data/news.db).

- items:   ogni notizia letta da una fonte (serve a non inviarla due volte)
- stories: gruppi di notizie uguali riportate da fonti diverse
- meta:    piccole informazioni (es. data dell'ultimo buongiorno inviato)
"""
import sqlite3
import time

from config import DB_PATH

AI_COLUMNS = {
    "ai_score": "INTEGER",      # voto di Claude 1-10 (NULL = non ancora valutata)
    "ai_category": "TEXT",
    "ai_title": "TEXT",
    "ai_text": "TEXT",
    "ai_impact": "TEXT",
    "ai_duplicate": "INTEGER",
}


class Storage:
    def __init__(self, path=DB_PATH):
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_seen REAL NOT NULL,
                last_seen REAL NOT NULL,
                sent_at REAL
            );
            CREATE TABLE IF NOT EXISTS items (
                uid TEXT PRIMARY KEY,
                story_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                link TEXT,
                source TEXT,
                tier INTEGER,
                category TEXT,
                base_score INTEGER,
                published REAL,
                seen REAL
            );
            CREATE INDEX IF NOT EXISTS idx_items_seen ON items(seen);
            CREATE INDEX IF NOT EXISTS idx_items_story ON items(story_id);
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        # Colonne aggiunte per Claude (anche su database già esistenti).
        existing = {row["name"] for row in self.db.execute("PRAGMA table_info(stories)")}
        for column, kind in AI_COLUMNS.items():
            if column not in existing:
                self.db.execute(f"ALTER TABLE stories ADD COLUMN {column} {kind}")
        self.db.commit()

    # ---------- meta ----------
    def get_meta(self, key, default=None):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_meta(self, key, value):
        self.db.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.db.commit()

    # ---------- notizie ----------
    def has_item(self, uid):
        return self.db.execute("SELECT 1 FROM items WHERE uid=?", (uid,)).fetchone() is not None

    def recent_items(self, since):
        return self.db.execute(
            "SELECT uid, story_id, title FROM items WHERE seen>=?", (since,)
        ).fetchall()

    def new_story(self, now):
        cur = self.db.execute(
            "INSERT INTO stories(first_seen, last_seen) VALUES(?, ?)", (now, now)
        )
        return cur.lastrowid

    def add_item(self, item, story_id, base_score, now):
        self.db.execute(
            "INSERT OR IGNORE INTO items(uid, story_id, title, summary, link, source, "
            "tier, category, base_score, published, seen) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (item["uid"], story_id, item["title"], item["summary"], item["link"],
             item["source"], item["tier"], item["category"], base_score,
             item["published"], now),
        )
        self.db.execute("UPDATE stories SET last_seen=? WHERE id=?", (now, story_id))
        self.db.commit()

    def story_items(self, story_id):
        return self.db.execute(
            "SELECT * FROM items WHERE story_id=? ORDER BY base_score DESC, tier ASC, published ASC",
            (story_id,),
        ).fetchall()

    def story(self, story_id):
        return self.db.execute("SELECT * FROM stories WHERE id=?", (story_id,)).fetchone()

    def stories_since(self, since):
        return self.db.execute(
            "SELECT * FROM stories WHERE last_seen>=? ORDER BY id", (since,)
        ).fetchall()

    def mark_sent(self, story_id, when):
        self.db.execute("UPDATE stories SET sent_at=? WHERE id=?", (when, story_id))
        self.db.commit()

    def save_ai(self, story_id, result):
        self.db.execute(
            "UPDATE stories SET ai_score=?, ai_category=?, ai_title=?, ai_text=?, "
            "ai_impact=?, ai_duplicate=? WHERE id=?",
            (int(result["importanza"]), result["categoria"], result["titolo"],
             result["testo"], result["impatto_oro"], int(bool(result["doppione"])), story_id),
        )
        self.db.commit()

    def sent_titles_since(self, since):
        rows = self.db.execute(
            "SELECT id, ai_title FROM stories WHERE sent_at>=? ORDER BY sent_at",
            (max(since, 1),),
        ).fetchall()
        titles = []
        for row in rows:
            title = row["ai_title"]
            if not title:
                items = self.story_items(row["id"])
                title = items[0]["title"] if items else ""
            if title:
                titles.append(title)
        return titles

    def count_ai_call(self, day):
        key = f"ai_calls_{day}"
        count = int(self.get_meta(key, "0")) + 1
        self.set_meta(key, count)
        return count

    def ai_calls(self, day):
        return int(self.get_meta(f"ai_calls_{day}", "0"))

    def alerts_sent_since(self, since):
        # sent_at = 0 indica "segnata come già vista al primo avvio", non un invio reale.
        row = self.db.execute(
            "SELECT COUNT(*) AS n FROM stories WHERE sent_at>=?", (max(since, 1),)
        ).fetchone()
        return row["n"]

    def cleanup(self, older_than_days=7):
        limit = time.time() - older_than_days * 86400
        self.db.execute("DELETE FROM items WHERE seen<?", (limit,))
        self.db.execute("DELETE FROM stories WHERE last_seen<?", (limit,))
        self.db.commit()
