from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.upload import router as upload_router

app = FastAPI(
    title="Guia Hospitalar API",
    description="Extração de dados de Guias SADT conforme padrão TISS/TUSS da ANS",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api", tags=["guias"])


@app.get("/health")
def health():
    return {"status": "ok"}
