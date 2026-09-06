"""
X簿 - db.py
データベース操作・マイグレーション管理モジュール
"""

import json
import sqlite3
from pathlib import Path

# ===================================================
# パス・バージョン定義
# ===================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "data" / "xbook.db"
SCHEMA_VERSION = 1


# ===================================================
# 接続
# ===================================================
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ===================================================
# 初期化・マイグレーション
# ===================================================
def initialize():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        _create_tables(conn)
        _migrate(conn)
    finally:
        conn.close()


def _create_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            date           TEXT NOT NULL UNIQUE,
            followers_count INTEGER,
            note           TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now', '+9 hours')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now', '+9 hours'))
        );

        CREATE TABLE IF NOT EXISTS analytics_data (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            date           TEXT,
            source_type    TEXT NOT NULL,
            source_hash    TEXT NOT NULL UNIQUE,
            extracted_data TEXT,
            created_at     TEXT NOT NULL DEFAULT (datetime('now', '+9 hours'))
        );

        CREATE TABLE IF NOT EXISTS ai_reviews (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            period_start   TEXT NOT NULL,
            period_end     TEXT NOT NULL,
            model_name     TEXT NOT NULL,
            prompt_version TEXT NOT NULL,
            review_json    TEXT NOT NULL,
            created_at     TEXT NOT NULL DEFAULT (datetime('now', '+9 hours'))
        );

        CREATE TABLE IF NOT EXISTS ai_usage_log (
            log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            year_month    TEXT NOT NULL UNIQUE,
            count         INTEGER NOT NULL DEFAULT 0,
            monthly_limit INTEGER,
            updated_at    TEXT NOT NULL DEFAULT (datetime('now', '+9 hours'))
        );

        CREATE TABLE IF NOT EXISTS schema_version (
            version    INTEGER NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now', '+9 hours'))
        );
    """)
    conn.commit()


def _migrate(conn):
    row = conn.execute("SELECT version FROM schema_version ORDER BY rowid DESC LIMIT 1").fetchone()
    current = row["version"] if row else 0

    if current == 0:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()


# ===================================================
# daily_logs CRUD
# ===================================================
def upsert_log(date: str, followers_count, note: str):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO daily_logs (date, followers_count, note, updated_at)
            VALUES (?, ?, ?, datetime('now', '+9 hours'))
            ON CONFLICT(date) DO UPDATE SET
                followers_count = excluded.followers_count,
                note            = excluded.note,
                updated_at      = excluded.updated_at
        """, (date, followers_count, note))
        conn.commit()
    finally:
        conn.close()


def get_all_logs():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM daily_logs ORDER BY date DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_logs_by_period(start: str, end: str):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM daily_logs WHERE date BETWEEN ? AND ? ORDER BY date ASC",
            (start, end)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_log(log_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM daily_logs WHERE id = ?", (log_id,))
        conn.commit()
    finally:
        conn.close()


# ===================================================
# ai_usage_log（振り返り・データ抽出の両方でカウントする）
# ===================================================
def get_monthly_count(year_month: str) -> int:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT count FROM ai_usage_log WHERE year_month = ?", (year_month,)
        ).fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()


def increment_monthly_count(year_month: str):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO ai_usage_log (year_month, count, updated_at)
            VALUES (?, 1, datetime('now', '+9 hours'))
            ON CONFLICT(year_month) DO UPDATE SET
                count      = count + 1,
                updated_at = datetime('now', '+9 hours')
        """, (year_month,))
        conn.commit()
    finally:
        conn.close()


def get_monthly_limit(year_month: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT monthly_limit FROM ai_usage_log WHERE year_month = ?", (year_month,)
        ).fetchone()
        return row["monthly_limit"] if row else 30
    finally:
        conn.close()


def set_monthly_limit(year_month: str, limit):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO ai_usage_log (year_month, count, monthly_limit, updated_at)
            VALUES (?, 0, ?, datetime('now', '+9 hours'))
            ON CONFLICT(year_month) DO UPDATE SET
                monthly_limit = excluded.monthly_limit,
                updated_at    = datetime('now', '+9 hours')
        """, (year_month, limit))
        conn.commit()
    finally:
        conn.close()


# ===================================================
# ai_reviews
# ===================================================
def save_ai_review(period_start: str, period_end: str,
                   model_name: str, prompt_version: str, review_json: str):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO ai_reviews
                (period_start, period_end, model_name, prompt_version, review_json)
            VALUES (?, ?, ?, ?, ?)
        """, (period_start, period_end, model_name, prompt_version, review_json))
        conn.commit()
    finally:
        conn.close()


def get_latest_ai_review():
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM ai_reviews ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ===================================================
# analytics_data
# ===================================================
def save_analytics_data(date, source_type: str, source_hash: str, extracted_data):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO analytics_data
                (date, source_type, source_hash, extracted_data)
            VALUES (?, ?, ?, ?)
        """, (date, source_type, source_hash, extracted_data))
        conn.commit()
    finally:
        conn.close()


def check_analytics_hash(source_hash: str) -> bool:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM analytics_data WHERE source_hash = ?", (source_hash,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def get_analytics_detail(period_start: str = None, period_end: str = None) -> list:
    """
    AI振り返り用にanalytics_dataの詳細リストを返す。
    period_start/period_endを指定すると、その期間と関連するデータのみに絞り込む。
    date（データの対象期間終了日）がperiod_start〜period_endの範囲、
    または日付未設定（date IS NULL）のデータを対象とする。
    """
    conn = get_connection()
    try:
        if period_start and period_end:
            rows = conn.execute("""
                SELECT extracted_data FROM analytics_data
                WHERE extracted_data IS NOT NULL
                  AND (date IS NULL OR date BETWEEN ? AND ?)
                ORDER BY created_at DESC LIMIT 5
            """, (period_start, period_end)).fetchall()
        else:
            rows = conn.execute("""
                SELECT extracted_data FROM analytics_data
                WHERE extracted_data IS NOT NULL
                ORDER BY created_at DESC LIMIT 5
            """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
