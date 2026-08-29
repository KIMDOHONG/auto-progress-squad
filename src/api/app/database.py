from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote


SCHEMA_VERSION = 8


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
                manual_generation TEXT,
                manual_model_year INTEGER,
                manual_image_url TEXT,
                manual_title TEXT,
                manual_source_url TEXT,
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
                    manual_generation TEXT,
                    manual_model_year INTEGER,
                    manual_image_url TEXT,
                    manual_title TEXT,
                    manual_source_url TEXT,
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
            "manual_generation": "TEXT",
            "manual_model_year": "INTEGER",
            "manual_image_url": "TEXT",
            "manual_title": "TEXT",
            "manual_source_url": "TEXT",
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

            CREATE TABLE IF NOT EXISTS manual_documents (
                document_key TEXT PRIMARY KEY,
                document_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                page_count INTEGER NOT NULL,
                ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS manual_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_key TEXT NOT NULL
                    REFERENCES manual_documents(document_key) ON DELETE CASCADE,
                document_name TEXT,
                source_url TEXT,
                page INTEGER,
                section TEXT,
                content TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_manual_chunks_document_key
            ON manual_chunks(document_key);
            """
        )
        chunk_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(manual_chunks)").fetchall()
        }
        for column_name in ("document_name", "source_url"):
            if column_name not in chunk_columns:
                connection.execute(
                    f"ALTER TABLE manual_chunks ADD COLUMN {column_name} TEXT"
                )
        connection.execute(
            """
            UPDATE manual_chunks
            SET document_name = COALESCE(
                    document_name,
                    (SELECT document_name FROM manual_documents
                     WHERE document_key = manual_chunks.document_key)
                ),
                source_url = COALESCE(
                    source_url,
                    (SELECT source_url FROM manual_documents
                     WHERE document_key = manual_chunks.document_key)
                )
            WHERE document_name IS NULL OR source_url IS NULL
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
    if not all((site_id, model_name, model_year)):
        return None
    if site_id in {"chevrolet", "kgm"}:
        generation = values.get("manual_generation")
        source_url = values.get("manual_source_url")
        if not all((generation, source_url)):
            return None
        document_key = (
            f"{site_id}:catalog:{quote(str(model_name).strip().casefold(), safe='')}:"
            f"{model_year}:{quote(str(generation).strip().casefold(), safe='')}"
        )
        return document_key, str(source_url)
    if not project_code:
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
        _delete_orphan_manual_documents(connection)
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
    _delete_orphan_manual_documents(connection)


def _delete_orphan_manual_documents(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        DELETE FROM manual_documents
        WHERE NOT EXISTS (
            SELECT 1
            FROM manual_ingestion_jobs AS job
            WHERE job.document_key = manual_documents.document_key
        )
        """
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
                   manual_model_name, manual_project_code, manual_generation,
                   manual_model_year, manual_image_url, manual_title,
                   manual_source_url, manual_verified_at, is_active
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
                   manual_model_name, manual_project_code, manual_generation,
                   manual_model_year, manual_image_url, manual_title,
                   manual_source_url, manual_verified_at, is_active
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
                manual_model_name, manual_project_code, manual_generation,
                manual_model_year, manual_image_url, manual_title,
                manual_source_url, manual_verified_at, is_active
            ) VALUES (
                :id, :nickname, :manufacturer, :model, :model_year, :powertrain,
                :fuel_grade, :battery_capacity_kwh, :manual_site_id,
                :manual_model_name, :manual_project_code, :manual_generation,
                :manual_model_year, :manual_image_url, :manual_title,
                :manual_source_url, :manual_verified_at, :is_active
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
                manual_generation = :manual_generation,
                manual_model_year = :manual_model_year,
                manual_image_url = :manual_image_url,
                manual_title = :manual_title,
                manual_source_url = :manual_source_url,
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
        _delete_orphan_manual_documents(connection)
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


def replace_manual_document(
    database_path: Path,
    *,
    vehicle_id: str,
    document_key: str,
    document_name: str,
    source_url: str,
    content_sha256: str,
    page_count: int,
    chunks: list[dict[str, object]],
) -> sqlite3.Row:
    with connect(database_path) as connection:
        job = connection.execute(
            """
            SELECT document_key FROM manual_ingestion_jobs
            WHERE vehicle_id = ?
            """,
            (vehicle_id,),
        ).fetchone()
        if job is None:
            raise ValueError("verified_manual_required")
        if job["document_key"] != document_key:
            raise ValueError("manual_document_mismatch")
        connection.execute(
            """
            INSERT INTO manual_documents (
                document_key, document_name, source_url, content_sha256,
                page_count, ingested_at
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(document_key) DO UPDATE SET
                document_name = excluded.document_name,
                source_url = excluded.source_url,
                content_sha256 = excluded.content_sha256,
                page_count = excluded.page_count,
                ingested_at = CURRENT_TIMESTAMP
            """,
            (
                document_key,
                document_name,
                source_url,
                content_sha256,
                page_count,
            ),
        )
        connection.execute(
            "DELETE FROM manual_chunks WHERE document_key = ?", (document_key,)
        )
        connection.executemany(
            """
            INSERT INTO manual_chunks (
                document_key, document_name, source_url, page, section, content
            ) VALUES (
                :document_key, :document_name, :source_url, :page, :section, :content
            )
            """,
            (
                {
                    **chunk,
                    "document_key": document_key,
                    "document_name": chunk.get("document_name", document_name),
                    "source_url": chunk.get("source_url", source_url),
                }
                for chunk in chunks
            ),
        )
        connection.execute(
            """
            UPDATE manual_ingestion_jobs
            SET status = 'ready', failure_code = NULL, failure_message = NULL,
                updated_at = CURRENT_TIMESTAMP, ready_at = CURRENT_TIMESTAMP
            WHERE document_key = ?
            """,
            (document_key,),
        )
        connection.commit()
    row = get_manual_ingestion_row(database_path, vehicle_id)
    if row is None:  # pragma: no cover - guarded by the transaction above
        raise ValueError("verified_manual_required")
    return row


def reuse_manual_document(
    database_path: Path,
    *,
    vehicle_id: str,
    document_key: str,
    document_name: str,
    source_url: str,
    content_sha256: str,
) -> int | None:
    with connect(database_path) as connection:
        job = connection.execute(
            """
            SELECT document_key FROM manual_ingestion_jobs
            WHERE vehicle_id = ?
            """,
            (vehicle_id,),
        ).fetchone()
        if job is None:
            raise ValueError("verified_manual_required")
        if job["document_key"] != document_key:
            raise ValueError("manual_document_mismatch")
        document = connection.execute(
            """
            SELECT content_sha256,
                   (SELECT COUNT(*) FROM manual_chunks
                    WHERE document_key = manual_documents.document_key) AS chunk_count
            FROM manual_documents
            WHERE document_key = ?
            """,
            (document_key,),
        ).fetchone()
        if (
            document is None
            or document["content_sha256"] != content_sha256
            or document["chunk_count"] < 1
        ):
            return None
        connection.execute(
            """
            UPDATE manual_documents
            SET document_name = ?, source_url = ?
            WHERE document_key = ?
            """,
            (document_name, source_url, document_key),
        )
        connection.execute(
            """
            UPDATE manual_ingestion_jobs
            SET status = 'ready', failure_code = NULL, failure_message = NULL,
                updated_at = CURRENT_TIMESTAMP, ready_at = CURRENT_TIMESTAMP
            WHERE document_key = ?
            """,
            (document_key,),
        )
        connection.commit()
        return int(document["chunk_count"])


def fail_manual_ingestion(
    database_path: Path,
    *,
    vehicle_id: str,
    failure_code: str,
    failure_message: str,
) -> sqlite3.Row:
    with connect(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE manual_ingestion_jobs
            SET status = 'failed', attempt_count = attempt_count + 1,
                failure_code = ?, failure_message = ?,
                updated_at = CURRENT_TIMESTAMP, ready_at = NULL
            WHERE vehicle_id = ?
            """,
            (failure_code, failure_message, vehicle_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("verified_manual_required")
        connection.commit()
    row = get_manual_ingestion_row(database_path, vehicle_id)
    if row is None:  # pragma: no cover - guarded by the update above
        raise ValueError("verified_manual_required")
    return row


def list_pending_manual_ingestion_rows(
    database_path: Path, vehicle_id: str | None = None
) -> list[sqlite3.Row]:
    query = """
        SELECT vehicle_id, document_key, source_url, status, attempt_count,
               failure_code, failure_message, queued_at, updated_at, ready_at
        FROM manual_ingestion_jobs
        WHERE status = 'pending'
    """
    parameters: tuple[object, ...] = ()
    if vehicle_id is not None:
        query += " AND vehicle_id = ?"
        parameters = (vehicle_id,)
    query += " ORDER BY queued_at, vehicle_id"
    with connect(database_path) as connection:
        return connection.execute(query, parameters).fetchall()


def list_manual_chunk_rows(
    database_path: Path, document_key: str
) -> list[sqlite3.Row]:
    with connect(database_path) as connection:
        return connection.execute(
            """
            SELECT COALESCE(c.document_name, d.document_name) AS document_name,
                   COALESCE(c.source_url, d.source_url) AS source_url,
                   c.page, c.section, c.content
            FROM manual_chunks AS c
            JOIN manual_documents AS d USING (document_key)
            WHERE c.document_key = ?
            ORDER BY c.id
            """,
            (document_key,),
        ).fetchall()


def manual_document_is_indexed(database_path: Path, document_key: str) -> bool:
    with connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT EXISTS(
                SELECT 1 FROM manual_chunks WHERE document_key = ? LIMIT 1
            )
            """,
            (document_key,),
        ).fetchone()
    return bool(row[0])
