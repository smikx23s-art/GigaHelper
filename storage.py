import sqlite3
import asyncio
from datetime import date

DB_PATH = "stats_history.db"


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            impressions INTEGER,
            clicks INTEGER,
            income REAL,
            cpm REAL,
            ctr REAL,
            updated_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def _save_sync(d: str, totals: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO daily_stats (date, impressions, clicks, income, cpm, ctr, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(date) DO UPDATE SET
            impressions=excluded.impressions,
            clicks=excluded.clicks,
            income=excluded.income,
            cpm=excluded.cpm,
            ctr=excluded.ctr,
            updated_at=excluded.updated_at
        """,
        (d, totals["impressions"], totals["clicks"], totals["income"], totals["cpm"], totals["ctr"]),
    )
    conn.commit()
    conn.close()


def _get_history_sync(days: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT date, impressions, clicks, income, cpm, ctr FROM daily_stats "
        "ORDER BY date DESC LIMIT ?",
        (days,),
    )
    rows = cur.fetchall()
    conn.close()
    rows.reverse()
    return [
        {
            "date": r[0],
            "impressions": r[1],
            "clicks": r[2],
            "income": r[3],
            "cpm": r[4],
            "ctr": r[5],
        }
        for r in rows
    ]


_init_db()


async def save_daily_stats(d: date, totals: dict):
    await asyncio.to_thread(_save_sync, d.isoformat(), totals)


async def get_history(days: int = 90):
    return await asyncio.to_thread(_get_history_sync, days)
