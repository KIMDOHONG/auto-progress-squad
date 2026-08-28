from __future__ import annotations

import argparse
import json

from .config import Settings
from .database import initialize_database
from .manual_ingestion import run_pending_ingestion


def main() -> None:
    parser = argparse.ArgumentParser(
        description="승인된 서버 매뉴얼을 추출하고 차량별 검색 인덱스를 준비합니다."
    )
    parser.add_argument(
        "--vehicle-id",
        help="지정한 차량의 pending 작업만 처리합니다. 생략하면 전체 pending 작업을 처리합니다.",
    )
    arguments = parser.parse_args()
    settings = Settings.from_env()
    initialize_database(settings.database_path)
    results = run_pending_ingestion(
        settings.database_path,
        settings.manual_source_dir,
        vehicle_id=arguments.vehicle_id,
    )
    print(
        json.dumps(
            [
                {
                    "vehicle_id": result.vehicle_id,
                    "document_key": result.document_key,
                    "status": result.status,
                    "chunk_count": result.chunk_count,
                    "failure_code": result.failure_code,
                }
                for result in results
            ],
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
