import sys
from pathlib import Path

# Ensure the parent directory ('backend') is in sys.path so 'app' module imports work from any directory
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database.db import create_tables
import app.models  # Import all models to register with SQLAlchemy

# Import routers
from app.routers import auth, transactions, categories, budgets, goals, recurring, subscriptions, analytics, notifications, demo

app = FastAPI(
    title="SpendWise API",
    description="Personal Finance Management API for SpendWise application",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware — allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup
@app.on_event("startup")
def startup_event():
    create_tables()

# Include routers
app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(goals.router)
app.include_router(recurring.router)
app.include_router(subscriptions.router)
app.include_router(analytics.router)
app.include_router(notifications.router)
app.include_router(demo.router)


@app.get("/")
def root():
    return {
        "message": "SpendWise API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

