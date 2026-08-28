from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .schemas import ApiErrorDetail, ApiErrorResponse


class ServiceNotConfiguredError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        retryable: bool = False,
        details: list[dict[str, object]] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(_request: Request, error: ApiError) -> JSONResponse:
        payload = ApiErrorResponse(
            error=ApiErrorDetail(
                code=error.code,
                message=error.message,
                retryable=error.retryable,
                details=error.details,
            )
        )
        return JSONResponse(status_code=error.status_code, content=payload.model_dump())

    @app.exception_handler(ServiceNotConfiguredError)
    async def service_not_configured_handler(
        _request: Request, error: ServiceNotConfiguredError
    ) -> JSONResponse:
        payload = ApiErrorResponse(
            error=ApiErrorDetail(code=error.code, message=error.message, retryable=False)
        )
        return JSONResponse(status_code=503, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, error: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "location": list(item["loc"]),
                "message": item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ]
        payload = ApiErrorResponse(
            error=ApiErrorDetail(
                code="validation_error",
                message="요청 입력값을 확인해 주세요.",
                retryable=False,
                details=details,
            )
        )
        return JSONResponse(status_code=422, content=payload.model_dump())
