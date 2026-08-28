from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote


SCHEMA_VERSION = 5


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
    connection.execute("PRAGMA foreign_keys = ON")
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
                    powertrain IN ('electric', 'hydrogen', 'gasoline', 'diesel', 'hybrid')
                ),
                fuel_grade TEXT CHECK (
                    fuel_grade IS NULL OR fuel_grade IN (
                        'regular', 'premium', 'super-premium', 'diesel', 'high-cetane'
                    )
                ),
                battery_capacity_kwh REAL,
                manual_site_id TEXT,
                manual_model_name TEXT,
                manual_project_code TEXT,
                manual_model_year INTEGER,
                manual_image_url TEXT,
                manual_verified_at TEXT,
                is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_vehicle_profiles_one_active
            ON vehicle_profiles(is_active)
            WHERE is_active = 1;

            """
        )
        table_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'vehicle_profiles'"
        ).fetchone()["sql"]
        if "'hydrogen'" not in table_sql:
            connection.executescript(
                """
                DROP INDEX IF EXISTS idx_vehicle_profiles_one_active;
                ALTER TABLE vehicle_profiles RENAME TO vehicle_profiles_v2;

                CREATE TABLE vehicle_profiles (
                    id TEXT PRIMARY KEY,
                    nickname TEXT NOT NULL,
                    manufacturer TEXT NOT NULL,
                    model TEXT NOT NULL,
                    model_year INTEGER NOT NULL,
                    powertrain TEXT NOT NULL CHECK (
                        powertrain IN ('electric', 'hydrogen', 'gasoline', 'diesel', 'hybrid')
                    ),
                    fuel_grade TEXT CHECK (
                        fuel_grade IS NULL OR fuel_grade IN (
                            'regular', 'premium', 'super-premium', 'diesel', 'high-cetane'
                        )
                    ),
                    battery_capacity_kwh REAL,
                    manual_site_id TEXT,
                    manual_model_name TEXT,
                    manual_project_code TEXT,
                    manual_model_year INTEGER,
                    manual_image_url TEXT,
                    manual_verified_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                INSERT INTO vehicle_profiles (
                    id, nickname, manufacturer, model, model_year, powertrain,
                    fuel_grade, battery_capacity_kwh, is_active, created_at
                )
                SELECT id, nickname, manufacturer, model, model_year, powertrain,
                       fuel_grade, battery_capacity_kwh, is_active, created_at
                FROM vehicle_profiles_v2;

                DROP TABLE vehicle_profiles_v2;
                CREATE UNIQUE INDEX idx_vehicle_profiles_one_active
                ON vehicle_profiles(is_active)
                WHERE is_active = 1;
                """
            )
        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(vehicle_profiles)").fetchall()
        }
        manual_columns = {
            "manual_site_id": "TEXT",
            "manual_model_name": "TEXT",
            "manual_project_code": "TEXT",
            "manual_model_year": "INTEGER",
            "manual_image_url": "TEXT",
            "manual_verified_at": "TEXT",
        }
        for column_name, column_type in manual_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE vehicle_profiles ADD COLUMN {column_name} {column_type}"
                )
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS manual_ingestion_jobs (
                vehicle_id TEXT PRIMARY KEY
                    REFERENCES vehicle_profiles(id) ON DELETE CASCADE,
                document_key TEXT NOT NULL,
                source_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (
                    status IN ('pending', 'ready', 'failed')
                ),
                attempt_count INTEGER NOT NULL DEFAULT 0,
                failure_code TEXT,
                failure_message TEXT,
                queued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ready_at TEXT
            );
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_meta(version) VALUES (?)", (SCHEMA_VERSION,)
        )
        connection.commit()


def _manual_document_identity(values: dict[str, object]) -> tuple[str, str] | None:
    site_id = values.get("manual_site_id")
    model_name = values.get("manual_model_name")
    project_code = values.get("manual_project_code")
    model_year = values.get("manual_model_year")
    if not all((site_id, model_name, project_code, model_year)):
        return None
    domains = {
        "hmc": "ownersmanual.hyundai.com",
        "kia": "ownersmanual.kia.com",
        "genesis": "ownersmanual.genesis.com",
    }
    domain = domains.get(str(site_id))
    if domain is None:
        return None
    document_key = f"{site_id}:{project_code}:{model_year}"
    source_url = (
        f"https://{domain}/manual/{quote(str(model_name), safe='')}"
        f"?projCode={quote(str(project_code), safe='')}&year={model_year}"
        "&langCode=ko_KR&countryCode=A99"
    )
    return document_key, source_url


def _sync_manual_ingestion_job(
    connection: sqlite3.Connection, vehicle_id: str, values: dict[str, object]
) -> None:
    identity = _manual_document_identity(values)
    if identity is None:
        connection.execute(
            "DELETE FROM manual_ingestion_jobs WHERE vehicle_id = ?", (vehicle_id,)
        )
        return
    document_key, source_url = identity
    current = connection.execute(
        "SELECT document_key FROM manual_ingestion_jobs WHERE vehicle_id = ?",
        (vehicle_id,),
    ).fetchone()
    if current is not None and current["document_key"] == document_key:
        connection.execute(
            """
            UPDATE manual_ingestion_jobs
            SET source_url = ?, updated_at = CURRENT_TIMESTAMP
            WHERE vehicle_id = ?
            """,
            (source_url, vehicle_id),
        )
        return
    connection.execute(
        """
        INSERT INTO manual_ingestion_jobs (
            vehicle_id, document_key, source_url, status, attempt_count,
            failure_code, failure_message, queued_at, updated_at, ready_at
        ) VALUES (?, ?, ?, 'pending', 0, NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL)
        ON CONFLICT(vehicle_id) DO UPDATE SET
            document_key = excluded.document_key,
            source_url = excluded.source_url,
            status = 'pending',
            attempt_count = 0,
            failure_code = NULL,
            failure_message = NULL,
            queued_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP,
            ready_at = NULL
        """,
        (vehicle_id, document_key, source_url),
    )


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
                   fuel_grade, battery_capacity_kwh, manual_site_id,
                   manual_model_name, manual_project_code, manual_model_year,
                   manual_image_url, manual_verified_at, is_active
            FROM vehicle_profiles
            ORDER BY created_at, id
            """
        ).fetchall()


def get_vehicle_row(database_path: Path, vehicle_id: str) -> sqlite3.Row:
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, nickname, manufacturer, model, model_year, powertrain,
                   fuel_grade, battery_capacity_kwh, manual_site_id,
                   manual_model_name, manual_project_code, manual_model_year,
                   manual_image_url, manual_verified_at, is_active
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
                fuel_grade, battery_capacity_kwh, manual_site_id,
                manual_model_name, manual_project_code, manual_model_year,
                manual_image_url, manual_verified_at, is_active
            ) VALUES (
                :id, :nickname, :manufacturer, :model, :model_year, :powertrain,
                :fuel_grade, :battery_capacity_kwh, :manual_site_id,
                :manual_model_name, :manual_project_code, :manual_model_year,
                :manual_image_url, :manual_verified_at, :is_active
            )
            """,
            {**values, "is_active": is_active},
        )
        _sync_manual_ingestion_job(connection, str(values["id"]), values)
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
                battery_capacity_kwh = :battery_capacity_kwh,
                manual_site_id = :manual_site_id,
                manual_model_name = :manual_model_name,
                manual_project_code = :manual_project_code,
                manual_model_year = :manual_model_year,
                manual_image_url = :manual_image_url,
                manual_verified_at = :manual_verified_at
            WHERE id = :vehicle_id
            """,
            {**values, "vehicle_id": vehicle_id},
        )
        if cursor.rowcount == 0:
            raise VehicleNotFoundError
        _sync_manual_ingestion_job(connection, vehicle_id, values)
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


def get_manual_ingestion_row(
    database_path: Path, vehicle_id: str
) -> sqlite3.Row | None:
    get_vehicle_row(database_path, vehicle_id)
    with connect(database_path) as connection:
        return connection.execute(
            """
            SELECT vehicle_id, document_key, source_url, status, attempt_count,
                   failure_code, failure_message, queued_at, updated_at, ready_at
            FROM manual_ingestion_jobs
            WHERE vehicle_id = ?
            """,
            (vehicle_id,),
        ).fetchone()


def retry_manual_ingestion(database_path: Path, vehicle_id: str) -> sqlite3.Row:
    get_vehicle_row(database_path, vehicle_id)
    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE manual_ingestion_jobs
            SET status = 'pending',
                attempt_count = attempt_count + 1,
                failure_code = NULL,
                failure_message = NULL,
                queued_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP,
                ready_at = NULL
            WHERE vehicle_id = ?
            """,
            (vehicle_id,),
        )
        if cursor.rowcount == 0:
            raise ValueError("verified_manual_required")
        connection.commit()
    row = get_manual_ingestion_row(database_path, vehicle_id)
    if row is None:  # pragma: no cover - guarded by the update above
        raise ValueError("verified_manual_required")
    return row
