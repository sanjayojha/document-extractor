from fastapi import FastAPI

from app.api.routers import documents

app = FastAPI(title="Doc Extractor Pro", version="0.1.0")

app.include_router(documents.router)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}