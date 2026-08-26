from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


SCHEMA_VERSION = 2


class VehicleLimitReachedError(Exception):
    pass


class VehicleNotFoundError(Exception):
    pass


class LastVehicleDeletionError(Exception):
    pass


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

            CREATE UNIQUE INDEX IF NOT EXISTS idx_vehicle_profiles_one_active
            ON vehicle_profiles(is_active)
            WHERE is_active = 1;
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


def get_vehicle_row(database_path: Path, vehicle_id: str) -> sqlite3.Row:
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, nickname, manufacturer, model, model_year, powertrain,
                   fuel_grade, battery_capacity_kwh, is_active
            FROM vehicle_profiles
            WHERE id = ?
            """,
            (vehicle_id,),
        ).fetchone()
    if row is None:
        raise VehicleNotFoundError
    return row


def create_vehicle(database_path: Path, values: dict[str, object]) -> sqlite3.Row:
    with connect(database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM vehicle_profiles").fetchone()[0]
        if count >= 3:
            raise VehicleLimitReachedError
        is_active = 1 if count == 0 else 0
        connection.execute(
            """
            INSERT INTO vehicle_profiles (
                id, nickname, manufacturer, model, model_year, powertrain,
                fuel_grade, battery_capacity_kwh, is_active
            ) VALUES (
                :id, :nickname, :manufacturer, :model, :model_year, :powertrain,
                :fuel_grade, :battery_capacity_kwh, :is_active
            )
            """,
            {**values, "is_active": is_active},
        )
        connection.commit()
    return get_vehicle_row(database_path, str(values["id"]))


def update_vehicle(
    database_path: Path, vehicle_id: str, values: dict[str, object]
) -> sqlite3.Row:
    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE vehicle_profiles
            SET nickname = :nickname,
                manufacturer = :manufacturer,
                model = :model,
                model_year = :model_year,
                powertrain = :powertrain,
                fuel_grade = :fuel_grade,
                battery_capacity_kwh = :battery_capacity_kwh
            WHERE id = :vehicle_id
            """,
            {**values, "vehicle_id": vehicle_id},
        )
        if cursor.rowcount == 0:
            raise VehicleNotFoundError
        connection.commit()
    return get_vehicle_row(database_path, vehicle_id)


def activate_vehicle(database_path: Path, vehicle_id: str) -> sqlite3.Row:
    with connect(database_path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM vehicle_profiles WHERE id = ?", (vehicle_id,)
        ).fetchone()
        if exists is None:
            raise VehicleNotFoundError
        connection.execute("UPDATE vehicle_profiles SET is_active = 0 WHERE is_active = 1")
        connection.execute(
            "UPDATE vehicle_profiles SET is_active = 1 WHERE id = ?", (vehicle_id,)
        )
        connection.commit()
    return get_vehicle_row(database_path, vehicle_id)


def delete_vehicle(database_path: Path, vehicle_id: str) -> None:
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT id, is_active FROM vehicle_profiles ORDER BY created_at, id"
        ).fetchall()
        target = next((row for row in rows if row["id"] == vehicle_id), None)
        if target is None:
            raise VehicleNotFoundError
        if len(rows) == 1:
            raise LastVehicleDeletionError
        connection.execute("DELETE FROM vehicle_profiles WHERE id = ?", (vehicle_id,))
        if target["is_active"]:
            replacement_id = next(row["id"] for row in rows if row["id"] != vehicle_id)
            connection.execute(
                "UPDATE vehicle_profiles SET is_active = 1 WHERE id = ?",
                (replacement_id,),
            )
        connection.commit()
