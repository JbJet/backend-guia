"""
Extração via OCR para PDFs escaneados e imagens (JPG, PNG, WEBP).
Converte para imagem com PyMuPDF e aplica pytesseract.
"""
import re
from io import BytesIO
from typing import Optional

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from app.models.sadt import (
    GuiaSADT, DadosOperadora, DadosBeneficiario, DadosSolicitante, Procedimento,
)


_TESSERACT_CONFIG = "--oem 3 --psm 6 -l por+eng"


def _pdf_to_images(pdf_bytes: bytes) -> list[Image.Image]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom para melhor OCR
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images


def _image_bytes_to_pil(image_bytes: bytes, content_type: str) -> list[Image.Image]:
    img = Image.open(BytesIO(image_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return [img]


def _ocr_images(images: list[Image.Image]) -> str:
    texts = []
    for img in images:
        text = pytesseract.image_to_string(img, config=_TESSERACT_CONFIG)
        texts.append(text)
    return "\n".join(texts)


def _find(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _parse_procedimentos(text: str) -> list[Procedimento]:
    procedimentos = []
    tuss_pattern = re.compile(r'(\d{8})\s+([^\n]{5,80}?)(?:\s+(\d{1,3}))?\s*$', re.MULTILINE)
    for m in tuss_pattern.finditer(text):
        try:
            qtd = int(m.group(3)) if m.group(3) else None
        except ValueError:
            qtd = None
        procedimentos.append(Procedimento(
            codigo_tuss=m.group(1),
            descricao=m.group(2).strip(),
            quantidade=qtd,
        ))
    return procedimentos


def extract_via_ocr(file_bytes: bytes, content_type: str) -> GuiaSADT:
    if content_type == "application/pdf":
        images = _pdf_to_images(file_bytes)
    else:
        images = _image_bytes_to_pil(file_bytes, content_type)

    text = _ocr_images(images)

    numero_carteira = _find(r'carteira[:\s]+([\d\s\-]{10,25})', text)
    nome_beneficiario = _find(r'benefici[aá]rio[:\s]+([^\n]{3,80})', text)
    data_nascimento = _find(r'nascimento[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})', text)
    registro_ans = _find(r'registro\s+ans[:\s]+(\d{6})', text)
    cnes = _find(r'cnes[:\s]+(\d{7})', text)
    crm = _find(r'crm[:\s]*([\d]{4,8})', text)
    cbo = _find(r'cbo[:\s]*([\d]{6})', text)
    cid = _find(r'\bCID[:\s\-]*([A-Z]\d{2}\.?\d?)', text)
    data_solic = _find(r'solicita[cç][aã]o[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})', text)
    numero_guia = _find(r'guia[:\s]+([\d]{6,20})', text)
    indicacao = _find(r'indica[cç][aã]o[:\s]+([^\n]{3,200})', text)

    procedimentos = _parse_procedimentos(text)

    campos_pendentes = []
    if not numero_carteira:
        campos_pendentes.append("beneficiario.numero_carteira")
    if not nome_beneficiario:
        campos_pendentes.append("beneficiario.nome")
    if not cid:
        campos_pendentes.append("cid_principal")
    if not procedimentos:
        campos_pendentes.append("procedimentos")

    confianca = max(0.0, 1.0 - (len(campos_pendentes) * 0.25))

    return GuiaSADT(
        numero_guia=numero_guia,
        data_solicitacao=data_solic,
        tipo_guia="SADT",
        operadora=DadosOperadora(registro_ans=registro_ans),
        beneficiario=DadosBeneficiario(
            numero_carteira=numero_carteira,
            nome=nome_beneficiario,
            data_nascimento=data_nascimento,
        ),
        solicitante=DadosSolicitante(
            cnes_solicitante=cnes,
            numero_conselho=crm,
            conselho="CRM" if crm else None,
            cbo=cbo,
        ),
        indicacao_clinica=indicacao,
        cid_principal=cid,
        procedimentos=procedimentos,
        confianca_extracao=confianca,
        metodo_extracao="ocr",
        campos_pendentes=campos_pendentes,
    )
