
from fastapi import FastAPI
from .routers import health, usage, reports

app = FastAPI(title="Prompt Go Dashboard", version="0.1.0")
app.include_router(health.router)
app.include_router(usage.router, prefix="/usage")
app.include_router(reports.router, prefix="/reports")

