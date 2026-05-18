"""
Main FastAPI application entry point.
Registers routers, mounts static files, configures middleware.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routers import home, dashboard, leave
from app.database import Base, init_db
import app.database as db

# ─── App Instance ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Employee Attendance Portal",
    description="View attendance calendars and apply for leave.",
    version="1.0.0",
)

# ─── CORS (permissive for internal use) ──────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static Files ─────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(home.router)
app.include_router(dashboard.router)
app.include_router(leave.router)


# ─── Startup Event ────────────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    init_db()

    async with db.engine.begin() as conn:
        import app.models  # noqa
        await conn.run_sync(Base.metadata.create_all)
