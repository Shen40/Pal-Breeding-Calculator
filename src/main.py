import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, ProgrammingError

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.database import Base, engine
from src.core.error_handler import register_error_handlers
from src.engine.pathfinder import build_reverse_lookup_table

# Base directory setup (Assuming this file lives at src/main.py)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create DB tables if they don't exist yet.
    # Under multiple Gunicorn workers this runs concurrently in every worker
    # process; on Postgres, CREATE TYPE for the `gender` enum isn't safely
    # concurrent, so a losing worker can hit a duplicate-object/duplicate-key
    # error even though the schema it wanted now exists. Treat that as success.
    try:
        Base.metadata.create_all(bind=engine)
    except (ProgrammingError, IntegrityError):
        pass

    # 2. Load breeding and pal datasets
    with open(DATA_DIR / "pals.json", "r", encoding="utf-8") as f:
        pals_data = json.load(f)

    with open(DATA_DIR / "unique_combos.json", "r", encoding="utf-8") as f:
        combos_data = json.load(f)

    with open(DATA_DIR / "passives.json", "r", encoding="utf-8") as f:
        passives_data = json.load(f)

    # 3. Populate state and construct reverse lookup table
    app.state.pals = pals_data
    app.state.unique_combos = combos_data
    app.state.passives = passives_data
    app.state.reverse_lookup = build_reverse_lookup_table(pals_data, combos_data)

    yield


# App Initialization
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/api/v1/openapi.json"
    if settings.ENVIRONMENT != "production"
    else None,
    lifespan=lifespan,
)

# Enable CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception & Error Handlers
register_error_handlers(app)

# API Routes
app.include_router(api_router, prefix="/api/v1")

# Mount Static Files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Serve Web Frontend Root
@app.get("/", response_class=FileResponse)
def read_root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend index.html not found in static directory."},
    )