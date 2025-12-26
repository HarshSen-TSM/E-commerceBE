from  utils.response_helper import error_response
from fastapi import Request
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

async def http_exception_handler(request: Request, exc: HTTPException):
    return error_response(
        message = exc.detail,
        status_code = exc.status_code,
        error = exc.detail
)

async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    first_error = exc.errors()[0]
    field = first_error["loc"][-1]
    error_message = f"{field}: {first_error['msg']}"

    return error_response(
        message="Validation error",
        status_code=422,
        error=error_message
    )

async def generic_exception_handler(request: Request, exc: Exception):
    return error_response(
        message="Internal server error",
        status_code=500,
        error="Internal server error"
    )