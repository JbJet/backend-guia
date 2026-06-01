from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class Procedimento(BaseModel):
    """Procedimento/exame solicitado — código TUSS + descrição."""

    codigo_tuss: Optional[str] = Field(None, description="Código TUSS do procedimento")
    descricao: Optional[str] = Field(None, description="Descrição do procedimento")
    quantidade: Optional[int] = Field(None, description="Quantidade solicitada")
    unidade_medida: Optional[str] = None


class DadosOperadora(BaseModel):
    registro_ans: Optional[str] = Field(None, description="Registro ANS da operadora")
    nome_operadora: Optional[str] = Field(
        None,
        description=(
            "Nome da operadora de saúde/plano de saúde (ex: UNIMED). "
            "Fica tipicamente isolado no topo esquerdo da guia. "
            "NÃO capture o nome de clínicas prestadoras ou contratados neste campo."
        ),
    )


class DadosBeneficiario(BaseModel):
    numero_carteira: Optional[str] = Field(
        None, description="Número do cartão do beneficiário"
    )
    nome: Optional[str] = None
    data_nascimento: Optional[str] = None
    cns: Optional[str] = Field(None, description="Cartão Nacional de Saúde")
    atendimento_rn: Optional[bool] = Field(
        None, description="Atendimento a recém-nascido"
    )


class DadosSolicitante(BaseModel):
    nome_contratado: Optional[str] = Field(
        None,
        description="Nome da empresa médica, clínica ou prestador contratado que está realizando a solicitação. Ex: Clínica Médica Nova Vida Ltda.",
    )
    cnes_solicitante: Optional[str] = Field(
        None, description="CNES do estabelecimento solicitante"
    )
    nome_profissional: Optional[str] = Field(
        None,
        description=(
            "Nome completo do médico ou profissional solicitante (ex: Dra. Mariana Silva Barros). "
            "Fica localizado próximo ao campo '11-NOME DO PROFISSIONAL SOLICITANTE'. "
            "Atenção: NÃO capture o rótulo de colunas ou cabeçalhos fixos como 'SOLICITANTE 12'."
        ),
    )
    conselho: Optional[str] = Field(None, description="Ex: CRM, CRO, COREN")
    numero_conselho: Optional[str] = Field(
        None,
        description="Apenas o número do conselho profissional (ex: 45678). Fica no campo '13-NÚMERO NO CONSELHO'.",
    )
    uf_conselho: Optional[str] = Field(
        None, description="UF do conselho. Campo '14-UF'."
    )
    cbo: Optional[str] = Field(None, description="Código Brasileiro de Ocupações")
    assinatura_data: Optional[str] = None


class DadosExecutante(BaseModel):
    nome_contratado: Optional[str] = None
    cnes_executante: Optional[str] = None
    codigo_na_operadora: Optional[str] = None


class GuiaSADT(BaseModel):
    """
    Guia de Solicitação de Autorização para exames/consultas (SADT)
    conforme padrão TISS 3.x da ANS.
    """

    # Cabeçalho
    numero_guia: Optional[str] = Field(
        None, description="Número da guia emitida pela operadora"
    )
    numero_guia_prestador: Optional[str] = Field(
        None, description="Número da guia no prestador"
    )
    data_solicitacao: Optional[str] = None
    data_autorizacao: Optional[str] = None
    senha_autorizacao: Optional[str] = None
    data_validade_senha: Optional[str] = None
    tipo_guia: Optional[str] = Field("SADT", description="Tipo de guia TISS")

    # Seções
    operadora: Optional[DadosOperadora] = None
    beneficiario: Optional[DadosBeneficiario] = None
    solicitante: Optional[DadosSolicitante] = None
    executante: Optional[DadosExecutante] = None

    # Dados clínicos
    indicacao_clinica: Optional[str] = Field(None, description="Justificativa clínica")
    cid_principal: Optional[str] = Field(None, description="CID-10 principal")
    cid_secundario: Optional[str] = None
    carater_atendimento: Optional[str] = Field(
        None, description="1=Eletivo, 2=Urgência/emergência"
    )
    tipo_atendimento: Optional[str] = Field(
        None, description="01=Consulta, 02=Exame, 03=Terapia, etc."
    )

    # Procedimentos solicitados
    procedimentos: list[Procedimento] = Field(default_factory=list)

    # Metadados da extração
    confianca_extracao: Optional[float] = Field(
        None, description="Score de confiança 0.0-1.0"
    )
    metodo_extracao: Optional[str] = Field(
        None, description="pdf_estruturado | ocr | gemini"
    )
    campos_pendentes: list[str] = Field(
        default_factory=list,
        description="Campos não extraídos com confiança suficiente",
    )
