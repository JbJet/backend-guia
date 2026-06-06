"""
Fallback via Gemini Vision API.
Acionado quando a confiança do OCR/pdfplumber está abaixo do threshold,
ou quando campos críticos (numero_carteira, procedimentos) não foram extraídos.
"""

import json
import base64
import re
from typing import Optional

import google.generativeai as genai
from PIL import Image
from io import BytesIO
import fitz  # PyMuPDF

from app.models.sadt import (
    GuiaSADT,
    DadosOperadora,
    DadosBeneficiario,
    DadosSolicitante,
    DadosExecutante,
    Procedimento,
)
from app.config import settings

# Prompt de sistema para guiar a extração de dados estruturados
_SYSTEM_PROMPT = """Você é um especialista em auditoria médica e faturamento de guias do padrão TISS/TUSS da ANS brasileira.
Sua tarefa é analisar a imagem de uma Guia e extrair estritamente os dados dinâmicos preenchidos, mapeando-os para a estrutura JSON exigida.

REGRAS CRÍTICAS DE MAPEAMENTO PARA EVITAR ERROS CONTEXTUAIS:
1. IDENTIFICAÇÃO DE RÓTULOS VS VALORES: Os textos fixos impressos no documento que identificam as caixas (exemplos: '10-NOME DO CONTRATADO', '11-NOME DO PROFISSIONAL SOLICITANTE', '12-CONSELHO', ou títulos de colunas) servem unicamente como guia estrutural. Você deve IGNORAR esses títulos textuais e capturar apenas os VALORES manuscritos ou digitados associados a eles.
2. CAMPO OPERADORA (nome_operadora): Busque marcas corporativas de planos de saúde tradicionalmente localizadas no topo esquerdo do documento (ex: 'UNIMED'). Jamais preencha este campo com nomes de clínicas prestadoras ou hospitais contratados.
3. SEPARAÇÃO NO BLOCO SOLICITANTE: Não confunda a clínica solicitante com o médico assistente.
   - O nome da Razão Social/clínica (ex: 'Clínica Médica Nova Vida Ltda') vai para o campo 'solicitante.nome_contratado'.
   - O nome completo da pessoa física/médico (ex: 'Dra. Mariana Silva Barros') vai única e exclusivamente para o campo 'solicitante.nome_profissional'.

Retorne APENAS um JSON válido com a seguinte estrutura (omita campos não encontrados):
{
  "numero_guia": "string",
  "numero_guia_prestador": "string",
  "data_solicitacao": "DD/MM/AAAA",
  "data_autorizacao": "DD/MM/AAAA",
  "senha_autorizacao": "string",
  "operadora": {
    "registro_ans": "6 dígitos",
    "nome_operadora": "string"
  },
  "beneficiario": {
    "numero_carteira": "string",
    "nome": "string",
    "data_nascimento": "DD/MM/AAAA",
    "cns": "15 dígitos",
    "atendimento_rn": false
  },
  "solicitante": {
    "nome_contratado": "string",
    "cnes_solicitante": "7 dígitos",
    "nome_profissional": "string",
    "conselho": "CRM|CRO|COREN|...",
    "numero_conselho": "string",
    "uf_conselho": "UF",
    "cbo": "6 dígitos"
  },
  "executante": {
    "nome_contratado": "string",
    "cnes_executante": "7 dígitos"
  },
  "indicacao_clinica": "string",
  "cid_principal": "A00.0",
  "cid_secundario": "string",
  "carater_atendimento": "1 ou 2",
  "tipo_atendimento": "01-07",
  "procedimentos": [
    {
      "codigo_tuss": "8 dígitos",
      "descricao": "string",
      "quantidade": 1
    }
  ]
}"""


def _pdf_first_page_as_image(pdf_bytes: bytes) -> bytes:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_bytes = pix.tobytes("jpeg")
    doc.close()
    return img_bytes


def _parse_gemini_response(text: str) -> dict:
    # Substituição limpa de texto para evitar confundir o analisador do VS Code
    clean = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Detect truncation specifically
    if clean.count("{") != clean.count("}") or clean.count("[") != clean.count("]"):
        raise ValueError(
            "Gemini response appears truncated (unbalanced braces). "
            "Increase max_output_tokens."
        )

    import logging
    logging.getLogger(__name__).error(
        "Gemini response could not be parsed as JSON:\n%s", text
    )
    raise ValueError(f"Gemini returned invalid JSON. Raw response: {text[:500]}")


def _dict_to_guia(data: dict) -> GuiaSADT:
    def safe_int(v) -> Optional[int]:
        try:
            return int(v) if v is not None else None
        except (ValueError, TypeError):
            return None

    procedimentos = [
        Procedimento(
            codigo_tuss=p.get("codigo_tuss"),
            descricao=p.get("descricao"),
            quantidade=safe_int(p.get("quantidade")),
        )
        for p in data.get("procedimentos", [])
    ]

    op = data.get("operadora", {}) or {}
    ben = data.get("beneficiario", {}) or {}
    sol = data.get("solicitante", {}) or {}
    exe = data.get("executante", {}) or {}

    return GuiaSADT(
        numero_guia=data.get("numero_guia"),
        numero_guia_prestador=data.get("numero_guia_prestador"),
        data_solicitacao=data.get("data_solicitacao"),
        data_autorizacao=data.get("data_autorizacao"),
        senha_autorizacao=data.get("senha_autorizacao"),
        tipo_guia="SADT",
        operadora=DadosOperadora(
            registro_ans=op.get("registro_ans"),
            nome_operadora=op.get("nome_operadora"),
        ),
        beneficiario=DadosBeneficiario(
            numero_carteira=ben.get("numero_carteira"),
            nome=ben.get("nome"),
            data_nascimento=ben.get("data_nascimento"),
            cns=ben.get("cns"),
            atendimento_rn=ben.get("atendimento_rn"),
        ),
        solicitante=DadosSolicitante(
            nome_contratado=sol.get("nome_contratado"),
            cnes_solicitante=sol.get("cnes_solicitante"),
            nome_profissional=sol.get("nome_profissional"),
            conselho=sol.get("conselho"),
            numero_conselho=sol.get("numero_conselho"),
            uf_conselho=sol.get("uf_conselho"),
            cbo=sol.get("cbo"),
        ),
        executante=DadosExecutante(
            nome_contratado=exe.get("nome_contratado"),
            cnes_executante=exe.get("cnes_executante"),
        ),
        indicacao_clinica=data.get("indicacao_clinica"),
        cid_principal=data.get("cid_principal"),
        cid_secundario=data.get("cid_secundario"),
        carater_atendimento=data.get("carater_atendimento"),
        tipo_atendimento=data.get("tipo_atendimento"),
        procedimentos=procedimentos,
        confianca_extracao=0.95,
        metodo_extracao="gemini",
        campos_pendentes=[],
    )


def extract_via_gemini(file_bytes: bytes, content_type: str) -> GuiaSADT:
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    if content_type == "application/pdf":
        image_bytes = _pdf_first_page_as_image(file_bytes)
        mime = "image/jpeg"
    else:
        image_bytes = file_bytes
        mime = content_type

    image_part = {"mime_type": mime, "data": image_bytes}

    response = model.generate_content(
    [_SYSTEM_PROMPT, image_part],
    generation_config={
        "temperature": 0.1,
        "max_output_tokens": 8192, 
        "response_mime_type": "application/json",
    },
)

    data = _parse_gemini_response(response.text)
    return _dict_to_guia(data)


def enrich_with_gemini(
    guia: GuiaSADT, file_bytes: bytes, content_type: str
) -> GuiaSADT:
    """
    Preenche apenas os campos pendentes usando Gemini,
    mantendo os campos já extraídos com confiança.
    """
    if not guia.campos_pendentes:
        return guia

    gemini_guia = extract_via_gemini(file_bytes, content_type)

    # Mescla: mantém valores já extraídos, preenche os pendentes
    guia_dict = guia.model_dump()
    gemini_dict = gemini_guia.model_dump()

    for campo in guia.campos_pendentes:
        parts = campo.split(".")
        if len(parts) == 1:
            if guia_dict.get(campo) is None and gemini_dict.get(campo) is not None:
                guia_dict[campo] = gemini_dict[campo]
        elif len(parts) == 2:
            section, field = parts
            if guia_dict.get(section) and gemini_dict.get(section):
                if guia_dict[section].get(field) is None:
                    guia_dict[section][field] = gemini_dict[section].get(field)

    guia_dict["campos_pendentes"] = []
    guia_dict["metodo_extracao"] = f"{guia.metodo_extracao}+gemini"
    guia_dict["confianca_extracao"] = min(1.0, (guia.confianca_extracao or 0) + 0.2)

    return GuiaSADT(**guia_dict)
