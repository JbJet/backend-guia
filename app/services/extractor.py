"""
Pipeline principal de extração de Guia SADT.

Fluxo:
  1. PDF com texto?  → pdf_parser (pdfplumber)
  2. PDF/imagem sem texto → ocr_service (pytesseract)
  3. Confiança < threshold ou campos críticos ausentes → gemini_service (fallback)
"""
from app.models.sadt import GuiaSADT
from app.config import settings
from app.services.pdf_parser import is_structured_pdf, extract_from_structured_pdf
from app.services.ocr_service import extract_via_ocr
from app.services.gemini_service import enrich_with_gemini, extract_via_gemini

_CRITICAL_FIELDS = {"beneficiario.numero_carteira", "procedimentos"}


def _needs_gemini_fallback(guia: GuiaSADT) -> bool:
    if (guia.confianca_extracao or 1.0) < settings.ocr_confidence_threshold:
        return True
    if _CRITICAL_FIELDS & set(guia.campos_pendentes):
        return True
    return False


def extract(file_bytes: bytes, content_type: str) -> GuiaSADT:
    """
    Recebe os bytes do arquivo e seu MIME type.
    Retorna uma GuiaSADT com os campos extraídos e metadados de confiança.
    """
    if not settings.gemini_api_key:
        # Sem chave Gemini, usa somente extratores locais
        use_gemini = False
    else:
        use_gemini = False # Default eh true

    # 1. Tenta extração local
    if content_type == "application/pdf" and is_structured_pdf(file_bytes):
        guia = extract_from_structured_pdf(file_bytes)
    else:
        guia = extract_via_ocr(file_bytes, content_type)

    # 2. Fallback Gemini se necessário
    if use_gemini and _needs_gemini_fallback(guia):
        guia = enrich_with_gemini(guia, file_bytes, content_type)

    return guia
