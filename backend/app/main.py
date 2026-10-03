import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.buses import router as buses_router
from app.api.routes.devices import router as devices_router
from app.api.routes.emergency import router as emergency_router
from app.api.routes.parents import router as parents_router
from app.api.routes.payroll import router as payroll_router
from app.api.routes.students import router as students_router
from app.api.routes.ws import router as ws_router
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.init_db import create_all_tables

settings = get_settings()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="School Bus Parent App API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(parents_router)
app.include_router(students_router)
app.include_router(buses_router)
app.include_router(devices_router)
app.include_router(emergency_router)
app.include_router(payroll_router)
app.include_router(admin_router)
app.include_router(ws_router)


@app.on_event("startup")
def startup_event() -> None:
    create_all_tables()
    logging.info("Database tables initialized.")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app_env": settings.APP_ENV}
