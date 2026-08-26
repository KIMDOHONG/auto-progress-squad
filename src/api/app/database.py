from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


SCHEMA_VERSION = 1


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vehicle_profiles (
                id TEXT PRIMARY KEY,
                nickname TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                model TEXT NOT NULL,
                model_year INTEGER NOT NULL,
                powertrain TEXT NOT NULL CHECK (
                    powertrain IN ('electric', 'gasoline', 'diesel', 'hybrid')
                ),
                fuel_grade TEXT CHECK (
                    fuel_grade IS NULL OR fuel_grade IN (
                        'regular', 'premium', 'super-premium', 'diesel', 'high-cetane'
                    )
                ),
                battery_capacity_kwh REAL,
                is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_meta(version) VALUES (?)", (SCHEMA_VERSION,)
        )
        connection.commit()


def database_is_ready(database_path: Path) -> bool:
    try:
        with connect(database_path) as connection:
            row = connection.execute(
                "SELECT version FROM schema_meta ORDER BY version DESC LIMIT 1"
            ).fetchone()
        return row is not None and row["version"] == SCHEMA_VERSION
    except sqlite3.Error:
        return False


def list_vehicle_rows(database_path: Path) -> list[sqlite3.Row]:
    with connect(database_path) as connection:
        return connection.execute(
            """
            SELECT id, nickname, manufacturer, model, model_year, powertrain,
                   fuel_grade, battery_capacity_kwh, is_active
            FROM vehicle_profiles
            ORDER BY created_at, id
            """
        ).fetchall()
