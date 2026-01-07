import sqlite3
import os
import time
from paths import backend_path
from config import CACHE_DB_FILE
from logger import logger

class AppCache:
    def __init__(self):
        self.db_path = backend_path(CACHE_DB_FILE)
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS app_cache (
                        appid INTEGER PRIMARY KEY,
                        mirror_url TEXT,
                        token TEXT,
                        key TEXT,
                        last_checked INTEGER
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.warn(f"SkyTools: Cache DB init failed: {e}")

    def get_cached_app(self, appid: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT mirror_url, token, key, last_checked FROM app_cache WHERE appid = ?", 
                    (appid,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "mirror_url": row[0],
                        "token": row[1],
                        "key": row[2],
                        "last_checked": row[3]
                    }
        except Exception as e:
            logger.warn(f"SkyTools: Cache read failed for {appid}: {e}")
        return None

    def update_cached_app(self, appid: int, mirror_url: str = None, token: str = None, key: str = None):
        try:
            now = int(time.time())
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO app_cache (appid, mirror_url, token, key, last_checked)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(appid) DO UPDATE SET
                        mirror_url = COALESCE(?, mirror_url),
                        token = COALESCE(?, token),
                        key = COALESCE(?, key),
                        last_checked = ?
                """, (appid, mirror_url, token, key, now, mirror_url, token, key, now))
                conn.commit()
        except Exception as e:
            logger.warn(f"SkyTools: Cache update failed for {appid}: {e}")

# Global instance
cache = AppCache()
