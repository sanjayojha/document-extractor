from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import documents
from app.core.config import settings

app = FastAPI(title="Doc Extractor Pro", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}