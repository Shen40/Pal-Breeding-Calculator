import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from src.core.exceptions import AppException

logger = logging.getLogger("palworld_api")

def register_error_handlers(app: FastAPI) -> None:

    # 1. Domain-specific application errors
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error_type": exc.__class__.__name__,
                "message": exc.message,
                "path": request.url.path,
            },
        )

    # 2. Schema validation errors (Pydantic 422 formatting)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        formatted_errors = []
        for error in exc.errors():
            # Clean up field path (e.g. ['body', 'gender'] -> 'gender')
            field = " -> ".join(str(loc) for loc in error.get("loc", []) if loc != "body")
            formatted_errors.append({
                "field": field or "body",
                "message": error.get("msg", "Invalid value")
            })

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error_type": "ValidationError",
                "message": "Input validation failed. Please check the provided fields.",
                "errors": formatted_errors,
                "path": request.url.path,
            },
        )

    # 3. Database constraint violations (Foreign Keys / Uniqueness)
    @app.exception_handler(IntegrityError)
    async def db_integrity_handler(request: Request, exc: IntegrityError):
        logger.error(f"Database Integrity Violation: {exc.orig}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "error_type": "DatabaseConflictError",
                "message": "Database constraint violation (e.g., referenced user does not exist or duplicate record).",
                "path": request.url.path,
            },
        )

    # 4. Fallback for unhandled 500 runtime exceptions
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled server error at {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error_type": "InternalServerError",
                "message": "An unexpected server error occurred. Please contact support if this persists.",
                "path": request.url.path,
            },
        )