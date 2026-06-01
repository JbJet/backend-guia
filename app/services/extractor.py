"""
Pipeline principal de extração de Guia SADT.

Fluxo atualizado:
  1. Se a chave do Gemini estiver configurada no .env, utiliza a extração inteligente via Gemini
     diretamente para garantir o mapeamento correto e evitar campos invertidos.
  2. Caso contrário (sem chave ou em caso de falha), recorre aos métodos locais estruturados e de OCR.
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

    # 1. TENTA EXTRAÇÃO DIRETA VIA GEMINI SE A CHAVE EXISTIR
    # Isso garante que a IA use a inteligência contextual do modelo estruturado
    if settings.gemini_api_key:
        try:
            return extract_via_gemini(file_bytes, content_type)
        except Exception as e:
            # Fallback de segurança: se a API falhar por rede ou limite, tenta o local
            print(
                f"Erro na extração direta do Gemini, tentando extrator local: {str(e)}"
            )

    # 2. FLUXO LOCAL (Se estiver sem chave no .env ou se a API falhar)
    if content_type == "application/pdf" and is_structured_pdf(file_bytes):
        guia = extract_from_structured_pdf(file_bytes)
    else:
        guia = extract_via_ocr(file_bytes, content_type)

    return guia
