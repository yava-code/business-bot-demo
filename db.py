import sqlite3

DB_PATH = "data.db"


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ts       TEXT    NOT NULL,
            user_id  INTEGER NOT NULL,
            filename TEXT    NOT NULL,
            summary  TEXT    NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            lang    TEXT NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role    TEXT    NOT NULL,
            content TEXT    NOT NULL,
            ts      TEXT    NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_files (
            user_id  INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            content  TEXT NOT NULL,
            ts       TEXT NOT NULL
        )
        """
    )
    con.commit()
    con.close()


def insert_log(ts: str, user_id: int, filename: str, summary: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO logs (ts, user_id, filename, summary) VALUES (?, ?, ?, ?)",
        (ts, user_id, filename, summary[:100]),
    )
    con.commit()
    con.close()


def get_history(user_id: int, limit: int = 5) -> list[tuple]:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT ts, filename, summary FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    con.close()
    return rows


def get_lang(user_id: int) -> str:
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT lang FROM user_settings WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    con.close()
    return (row[0] if row else "ru")


def set_lang(user_id: int, lang: str):
    if lang not in ("ru", "en"):
        lang = "ru"
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO user_settings (user_id, lang) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET lang = excluded.lang",
        (user_id, lang),
    )
    con.commit()
    con.close()


def add_msg(user_id: int, role: str, content: str, ts: str):
    if role not in ("user", "assistant", "system"):
        role = "user"
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO chat_messages (user_id, role, content, ts) VALUES (?, ?, ?, ?)",
        (user_id, role, content, ts),
    )
    con.commit()
    con.close()


def get_msgs(user_id: int, limit: int = 16) -> list[tuple[str, str]]:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    con.close()
    rows.reverse()
    return [(r, c) for r, c in rows]


def clear_msgs(user_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    con.commit()
    con.close()


def set_pending_file(user_id: int, filename: str, content: str, ts: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO pending_files (user_id, filename, content, ts) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET filename = excluded.filename, content = excluded.content, ts = excluded.ts",
        (user_id, filename, content, ts),
    )
    con.commit()
    con.close()


def get_pending_file(user_id: int) -> tuple[str, str] | None:
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT filename, content FROM pending_files WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    con.close()
    if not row:
        return None
    return row[0], row[1]


def clear_pending_file(user_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM pending_files WHERE user_id = ?", (user_id,))
    con.commit()
    con.close()
