"""Chattics API — the only authority. Feature routers arrive with their tickets."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import repo
from app.db import get_session
from app.errors import AppError, register_error_handlers
from app.routers import auth, tenants

app = FastAPI(title="Chattics API")

register_error_handlers(app)
app.include_router(auth.router)
app.include_router(tenants.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "chattics-backend"}


@app.get("/api/health/db")
def health_db(session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        repo.ping(session)
    except SQLAlchemyError:
        raise AppError(
            "database_unreachable",
            "The database could not be reached. Please try again shortly.",
            503,
        ) from None
    return {"database": "ok"}