from typing import Any
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


def success_response(
    message: str,
    data: Any = None,
    status_code: int = 200
):
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "status_code": status_code,
            "message": message,
            "data": data,
            "error": None
        })
    )


def error_response(
    message: str,
    status_code: int = 400,
    error: str | None = None
):
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder({
            "status_code": status_code,
            "message": message,
            "data": None,
            "error": error or message
        })
    )
