from fastapi import FastAPI
from contextlib import asynccontextmanager

from .database import engine, Base
from .audit_trail import AuditLogMiddleware
from .routes import auth, deviations, capa, documents, batch_records, dashboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup Database schema on startup
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Pharma QMS", version="1.0.0", lifespan=lifespan)

app.add_middleware(AuditLogMiddleware)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(deviations.router, prefix="/deviations", tags=["Deviations"])
app.include_router(capa.router, prefix="/capas", tags=["CAPAs"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(batch_records.router, prefix="/batch_records", tags=["Batch Records"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok"}
