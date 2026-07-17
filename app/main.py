import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()
    message = "Validation error"
    if errors:
        first = errors[0]
        field = ".".join(str(loc) for loc in first.get("loc", []) if loc != "body")
        err_msg = first.get("msg", "Invalid value")
        if field:
            # Match contract style: "Email is required"
            if "required" in err_msg.lower() or first.get("type") == "missing":
                message = f"{field[0].upper() + field[1:] if field else 'Field'} is required"
                # Prefer human field names from alias when available
                field_name = field.split(".")[-1]
                pretty = {
                    "email": "Email",
                    "password": "Password",
                    "name": "Name",
                    "guardian": "Guardian",
                    "acceptedTerms": "AcceptedTerms",
                    "accepted_terms": "AcceptedTerms",
                    "code": "Code",
                }.get(field_name, field_name.capitalize())
                message = f"{pretty} is required"
            else:
                message = f"{field}: {err_msg}"
        else:
            message = err_msg
    return JSONResponse(
        status_code=400,
        content={"success": False, "message": message},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logging.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error"},
    )
