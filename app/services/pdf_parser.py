"""
Extração de campos TISS a partir de PDFs com camada de texto (estruturados).
Usa pdfplumber para extrair texto e tabelas.
"""
import re
import pdfplumber
from io import BytesIO
from typing import Optional

from app.models.sadt import GuiaSADT, DadosOperadora, DadosBeneficiario, DadosSolicitante, Procedimento


def _find(pattern: str, text: str, flags: int = re.IGNORECASE) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else None


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        pages_text = []
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if text:
                pages_text.append(text)
    return "\n".join(pages_text)


def _extract_tables_from_pdf(pdf_bytes: bytes) -> list[list[list[str]]]:
    tables = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)
    return tables


def is_structured_pdf(pdf_bytes: bytes) -> bool:
    """Retorna True se o PDF contém texto extraível (não é apenas imagem escaneada)."""
    text = _extract_text_from_pdf(pdf_bytes)
    # Considera estruturado se tiver mais de 50 caracteres de texto significativo
    meaningful = re.sub(r'\s+', '', text)
    return len(meaningful) > 50


def _parse_procedimentos_from_tables(tables: list) -> list[Procedimento]:
    procedimentos = []
    tuss_pattern = re.compile(r'^\d{8}$')

    for table in tables:
        for row in table:
            if not row:
                continue
            cells = [str(c).strip() if c else "" for c in row]
            # Tenta identificar linha com código TUSS (8 dígitos)
            codigo = next((c for c in cells if tuss_pattern.match(c)), None)
            if codigo:
                idx = cells.index(codigo)
                descricao = cells[idx + 1] if idx + 1 < len(cells) else None
                qtd_raw = cells[idx + 2] if idx + 2 < len(cells) else None
                try:
                    qtd = int(re.sub(r'\D', '', qtd_raw)) if qtd_raw else None
                except ValueError:
                    qtd = None
                procedimentos.append(Procedimento(
                    codigo_tuss=codigo,
                    descricao=descricao,
                    quantidade=qtd,
                ))
    return procedimentos


def extract_from_structured_pdf(pdf_bytes: bytes) -> GuiaSADT:
    text = _extract_text_from_pdf(pdf_bytes)
    tables = _extract_tables_from_pdf(pdf_bytes)

    # --- Operadora ---
    registro_ans = _find(r'registro\s+ans[:\s]+(\d{6})', text)
    nome_operadora = _find(r'operadora[:\s]+([^\n]{3,60})', text)

    # --- Beneficiário ---
    numero_carteira = _find(r'n[uú]mero\s+da\s+carteira[:\s]+([\d\s\-]{10,25})', text)
    if not numero_carteira:
        numero_carteira = _find(r'carteirinha[:\s]+([\d\s\-]{10,25})', text)
    nome_beneficiario = _find(r'nome\s+do\s+benefici[aá]rio[:\s]+([^\n]{3,80})', text)
    data_nascimento = _find(r'data\s+de\s+nascimento[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})', text)
    cns = _find(r'cns[:\s]+([\d]{15})', text)

    # --- Solicitante ---
    nome_solicitante = _find(r'nome\s+do\s+profissional[:\s]+([^\n]{3,80})', text)
    cnes = _find(r'cnes[:\s]+(\d{7})', text)
    crm = _find(r'crm[:\s]*([\d]{4,8})', text)
    cbo = _find(r'cbo[:\s]*([\d]{6})', text)

    # --- Dados clínicos ---
    cid = _find(r'\bCID[:\s\-]*([A-Z]\d{2}\.?\d?)', text)
    indicacao = _find(r'indica[cç][aã]o\s+cl[ií]nica[:\s]+([^\n]{3,200})', text)
    data_solic = _find(r'data\s+da\s+solicita[cç][aã]o[:\s]+(\d{2}[/\-]\d{2}[/\-]\d{4})', text)
    numero_guia = _find(r'n[uú]mero\s+da\s+guia[:\s]+([\d]{6,20})', text)

    # --- Procedimentos das tabelas ---
    procedimentos = _parse_procedimentos_from_tables(tables)

    # Calcula campos não preenchidos para sinalizar baixa confiança
    campos_pendentes = []
    if not numero_carteira:
        campos_pendentes.append("beneficiario.numero_carteira")
    if not nome_beneficiario:
        campos_pendentes.append("beneficiario.nome")
    if not cid:
        campos_pendentes.append("cid_principal")
    if not procedimentos:
        campos_pendentes.append("procedimentos")

    confianca = max(0.0, 1.0 - (len(campos_pendentes) * 0.2))

    return GuiaSADT(
        numero_guia=numero_guia,
        data_solicitacao=data_solic,
        tipo_guia="SADT",
        operadora=DadosOperadora(
            registro_ans=registro_ans,
            nome_operadora=nome_operadora,
        ),
        beneficiario=DadosBeneficiario(
            numero_carteira=numero_carteira,
            nome=nome_beneficiario,
            data_nascimento=data_nascimento,
            cns=cns,
        ),
        solicitante=DadosSolicitante(
            nome_profissional=nome_solicitante,
            cnes_solicitante=cnes,
            numero_conselho=crm,
            conselho="CRM" if crm else None,
            cbo=cbo,
        ),
        indicacao_clinica=indicacao,
        cid_principal=cid,
        procedimentos=procedimentos,
        confianca_extracao=confianca,
        metodo_extracao="pdf_estruturado",
        campos_pendentes=campos_pendentes,
    )
