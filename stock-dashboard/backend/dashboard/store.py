"""Tiny SQLite JSON key-value store with timestamps. Failed refreshes never overwrite last-good values."""
import json
import sqlite3
import threading
import time

from .config import DB_PATH


class Store:
    def __init__(self, path=DB_PATH):
        self._c = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
        self._c.execute("PRAGMA journal_mode=WAL")
        self._c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL, t REAL NOT NULL)")
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            row = self._c.execute("SELECT v, t FROM kv WHERE k=?", (key,)).fetchone()
        return (json.loads(row[0]), row[1]) if row else (None, None)

    def val(self, key, default=None):
        v, _ = self.get(key)
        return default if v is None else v

    def set(self, key, value, t=None):
        with self._lock:
            self._c.execute("INSERT OR REPLACE INTO kv (k, v, t) VALUES (?,?,?)",
                            (key, json.dumps(value, default=str), t or time.time()))
            self._c.commit()

    def keys(self, prefix):
        with self._lock:
            return [r[0] for r in self._c.execute("SELECT k FROM kv WHERE k LIKE ?", (prefix + "%",))]

    def delete(self, key):
        with self._lock:
            self._c.execute("DELETE FROM kv WHERE k=?", (key,))
            self._c.commit()


_store = None


def store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store
