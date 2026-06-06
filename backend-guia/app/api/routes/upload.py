from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.models.sadt import GuiaSADT
from app.services.extractor import extract

router = APIRouter()

_ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=GuiaSADT, summary="Extrai dados de Guia SADT")
async def upload_guia(file: UploadFile = File(...)):
    content_type = file.content_type or ""

    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Formato não suportado: {content_type}. Envie PDF ou imagem (JPG, PNG, WEBP).",
        )

    file_bytes = await file.read()

    if len(file_bytes) > _MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Arquivo excede o limite de 10 MB.",
        )

    try:
        guia = extract(file_bytes, content_type)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro na extração: {str(exc)}")

    return guia
