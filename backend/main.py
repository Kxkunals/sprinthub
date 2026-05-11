from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.core.config import settings
from app.routers import auth, workspaces, items, dashboard

# Register ORM models so Base can create tables
from app.models.core import (
    Account, Workspace, WorkspaceMember,
    WorkItem, Remark, AuditEvent
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SprintHub API",
    description="Collaborative project tracker with role-based access control",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Cross-origin resource sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")
app.include_router(items.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")

@app.get("/")
def index():
    return {"service": "SprintHub API", "version": "2.0.0", "docs": "/docs"}

@app.get("/health")
def healthcheck():
    return {"status": "ok"}
