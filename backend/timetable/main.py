# backend/main.py
from fastapi import FastAPI # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import CORSMiddleware # pyright: ignore[reportMissingImports]
from .db_init import init_database
from .api import router as api_router

# Initialize DB on startup
init_database()

app = FastAPI(title="Smart Timetable API")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",   # optional if you ever use CRA
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(api_router)

@app.get("/")
def root():
    return {"status": "ok"}
