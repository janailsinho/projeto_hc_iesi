"""
Controller do Serviço de Anatomia Patológica (SAP / SISPATO)
=============================================================
Implementa as regras de negócio de ponta a ponta (RF001 a RF055 e RNF001 a RNF017),
incluindo todos os fluxos validados na visita técnica ao SAP/HC-UFPE:
- Recepção HC (AGHU) e SUS (pacientes externos), bipador de 7 ou 10 dígitos, múltiplos exames
  na mesma solicitação (HP + IHQ, CO + HP), lista padronizada de rejeições + 'Outros',
  etiquetas térmicas ZPL (Norma Zero: Nome + Prontuário/Nasc) e Ficha de Trabalho única.
- Macroscopia (RF013-RF018): identificação de frasco, descrição macroscópica, cassetes 1:N,
  confirmação de identidade e envio para Processamento Técnico.
- Processamento Técnico (RF019-RF032): processamento de tecidos, blocos de parafina 1:N,
  corte (microtomia), lâminas 1:N, coloração/montagem, liberação técnica, envio para
  Microscopia, arquivamento de blocos e atendimento de pedidos de IHQ/recorte.
- Microscopia (RF033-RF039): identificação de lâmina, laudo prévio do residente, revisão do
  patologista, solicitação de IHQ/complementos, liberação de exame, SISCAN e arquivamento.
- Rastreabilidade, Árvore Hierárquica, Acervo Científico (RF040-RF050) e Impressoras (RF054-RF055).
"""

import csv
import io
import unicodedata
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.sap_models import (
    AmostraFrasco,
    BlocoSAP,
    CasseteSAP,
    ComplementoSAP,
    ExameSAP,
    ImpressoraEstacaoSAP,
    LaminaSAP,
    MovimentacaoSAP,
    PacienteSUS,
    RejeicaoSAP,
)
from ..providers.implementations.sap_csv_provider import SapCsvProvider

META_DIAS_LIMITE = 20          # Meta interna de liberação de laudo (RN-02)
ALERTA_PREVENTIVO_DIAS = 15    # Alerta visual preventivo de SLA
LEI_ONCO_LIMITE = 60           # Lei Federal nº 12.732/12 (Oncologia)

# Limite esperado (em dias) por etapa para emitir alerta de retenção (RF043)
PRAZO_ETAPA_DIAS: Dict[str, int] = {
    "Recepção / Triagem": 1,
    "Macroscopia": 3,
    "Processamento Técnico": 5,
    "Microscopia": 7,
    "Revisão Patologista": 4,
}

# Mapeamento Sigla AGHU -> (Prefixo SAP, Nome do Tipo de Exame, Tipo de Peça Padrão)
MAPA_SIGLAS: Dict[str, Tuple[str, str, str]] = {
    "APECR": ("HP", "Histopatológico", "Peça Cirúrgica Geral"),
    "APSR": ("HP", "Histopatológico", "Peça Cirúrgica Geral"),
    "HPDER": ("HP", "Histopatológico", "Dermatologia / Pele"),
    "MBIOP": ("HP", "Histopatológico", "Biópsia de Mama"),
    "MPCIR": ("HP", "Histopatológico", "Peça Cirúrgica de Mama"),
    "COUT2": ("HP", "Histopatológico", "Peça de Colo Uterino"),
    "COLUT": ("HP", "Histopatológico", "Biópsia de Colo Uterino"),
    "IMUHI": ("IHQ", "Imuno-histoquímica", "Painel Imuno-histoquímico"),
    "CONGE": ("CO", "Congelação Intraoperatória", "Peça Transoperatória (Congelação)"),
    "CITOP": ("CG", "Citopatologia Geral", "Líquidos / PAAF / Citologia Geral"),
    "CPMAM": ("CG", "Citopatologia Geral", "Citopatológico de Mama"),
    "CCVM": ("CCV", "Citologia Cérvico-Vaginal", "Preventivo Colo Uterino (CCV)"),
    "CITO": ("CCV", "Citologia Cérvico-Vaginal", "Citologia Oncótica"),
}

# Lista padronizada de motivos de rejeição/não conformidade validada na reunião com o HC (págs. 6-9)
MOTIVOS_REJEICAO_PADRAO: List[str] = [
    "Quantidade de frascos divergente da solicitação",
    "Amostra sem formol / fixador inadequado",
    "Frasco derramado, quebrado ou violado",
    "Identificação do frasco divergente da requisição (Norma Zero)",
    "Descrição do material divergente do conteúdo físico (ex: inversão de topografia)",
    "Frasco vazio / material ausente no recipiente",
    "Erro de cadastro na solicitação do AGHU",
    "Solicitação duplicada ou exame de outro setor",
    "Outros",
]

ETAPAS_STATUS_AGHU: Dict[str, str] = {
    "AC": "A Coletar (AGHU)",
    "EC": "Em Coleta (AGHU)",
    "PE": "Aguardando Recebimento",
    "CO": "Coletado — Aguardando Recebimento",
    "AE": "Em Processamento (Área Executora)",
    "EX": "Em Processamento (Executando)",
    "LI": "Concluído / Laudo Liberado",
    "CA": "Cancelado",
}
PRIORIDADE_ETAPA_AGHU = ["PE", "AC", "EC", "CO", "AE", "EX", "LI", "CA"]

TERMOS_ONCO = (
    "NEOPLASIA", "CARCINOMA", "TUMOR", "MALIGN", "CANCER", "LINFOMA",
    "SARCOMA", "METASTA", "MELANOMA", "ADENOCARCINOMA", "ONCOLOG", "NEOPLASICA",
)

SIGLAS_SISCAN = {"MBIOP", "MPCIR", "COUT2", "COLUT", "CCVM", "CPMAM"}


def _agora_str() -> str:
    """Data/hora formatada no padrão brasileiro."""
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _hoje_iso() -> str:
    """Data atual no formato YYYY-MM-DD para filtros de período."""
    return date.today().isoformat()


def _normalizar(texto: str) -> str:
    """Remove acentos e converte para maiúsculas."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return sem_acento.upper()


def _parse_data_br_ou_iso(valor: Optional[str]) -> Optional[date]:
    """Aceita 'dd/mm/aaaa', 'dd/mm/aaaa HH:MM' ou 'aaaa-mm-dd'."""
    if not valor:
        return None
    texto = valor.strip()[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def _classificar_item(sigla_aghu: str, descricao_material: str = "") -> Tuple[str, str, str]:
    """Retorna (prefixo_sap, tipo_exame, tipo_peca) para uma amostra."""
    sigla = (sigla_aghu or "").upper().strip()
    prefixo, tipo, peca = MAPA_SIGLAS.get(sigla, ("HP", "Histopatológico", "Peça Cirúrgica Geral"))
    mat_norm = _normalizar(descricao_material)
    if "PROSTATA" in mat_norm:
        peca = "Biópsia / Peça de Próstata"
    elif "MAMA" in mat_norm and "Mama" not in peca:
        peca = "Mama"
    elif ("COLO UTER" in mat_norm or "ENDOCERV" in mat_norm) and "Colo" not in peca:
        peca = "Colo Uterino"
    elif any(k in mat_norm for k in (" RETO", "SIGMOIDE", "COLON", "ANTRO", "GASTRIC", "ESOFAG")):
        peca = "Endoscopia / Colonoscopia Digestiva"
    return prefixo, tipo, peca


def _requer_siscan(itens_sigla: List[str], descricao_material: str) -> bool:
    """Verifica se o exame deve ser lançado no SISCAN (Mama e Colo de Útero — reunião pág. 43)."""
    if any((s or "").upper() in SIGLAS_SISCAN for s in itens_sigla):
        return True
    mat = _normalizar(descricao_material)
    return "MAMA" in mat or "COLO UTER" in mat or "COLO DO UTERO" in mat or "CERVICO-VAGINAL" in mat


def _suspeita_neoplasia(itens: List[Dict[str, str]]) -> bool:
    """Identifica suspeita oncológica pelas informações clínicas, material ou especialidade."""
    for item in itens:
        texto = _normalizar(
            " ".join([
                item.get("informacoes_clinica", ""),
                item.get("descricao_material", ""),
                item.get("especialidade", ""),
            ])
        )
        if any(termo in texto for termo in TERMOS_ONCO):
            return True
    return False


def _interpretar_codigo_bipado(codigo: str) -> Tuple[str, Optional[str]]:
    """
    Interpreta o código lido pela pistola/bipador HID (reunião pág. 14):
    - Se tiver 10 dígitos numéricos (ex: '1479367001'), os 7 primeiros são a solicitação ('1479367')
      e os 3 últimos são o número da amostra ('1').
    - Caso contrário, retorna o próprio código limpo.
    """
    limpo = (codigo or "").strip()
    somente_digitos = "".join(ch for ch in limpo if ch.isdigit())
    if len(somente_digitos) == 10 and limpo.isdigit():
        solicitacao = somente_digitos[:7]
        amostra = str(int(somente_digitos[7:])) if int(somente_digitos[7:]) > 0 else "1"
        return solicitacao, amostra
    return limpo, None


async def _registrar_movimentacao(
    db: AsyncSession,
    exame_id: int,
    codigo_subproduto: str,
    tipo_subproduto: str,
    etapa: str,
    acao: str,
    perfil: str,
    operador: str,
) -> MovimentacaoSAP:
    """Insere um registro imutável na tabela sap_movimentacoes (RF040, RNF010)."""
    mov = MovimentacaoSAP(
        exame_id=exame_id,
        codigo_subproduto=codigo_subproduto,
        tipo_subproduto=tipo_subproduto,
        etapa=etapa,
        acao=acao,
        perfil=perfil or "Operador SAP",
        operador=operador or "admin",
        timestamp=_agora_str(),
    )
    db.add(mov)
    return mov


async def _gerar_proximo_codigo_sap(db: AsyncSession, prefixo: str) -> str:
    """Gera código único sequencial anual por prefixo, ex: HP-2026-001, CO-2026-001 (RF009, RNF011)."""
    ano = datetime.now().year
    padrao = f"{prefixo}-{ano}-%"
    stmt = select(func.count(ExameSAP.id)).where(ExameSAP.codigo_sap.like(padrao))
    total = (await db.execute(stmt)).scalar() or 0
    seq = total + 1
    while True:
        candidato = f"{prefixo}-{ano}-{seq:03d}"
        existe = (await db.execute(select(ExameSAP.id).where(ExameSAP.codigo_sap == candidato))).scalar_one_or_none()
        if not existe:
            return candidato
        seq += 1


# =====================================================================
# 1. IMPRESSORAS E ETIQUETAS ZPL / FICHA DE TRABALHO (RF010, RF054, RF055)
# =====================================================================

async def garantir_impressoras_padrao(db: AsyncSession) -> List[ImpressoraEstacaoSAP]:
    """Garante as 4 estações de impressão térmica configuradas por padrão (RF055)."""
    stmt = select(ImpressoraEstacaoSAP)
    existentes = list((await db.execute(stmt)).scalars().all())
    if existentes:
        return existentes

    padroes = [
        ImpressoraEstacaoSAP(
            estacao="Triagem / Recepção",
            nome_impressora="ZEBRA-SAP-RECEP-01",
            fabricante_modelo="Zebra ZD220 (Térmica Direta / Transferência)",
            linguagem="ZPL",
            endereco_conexao="tcp://10.22.14.51:9100",
            dpi=203,
            tamanho_etiqueta="50x30mm (Frasco Resistente a Formol)",
            impressao_automatica=True,
        ),
        ImpressoraEstacaoSAP(
            estacao="Macroscopia",
            nome_impressora="ARGOX-SAP-MACRO-01",
            fabricante_modelo="Argox OS-214 Plus / Zebra GK420t",
            linguagem="ZPL",
            endereco_conexao="tcp://10.22.14.52:9100",
            dpi=203,
            tamanho_etiqueta="30x15mm (Cassete Resistente a Xilol/Parafina)",
            impressao_automatica=True,
        ),
        ImpressoraEstacaoSAP(
            estacao="Processamento Técnico",
            nome_impressora="ZEBRA-SAP-PROC-01",
            fabricante_modelo="Zebra ZD421 Healthcare (300 DPI)",
            linguagem="ZPL",
            endereco_conexao="tcp://10.22.14.53:9100",
            dpi=300,
            tamanho_etiqueta="22x19mm (Lâmina Microscopia Resistente a Reagentes)",
            impressao_automatica=True,
        ),
        ImpressoraEstacaoSAP(
            estacao="Microscopia",
            nome_impressora="ZEBRA-SAP-MICRO-01",
            fabricante_modelo="Zebra ZD220",
            linguagem="ZPL",
            endereco_conexao="tcp://10.22.14.54:9100",
            dpi=203,
            tamanho_etiqueta="22x19mm (Etiqueta de Revisão / Arquivo)",
            impressao_automatica=False,
        ),
    ]
    db.add_all(padroes)
    await db.commit()
    return padroes


def gerar_zpl_etiqueta(
    codigo_principal: str,
    qr_code: str,
    nome_paciente: str,
    segundo_identificador: str,
    descricao_item: str,
    solicitacao_aghu: str,
) -> str:
    """
    Gera o comando ZPL II (Zebra Programming Language) para etiqueta térmica com QR Code.
    Segue a Norma Zero do HC-UFPE mencionada na reunião (pág. 19): 2 campos de identificação
    do paciente (Nome + Prontuário/Data de Nascimento), além do código SAP e nº AGHU.
    """
    pac = (nome_paciente or "PACIENTE")[:28]
    id2 = (segundo_identificador or "S/PRONT")[:28]
    desc = (descricao_item or "")[:30]
    return (
        "^XA\n"
        "^CI28\n"
        "^PW400\n"
        "^LL240\n"
        f"^FO18,16^A0N,28,28^FD{codigo_principal}^FS\n"
        f"^FO18,48^A0N,20,20^FDPac: {pac}^FS\n"
        f"^FO18,72^A0N,18,18^FD{id2}^FS\n"
        f"^FO18,96^A0N,18,18^FDAGHU #{solicitacao_aghu}^FS\n"
        f"^FO18,120^A0N,18,18^FD{desc}^FS\n"
        f"^FO270,18^BQN,2,4^FDQA,{qr_code}^FS\n"
        f"^FO18,160^BY2,2,45^BCN,45,Y,N,N^FD{qr_code}^FS\n"
        "^XZ"
    )


# =====================================================================
# 2. PACIENTES EXTERNOS SUS (RF005, RF006)
# =====================================================================

async def cadastrar_ou_buscar_paciente_sus(db: AsyncSession, dados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cadastra paciente externo (SUS/Prefeituras) verificando duplicidade por CPF ou CNS (RF006).
    """
    cpf = "".join(c for c in (dados.get("cpf") or "") if c.isdigit()) or None
    cns = "".join(c for c in (dados.get("cns") or "") if c.isdigit()) or None
    nome = (dados.get("nome") or "").strip()
    data_nasc = (dados.get("data_nascimento") or "").strip()

    if not cpf and not cns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe o CPF (11 dígitos) ou o CNS (15 dígitos) do paciente SUS.",
        )

    condicoes = []
    if cpf:
        condicoes.append(PacienteSUS.cpf == cpf)
    if cns:
        condicoes.append(PacienteSUS.cns == cns)

    existente = (await db.execute(select(PacienteSUS).where(or_(*condicoes)))).scalar_one_or_none()
    if existente:
        return {
            "ja_existia": True,
            "mensagem": "Paciente já cadastrado na base local SUS. Registro recuperado.",
            "paciente": {
                "id": existente.id,
                "nome": existente.nome,
                "cpf": existente.cpf,
                "cns": existente.cns,
                "data_nascimento": existente.data_nascimento,
                "sexo": existente.sexo,
                "telefone": existente.telefone,
                "municipio_origem": existente.municipio_origem,
                "unidade_solicitante": existente.unidade_solicitante,
            },
        }

    if len(nome) < 3 or not data_nasc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para novo cadastro SUS, informe Nome Completo e Data de Nascimento.",
        )

    novo = PacienteSUS(
        nome=nome,
        cpf=cpf,
        cns=cns,
        data_nascimento=data_nasc,
        sexo=dados.get("sexo") or "N/I",
        telefone=dados.get("telefone"),
        municipio_origem=dados.get("municipio_origem") or "Secretaria Municipal de Saúde (SUS)",
        unidade_solicitante=dados.get("unidade_solicitante") or "Unidade Externa SUS",
    )
    db.add(novo)
    await db.commit()
    await db.refresh(novo)
    return {
        "ja_existia": False,
        "mensagem": "Paciente SUS cadastrado com sucesso.",
        "paciente": {
            "id": novo.id,
            "nome": novo.nome,
            "cpf": novo.cpf,
            "cns": novo.cns,
            "data_nascimento": novo.data_nascimento,
            "sexo": novo.sexo,
            "telefone": novo.telefone,
            "municipio_origem": novo.municipio_origem,
            "unidade_solicitante": novo.unidade_solicitante,
        },
    }


async def buscar_pacientes_sus(db: AsyncSession, termo: str) -> List[Dict[str, Any]]:
    """Busca pacientes SUS por CPF, CNS ou nome."""
    q = (termo or "").strip()
    stmt = select(PacienteSUS)
    if q:
        digitos = "".join(c for c in q if c.isdigit())
        filtros = [PacienteSUS.nome.ilike(f"%{q}%")]
        if digitos:
            filtros.append(PacienteSUS.cpf.like(f"%{digitos}%"))
            filtros.append(PacienteSUS.cns.like(f"%{digitos}%"))
        stmt = stmt.where(or_(*filtros))
    stmt = stmt.order_by(PacienteSUS.id.desc()).limit(30)
    pacientes = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": p.id,
            "nome": p.nome,
            "cpf": p.cpf,
            "cns": p.cns,
            "data_nascimento": p.data_nascimento,
            "sexo": p.sexo,
            "municipio_origem": p.municipio_origem,
            "unidade_solicitante": p.unidade_solicitante,
        }
        for p in pacientes
    ]


# =====================================================================
# 3. TRIAGEM / RECEPÇÃO E CONSULTA AGHU (RF005 a RF012 + Reunião HC)
# =====================================================================

async def obter_solicitacao(
    codigo_ou_bip: str,
    provider: SapCsvProvider,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Consulta uma solicitação no AGHU (por código de 7 dígitos, bipagem de 10 dígitos 'SSSSSSSAAA',
    prontuário ou nome) e cruza com os exames e rejeições já registrados no banco local SQLite.
    Separa automaticamente os grupos de exames quando a mesma solicitação possui tipos distintos
    (ex: HP + IHQ ou CO + HP, conforme validado na reunião págs. 34-40).
    """
    codigo_sol, amostra_bipada = _interpretar_codigo_bipado(codigo_ou_bip)
    todos_itens = await provider.listar_itens()
    itens = [i for i in todos_itens if i["codigo_solicitacao"] == codigo_sol]

    # Se não achou por codigo_solicitacao exato, tenta buscar por prontuário
    if not itens:
        itens_pront = [i for i in todos_itens if i.get("prontuario") == codigo_sol]
        if itens_pront:
            codigo_sol = itens_pront[0]["codigo_solicitacao"]
            itens = [i for i in todos_itens if i["codigo_solicitacao"] == codigo_sol]

    if not itens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Solicitação '{codigo_ou_bip}' não encontrada na base do AGHU.",
        )

    primeiro = itens[0]

    # Exames já recebidos no SQLite para esta solicitação
    exames_db = list(
        (await db.execute(select(ExameSAP).where(ExameSAP.codigo_solicitacao == codigo_sol))).scalars().all()
    )
    frascos_db = list(
        (await db.execute(select(AmostraFrasco).where(AmostraFrasco.codigo_solicitacao == codigo_sol))).scalars().all()
    )
    amostras_recebidas_map = {f.numero_amostra: f for f in frascos_db}

    # Histórico de rejeições (ativas e superadas) desta solicitação
    rejeicoes_db = list(
        (await db.execute(select(RejeicaoSAP).where(RejeicaoSAP.codigo_solicitacao == codigo_sol))).scalars().all()
    )

    # Agrupa amostras por prefixo SAP (HP, IHQ, CO, CG, CCV) para suportar solicitações mistas
    grupos_exame: Dict[str, Dict[str, Any]] = {}
    amostras_formatadas: List[Dict[str, Any]] = []

    for item in sorted(itens, key=lambda x: int(x.get("numero_amostra") or "1")):
        num_amostra = item.get("numero_amostra", "1")
        prefixo, tipo_exame, tipo_peca = _classificar_item(
            item.get("sigla_exame", ""), item.get("descricao_material", "")
        )
        frasco_registrado = amostras_recebidas_map.get(num_amostra)
        exame_vinculado = next((e for e in exames_db if frasco_registrado and e.id == frasco_registrado.exame_id), None)

        cod_bip = f"{codigo_sol.zfill(7)}{int(num_amostra):03d}"
        amostra_dict = {
            "numero_amostra": num_amostra,
            "codigo_bipagem": cod_bip,
            "sigla_exame": item.get("sigla_exame", ""),
            "nome_exame": item.get("nome_exame", ""),
            "prefixo_sap": prefixo,
            "tipo_exame_sap": tipo_exame,
            "tipo_peca": tipo_peca,
            "cod_status_item": item.get("cod_status_item", ""),
            "status_item_exame": item.get("status_item_exame", ""),
            "descricao_material": item.get("descricao_material", ""),
            "ja_recebida": frasco_registrado is not None,
            "codigo_sap_recebido": exame_vinculado.codigo_sap if exame_vinculado else None,
            "qr_code_frasco": frasco_registrado.qr_code if frasco_registrado else None,
        }
        amostras_formatadas.append(amostra_dict)

        if prefixo not in grupos_exame:
            exame_do_grupo = next(
                (e for e in exames_db if e.sigla_exame == prefixo and e.status_exame != "CANCELADO"), None
            )
            grupos_exame[prefixo] = {
                "prefixo_sap": prefixo,
                "tipo_exame": tipo_exame,
                "tipo_peca": tipo_peca,
                "urgente_padrao": prefixo == "CO",
                "amostras": [],
                "ja_recebido": exame_do_grupo is not None,
                "codigo_sap": exame_do_grupo.codigo_sap if exame_do_grupo else None,
            }
        grupos_exame[prefixo]["amostras"].append(num_amostra)

    prefixo_principal = list(grupos_exame.keys())[0]
    _, tipo_principal, peca_principal = _classificar_item(
        primeiro.get("sigla_exame", ""), primeiro.get("descricao_material", "")
    )
    todas_recebidas = all(a["ja_recebida"] for a in amostras_formatadas)
    tem_congelacao = "CO" in grupos_exame
    siscan = _requer_siscan(
        [a["sigla_exame"] for a in amostras_formatadas],
        " ".join(a["descricao_material"] for a in amostras_formatadas),
    )

    return {
        "codigo_solicitacao": codigo_sol,
        "amostra_bipada_foco": amostra_bipada,
        "origem_peca": "HC",
        "nome_paciente": primeiro.get("nome_paciente", ""),
        "prontuario": primeiro.get("prontuario", ""),
        "data_nascimento": primeiro.get("data_nascimento", ""),
        "data_solicitacao": primeiro.get("data_solicitacao", ""),
        "origem": primeiro.get("origem", ""),
        "unidade": primeiro.get("unidade", ""),
        "especialidade": primeiro.get("especialidade", ""),
        "convenio": primeiro.get("convenio", "SUS"),
        "informacoes_clinica": primeiro.get("informacoes_clinica", ""),
        "prefixo_sugerido": prefixo_principal,
        "tipo_exame": tipo_principal,
        "tipo_peca": peca_principal,
        "urgente_sugerido": tem_congelacao,
        "requer_siscan": siscan,
        "multiplos_tipos_exame": len(grupos_exame) > 1,
        "grupos_exame": list(grupos_exame.values()),
        "total_amostras": len(amostras_formatadas),
        "suspeita_neoplasia_sugerida": _suspeita_neoplasia(itens),
        "ja_recebida": todas_recebidas,
        "exames_registrados": [
            {
                "id": e.id,
                "codigo_sap": e.codigo_sap,
                "sigla_exame": e.sigla_exame,
                "tipo_exame": e.tipo_exame,
                "etapa_atual": e.etapa_atual,
                "status_exame": e.status_exame,
                "qr_code": e.qr_code,
            }
            for e in exames_db
        ],
        "rejeicoes_historico": [
            {
                "id": r.id,
                "tipo_inconformidade": r.tipo_inconformidade,
                "motivo_padrao": r.motivo_padrao,
                "detalhe_outros": r.detalhe_outros,
                "data_rejeicao": r.data_rejeicao,
                "responsavel": r.responsavel,
                "superada": r.superada,
                "data_superacao": r.data_superacao,
            }
            for r in rejeicoes_db
        ],
        "amostras": amostras_formatadas,
    }


async def registrar_recebimento(
    dados: Dict[str, Any],
    provider: SapCsvProvider,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Registra a entrada física da peça (HC via AGHU ou Externa via SUS), gera o código único SAP,
    cria os registros de Frascos individuais com QR Code e comandos ZPL de impressão térmica,
    marca eventuais rejeições anteriores como 'superadas' (mantendo-as no histórico) e gera
    a Ficha de Trabalho única da Recepção (RF005 a RF012).
    """
    origem_peca = (dados.get("origem_peca") or "HC").upper()
    operador = dados.get("operador") or "recepcionista.sap"
    perfil = dados.get("perfil_usuario") or "Recepcionista"

    if origem_peca == "SUS":
        # Recepção Externa SUS (RF005, RF006, RF009)
        paciente_sus_id = dados.get("paciente_sus_id")
        pac = None
        if paciente_sus_id:
            pac = (await db.execute(select(PacienteSUS).where(PacienteSUS.id == int(paciente_sus_id)))).scalar_one_or_none()
        if not pac:
            res_pac = await cadastrar_ou_buscar_paciente_sus(db, dados.get("paciente_sus") or dados)
            pac_info = res_pac["paciente"]
        else:
            pac_info = {
                "id": pac.id,
                "nome": pac.nome,
                "cpf": pac.cpf,
                "cns": pac.cns,
                "data_nascimento": pac.data_nascimento,
                "sexo": pac.sexo,
                "municipio_origem": pac.municipio_origem,
                "unidade_solicitante": pac.unidade_solicitante,
            }

        prefixo = (dados.get("prefixo_exame") or "HP").upper()
        mapa_tipo = {
            "HP": "Histopatológico",
            "CO": "Congelação Intraoperatória",
            "IHQ": "Imuno-histoquímica",
            "CG": "Citopatologia Geral",
            "CCV": "Citologia Cérvico-Vaginal",
        }
        tipo_exame = mapa_tipo.get(prefixo, "Histopatológico")
        codigo_sol = dados.get("codigo_solicitacao") or f"SUS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        amostras_input = dados.get("amostras_sus") or [
            {"numero_amostra": "1", "descricao_material": dados.get("descricao_material") or "Biópsia / Peça Externa SUS"}
        ]
        nome_paciente = pac_info["nome"]
        prontuario = f"CNS:{pac_info.get('cns') or pac_info.get('cpf') or 'SUS'}"
        cpf_pac = pac_info.get("cpf")
        cns_pac = pac_info.get("cns")
        data_nasc = pac_info.get("data_nascimento", "")
        sexo_pac = pac_info.get("sexo", "N/I")
        data_sol = datetime.now().strftime("%d/%m/%Y")
        origem_unidade = f"SUS Externo — {pac_info.get('municipio_origem') or 'Prefeitura'}"
        especialidade = dados.get("especialidade") or "Rede Externa SUS"
        info_clinicas = dados.get("informacoes_clinicas") or "Encaminhamento externo SUS."
        desc_concat = " | ".join(a.get("descricao_material", "") for a in amostras_input)
        _, _, tipo_peca = _classificar_item(prefixo, desc_concat)
        siscan = _requer_siscan([prefixo], desc_concat)
    else:
        # Recepção Interna HC-UFPE integrada ao AGHU (RF007, RF008)
        sol = await obter_solicitacao(dados["codigo_solicitacao"], provider, db)
        codigo_sol = sol["codigo_solicitacao"]
        amostras_marcadas = [str(n) for n in (dados.get("amostras_conferidas") or [])]
        if not amostras_marcadas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selecione/confira ao menos um frasco físico antes de confirmar o recebimento.",
            )

        # Filtra amostras conferidas que ainda não foram recebidas
        amostras_selecionadas = [
            a for a in sol["amostras"] if str(a["numero_amostra"]) in amostras_marcadas and not a["ja_recebida"]
        ]
        if not amostras_selecionadas:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="As amostras selecionadas já foram recebidas anteriormente no SAP.",
            )

        # Se um filtro de prefixo específico foi pedido (ex: receber apenas HP primeiro e deixar IHQ aguardando)
        prefixo_filtro = dados.get("prefixo_exame")
        if prefixo_filtro:
            amostras_selecionadas = [
                a for a in amostras_selecionadas if a["prefixo_sap"] == prefixo_filtro.upper()
            ]
            if not amostras_selecionadas:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Nenhuma amostra pendente para o tipo {prefixo_filtro} nesta seleção.",
                )

        # Permite sobrescrever a descrição individual do material por amostra se editada na conferência
        descricoes_custom = dados.get("descricoes_amostras") or {}
        amostras_input = [
            {
                "numero_amostra": a["numero_amostra"],
                "sigla_aghu": a["sigla_exame"],
                "nome_exame_aghu": a["nome_exame"],
                "descricao_material": descricoes_custom.get(str(a["numero_amostra"])) or a["descricao_material"],
            }
            for a in amostras_selecionadas
        ]
        prefixo = amostras_selecionadas[0]["prefixo_sap"]
        tipo_exame = amostras_selecionadas[0]["tipo_exame_sap"]
        tipo_peca = dados.get("tipo_peca") or amostras_selecionadas[0]["tipo_peca"]
        nome_paciente = sol["nome_paciente"]
        prontuario = sol["prontuario"]
        cpf_pac = dados.get("cpf_paciente")
        cns_pac = dados.get("cns_paciente")
        data_nasc = sol["data_nascimento"]
        sexo_pac = dados.get("sexo_paciente") or "N/I"
        data_sol = sol["data_solicitacao"]
        origem_unidade = f"{sol['origem']} — {sol['unidade']}"
        especialidade = sol["especialidade"]
        info_clinicas = sol["informacoes_clinica"]
        siscan = sol["requer_siscan"]

    # Gera código SAP único (ex: HP-2026-001, CO-2026-001, IHQ-2026-001)
    codigo_sap = await _gerar_proximo_codigo_sap(db, prefixo)
    qr_code_exame = f"SAP-QR-{codigo_sap}"
    urgente = bool(dados.get("urgente")) or (prefixo == "CO")

    # Verifica se já há um exame anterior (ex: HP ou CO) na mesma solicitação para criar vínculo automático
    exame_anterior = (
        await db.execute(
            select(ExameSAP)
            .where(ExameSAP.codigo_solicitacao == codigo_sol, ExameSAP.status_exame != "CANCELADO")
            .order_by(ExameSAP.id.asc())
        )
    ).scalars().first()
    vinculo_codigo = dados.get("exame_origem_codigo") or (exame_anterior.codigo_sap if exame_anterior else None)

    estagio = dados.get("estagio_entrada") or "Peça a Fresco / Formol (Para Macroscopia)"
    enviar_direto_macro = bool(dados.get("enviar_macroscopia", True))
    if "Bloco" in estagio:
        etapa_inicial = "Processamento Técnico"
    elif "Lâmina" in estagio:
        etapa_inicial = "Microscopia"
    elif enviar_direto_macro:
        etapa_inicial = "Macroscopia"
    else:
        etapa_inicial = "Recepção / Triagem"

    novo_exame = ExameSAP(
        codigo_sap=codigo_sap,
        qr_code=qr_code_exame,
        codigo_solicitacao=codigo_sol,
        origem_peca=origem_peca,
        nome_paciente=nome_paciente,
        prontuario_paciente=prontuario,
        cpf_paciente=cpf_pac,
        cns_paciente=cns_pac,
        data_nascimento=data_nasc,
        sexo_paciente=sexo_pac,
        data_solicitacao=data_sol,
        origem_unidade=origem_unidade,
        especialidade=especialidade,
        informacoes_clinicas=info_clinicas,
        sigla_exame=prefixo,
        tipo_exame=tipo_exame,
        tipo_peca=tipo_peca,
        urgente=urgente,
        motivo_urgencia=dados.get("motivo_urgencia") or ("Congelação Intraoperatória" if prefixo == "CO" else None),
        suspeita_neoplasia=bool(dados.get("suspeita_neoplasia")),
        requer_siscan=siscan,
        estagio_entrada=estagio,
        observacao_recepcao=dados.get("observacao_recepcao"),
        etapa_atual=etapa_inicial,
        status_exame="ATIVO",
        exame_origem_codigo=vinculo_codigo,
        responsavel_recepcao=operador,
        data_recebimento=_agora_str(),
    )
    db.add(novo_exame)
    await db.flush()

    # Cria os Frascos individuais e suas etiquetas ZPL (RF010 + Norma Zero HC)
    etiquetas_frascos: List[Dict[str, Any]] = []
    segundo_id_paciente = f"Pront: {prontuario} | Nasc: {data_nasc}"

    for am in amostras_input:
        num = str(am.get("numero_amostra") or "1")
        qr_frasco = f"{codigo_sap}-F{num}"
        cod_bip = f"{codigo_sol.zfill(7)}{int(num) if num.isdigit() else 1:03d}"
        frasco = AmostraFrasco(
            exame_id=novo_exame.id,
            codigo_solicitacao=codigo_sol,
            numero_amostra=num,
            codigo_bipagem=cod_bip,
            qr_code=qr_frasco,
            sigla_aghu=am.get("sigla_aghu") or prefixo,
            nome_exame_aghu=am.get("nome_exame_aghu") or tipo_exame,
            descricao_material=am.get("descricao_material") or f"Frasco #{num}",
            status_frasco="Encaminhado para Macroscopia" if etapa_inicial == "Macroscopia" else "Recebido na Triagem",
            responsavel_atual=operador,
        )
        db.add(frasco)
        etiquetas_frascos.append({
            "numero_amostra": num,
            "qr_code": qr_frasco,
            "codigo_bipagem": cod_bip,
            "nome_paciente": nome_paciente,
            "segundo_identificador": segundo_id_paciente,
            "descricao_material": frasco.descricao_material,
            "zpl": gerar_zpl_etiqueta(
                codigo_principal=f"{codigo_sap} (Frasco #{num})",
                qr_code=qr_frasco,
                nome_paciente=nome_paciente,
                segundo_identificador=segundo_id_paciente,
                descricao_item=f"Amostra {num}: {frasco.descricao_material}",
                solicitacao_aghu=codigo_sol,
            ),
        })

    # Se havia rejeições ativas para esta solicitação, marca como superadas mantendo no histórico! (Reunião pág. 8)
    rejeicoes_ativas = (
        await db.execute(
            select(RejeicaoSAP).where(
                RejeicaoSAP.codigo_solicitacao == codigo_sol,
                RejeicaoSAP.superada.is_(False),
            )
        )
    ).scalars().all()
    for rej in rejeicoes_ativas:
        rej.superada = True
        rej.data_superacao = _agora_str()

    await _registrar_movimentacao(
        db=db,
        exame_id=novo_exame.id,
        codigo_subproduto=codigo_sap,
        tipo_subproduto="EXAME",
        etapa="Recepção / Triagem",
        acao=f"Recebimento de {len(amostras_input)} amostra(s) registrado ({origem_peca}). "
             f"Código gerado: {codigo_sap}. Encaminhado para: {etapa_inicial}.",
        perfil=perfil,
        operador=operador,
    )

    await db.commit()
    await db.refresh(novo_exame)

    # Ficha de Trabalho Única impressa na Recepção com descrição por amostra (Reunião págs. 20-22)
    ficha_trabalho = {
        "titulo": "FICHA DE TRABALHO — SERVIÇO DE ANATOMIA PATOLÓGICA (HC-UFPE)",
        "codigo_sap": codigo_sap,
        "qr_code": qr_code_exame,
        "codigo_solicitacao": codigo_sol,
        "origem_peca": origem_peca,
        "nome_paciente": nome_paciente,
        "prontuario": prontuario,
        "data_nascimento": data_nasc,
        "origem_unidade": origem_unidade,
        "especialidade": especialidade,
        "tipo_exame": f"{tipo_exame} ({prefixo})",
        "urgente": urgente,
        "suspeita_neoplasia": novo_exame.suspeita_neoplasia,
        "requer_siscan": siscan,
        "exame_origem_codigo": vinculo_codigo,
        "informacoes_clinicas": info_clinicas,
        "data_recebimento": novo_exame.data_recebimento,
        "responsavel_recepcao": operador,
        "amostras": etiquetas_frascos,
    }

    return {
        "id": novo_exame.id,
        "codigo_sap": codigo_sap,
        "prefixo": prefixo,
        "tipo_exame": tipo_exame,
        "qr_code": qr_code_exame,
        "codigo_solicitacao": codigo_sol,
        "etapa_atual": etapa_inicial,
        "urgente": urgente,
        "requer_siscan": siscan,
        "exame_origem_codigo": vinculo_codigo,
        "etiquetas_frascos": etiquetas_frascos,
        "ficha_trabalho": ficha_trabalho,
        "historico": {
            "etapa": "Recepção / Triagem",
            "perfil": perfil,
            "timestamp": novo_exame.data_recebimento,
            "acao": f"Recebimento de {len(amostras_input)} amostra(s). Encaminhado para {etapa_inicial}.",
            "operador": operador,
        },
    }


async def registrar_rejeicao(dados: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """
    Registra não conformidade / rejeição de amostra ou solicitação na recepção ou bancada
    (Reunião págs. 6-9: lista fechada de motivos + campo livre se 'Outros').
    """
    motivo = (dados.get("motivo_padrao") or "").strip()
    if not motivo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selecione o motivo da não conformidade.")
    if motivo == "Outros" and not (dados.get("detalhe_outros") or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ao selecionar 'Outros', descreva o motivo específico da rejeição.",
        )

    rej = RejeicaoSAP(
        codigo_solicitacao=str(dados.get("codigo_solicitacao") or "").strip(),
        numero_amostra=str(dados.get("numero_amostra") or "Todas"),
        nome_paciente=dados.get("nome_paciente") or "Não informado",
        prontuario=dados.get("prontuario") or "N/D",
        origem_unidade=dados.get("origem_unidade") or "Unidade Solicitante",
        tipo_inconformidade=dados.get("tipo_inconformidade") or "Frasco / Material",
        motivo_padrao=motivo,
        detalhe_outros=dados.get("detalhe_outros"),
        setor_devolucao=dados.get("setor_devolucao") or "Contínuo / Setor de Origem",
        responsavel=dados.get("operador") or "recepcionista.sap",
        data_rejeicao=_agora_str(),
        superada=False,
    )
    db.add(rej)
    await db.commit()
    await db.refresh(rej)
    return {
        "id": rej.id,
        "codigo_solicitacao": rej.codigo_solicitacao,
        "numero_amostra": rej.numero_amostra,
        "nome_paciente": rej.nome_paciente,
        "prontuario": rej.prontuario,
        "origem_unidade": rej.origem_unidade,
        "tipo_inconformidade": rej.tipo_inconformidade,
        "motivo_padrao": rej.motivo_padrao,
        "detalhe_outros": rej.detalhe_outros,
        "setor_devolucao": rej.setor_devolucao,
        "responsavel": rej.responsavel,
        "data_rejeicao": rej.data_rejeicao,
        "superada": rej.superada,
    }


async def listar_rejeicoes(db: AsyncSession, incluir_superadas: bool = True) -> List[Dict[str, Any]]:
    """Lista a relação de amostras rejeitadas / devolvidas (ativas e superadas)."""
    stmt = select(RejeicaoSAP).order_by(RejeicaoSAP.id.desc())
    if not incluir_superadas:
        stmt = stmt.where(RejeicaoSAP.superada.is_(False))
    itens = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "codigo_solicitacao": r.codigo_solicitacao,
            "numero_amostra": r.numero_amostra,
            "nome_paciente": r.nome_paciente,
            "prontuario": r.prontuario,
            "origem_unidade": r.origem_unidade,
            "tipo_inconformidade": r.tipo_inconformidade,
            "motivo_padrao": r.motivo_padrao,
            "detalhe_outros": r.detalhe_outros,
            "setor_devolucao": r.setor_devolucao,
            "responsavel": r.responsavel,
            "data_rejeicao": r.data_rejeicao,
            "superada": r.superada,
            "data_superacao": r.data_superacao,
        }
        for r in itens
    ]


# =====================================================================
# 4. MACROSCOPIA (RF013 a RF018)
# =====================================================================

async def identificar_frasco_macroscopia(
    codigo: str,
    operador: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Identifica um frasco na Macroscopia por QR Code do frasco, código SAP, código de 10 dígitos
    do bipador ou número de solicitação (RF013).
    """
    termo = (codigo or "").strip()
    sol_bip, am_bip = _interpretar_codigo_bipado(termo)

    stmt_frasco = select(AmostraFrasco).where(
        or_(
            AmostraFrasco.qr_code.ilike(termo),
            AmostraFrasco.codigo_bipagem == termo,
            AmostraFrasco.codigo_solicitacao == sol_bip,
        )
    )
    frascos = list((await db.execute(stmt_frasco)).scalars().all())

    if not frascos:
        # Tenta localizar pelo codigo_sap do exame
        exame_busca = (
            await db.execute(
                select(ExameSAP).where(
                    or_(ExameSAP.codigo_sap.ilike(termo), ExameSAP.qr_code.ilike(termo))
                )
            )
        ).scalar_one_or_none()
        if exame_busca:
            frascos = list(
                (await db.execute(select(AmostraFrasco).where(AmostraFrasco.exame_id == exame_busca.id))).scalars().all()
            )

    if not frascos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum frasco recebido encontrado para '{termo}'. Realize o recebimento na Triagem primeiro.",
        )

    frasco_foco = next((f for f in frascos if am_bip and f.numero_amostra == am_bip), frascos[0])
    exame = (await db.execute(select(ExameSAP).where(ExameSAP.id == frasco_foco.exame_id))).scalar_one()

    if not frasco_foco.identificado_macroscopia:
        frasco_foco.identificado_macroscopia = True
        frasco_foco.status_frasco = "Identificado na Bancada de Macroscopia"
        frasco_foco.responsavel_atual = operador
        if exame.etapa_atual == "Recepção / Triagem":
            exame.etapa_atual = "Macroscopia"
        await _registrar_movimentacao(
            db=db,
            exame_id=exame.id,
            codigo_subproduto=frasco_foco.qr_code,
            tipo_subproduto="FRASCO",
            etapa="Macroscopia",
            acao=f"Frasco #{frasco_foco.numero_amostra} ({frasco_foco.descricao_material}) identificado na Macroscopia.",
            perfil="Macroscopista / Residente",
            operador=operador,
        )
        await db.commit()

    return await montar_visao_unificada_exame(exame, db)


async def registrar_macroscopia_e_cassetes(dados: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """
    Registra a descrição macroscópica (mantida exclusivamente no sistema - RF014), gera N cassetes
    vinculados hierarquicamente ao frasco matriz (1:N - RF015) e retorna as etiquetas ZPL dos cassetes (RF016).
    """
    exame_id = int(dados["exame_id"])
    frasco_id = int(dados["frasco_id"])
    operador = dados.get("operador") or "macroscopista.sap"
    descricao_macro = (dados.get("descricao_macroscopica") or "").strip()
    qtd_cassetes = int(dados.get("quantidade_cassetes") or 1)
    descricao_fragmentos = dados.get("descricao_fragmentos") or "Fragmentos representativos da peça"

    if not descricao_macro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A descrição macroscópica é obrigatória para concluir a etapa (RF014).",
        )
    if qtd_cassetes < 1 or qtd_cassetes > 26:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe entre 1 e 26 cassetes.")

    exame = (await db.execute(select(ExameSAP).where(ExameSAP.id == exame_id))).scalar_one_or_none()
    frasco = (await db.execute(select(AmostraFrasco).where(AmostraFrasco.id == frasco_id))).scalar_one_or_none()
    if not exame or not frasco:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exame ou frasco não encontrado.")

    exame.descricao_macroscopica = descricao_macro
    exame.data_macroscopia = _agora_str()
    exame.responsavel_macroscopia = operador
    exame.etapa_atual = "Macroscopia"
    frasco.identificado_macroscopia = True
    frasco.status_frasco = "Clivado na Macroscopia"

    cassetes_existentes = list(
        (await db.execute(select(CasseteSAP).where(CasseteSAP.frasco_id == frasco.id))).scalars().all()
    )
    offset_letra = len(cassetes_existentes)
    novos_cassetes: List[Dict[str, Any]] = []

    for idx in range(qtd_cassetes):
        letra = chr(ord("A") + ((offset_letra + idx) % 26))
        sufixo = f"{letra}{(offset_letra + idx) // 26 or ''}"
        cod_cassete = f"{exame.codigo_sap}-F{frasco.numero_amostra}-{sufixo}"
        qr_cassete = f"CAS-{cod_cassete}"
        cassete = CasseteSAP(
            exame_id=exame.id,
            frasco_id=frasco.id,
            codigo_cassete=cod_cassete,
            qr_code=qr_cassete,
            sigla_cassete=sufixo,
            descricao_fragmentos=f"{frasco.descricao_material} ({descricao_fragmentos} - Cassete {sufixo})",
            identidade_confirmada_macro=bool(dados.get("confirmar_identidade_automatico", False)),
            status_cassete="Gerado na Macroscopia",
            responsavel_criacao=operador,
        )
        db.add(cassete)
        novos_cassetes.append({
            "codigo_cassete": cod_cassete,
            "qr_code": qr_cassete,
            "sigla_cassete": sufixo,
            "zpl": gerar_zpl_etiqueta(
                codigo_principal=cod_cassete,
                qr_code=qr_cassete,
                nome_paciente=exame.nome_paciente,
                segundo_identificador=f"Pront: {exame.prontuario_paciente}",
                descricao_item=f"Cassete {sufixo} - {frasco.descricao_material}",
                solicitacao_aghu=exame.codigo_solicitacao,
            ),
        })

    await _registrar_movimentacao(
        db=db,
        exame_id=exame.id,
        codigo_subproduto=frasco.qr_code,
        tipo_subproduto="CASSETE",
        etapa="Macroscopia",
        acao=f"Macroscopia registrada e {qtd_cassetes} cassete(s) gerado(s) para o Frasco #{frasco.numero_amostra}.",
        perfil="Macroscopista",
        operador=operador,
    )
    await db.commit()
    return {
        "mensagem": f"Macroscopia salva e {qtd_cassetes} cassete(s) gerado(s) com etiquetas QR Code.",
        "cassetes_gerados": novos_cassetes,
        "exame": await montar_visao_unificada_exame(exame, db),
    }


async def confirmar_e_enviar_cassetes_processamento(dados: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """
    Confirma a identidade dos cassetes (por leitura QR ou seleção - RF017) e registra o envio
    digital para a etapa de Processamento Técnico (RF018).
    """
    exame_id = int(dados["exame_id"])
    cassete_ids = [int(cid) for cid in (dados.get("cassete_ids") or [])]
    operador = dados.get("operador") or "macroscopista.sap"

    exame = (await db.execute(select(ExameSAP).where(ExameSAP.id == exame_id))).scalar_one_or_none()
    if not exame:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exame não encontrado.")

    stmt = select(CasseteSAP).where(CasseteSAP.exame_id == exame.id)
    if cassete_ids:
        stmt = stmt.where(CasseteSAP.id.in_(cassete_ids))
    cassetes = list((await db.execute(stmt)).scalars().all())
    if not cassetes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gere ao menos um cassete antes de enviar.")

    for c in cassetes:
        c.identidade_confirmada_macro = True
        c.enviado_processamento = True
        c.status_cassete = "Enviado ao Processamento Técnico"

    exame.etapa_atual = "Processamento Técnico"
    await _registrar_movimentacao(
        db=db,
        exame_id=exame.id,
        codigo_subproduto=exame.codigo_sap,
        tipo_subproduto="CASSETE",
        etapa="Macroscopia → Processamento Técnico",
        acao=f"Identidade confirmada e {len(cassetes)} cassete(s) enviado(s) digitalmente para Processamento Técnico.",
        perfil="Macroscopista",
        operador=operador,
    )
    await db.commit()
    return await montar_visao_unificada_exame(exame, db)


# =====================================================================
# 5. PROCESSAMENTO TÉCNICO (RF019 a RF032)
# =====================================================================

async def registrar_etapa_processamento_tecnico(dados: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """
    Executa as operações do Processamento Técnico (RF019 a RF032):
    - 'INICIAR_PROCESSAMENTO' (RF019, RF020): identifica cassetes e registra início do processamento de tecidos.
    - 'GERAR_BLOCOS' (RF021, RF022): registra inclusão em parafina e gera blocos vinculados ao cassete (1:N).
    - 'CORTE_GERAR_LAMINAS' (RF023, RF024, RF027): registra corte e gera N lâminas vinculadas ao bloco (1:N) com ZPL.
    - 'COLORACAO_E_LIBERACAO' (RF025, RF026): registra coloração/montagem e liberação técnica das lâminas.
    - 'ENVIAR_MICROSCOPIA' (RF028, RF030): confirma identidade das lâminas e envia para Microscopia.
    - 'ARQUIVAR_BLOCOS' (RF029, RF031): confirma identidade dos blocos de parafina e encaminha ao arquivo físico.
    """
    acao_proc = (dados.get("acao_processamento") or "").upper()
    exame_id = int(dados["exame_id"])
    operador = dados.get("operador") or "tecnico.lab"

    exame = (await db.execute(select(ExameSAP).where(ExameSAP.id == exame_id))).scalar_one_or_none()
    if not exame:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exame não encontrado.")

    agora = _agora_str()

    if acao_proc == "INICIAR_PROCESSAMENTO":
        cassetes = list((await db.execute(select(CasseteSAP).where(CasseteSAP.exame_id == exame.id))).scalars().all())
        if not cassetes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exame não possui cassetes.")
        for c in cassetes:
            c.identificado_processamento = True
            c.processamento_iniciado = True
            c.data_inicio_processamento = agora
            c.tecnico_processamento = operador
            c.status_cassete = "Em Processamento de Tecidos (Histotécnico)"
        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "CASSETE", "Processamento Técnico",
            f"Identificação confirmada e processamento de tecidos iniciado em {len(cassetes)} cassete(s).",
            "Técnico de Laboratório", operador,
        )

    elif acao_proc == "GERAR_BLOCOS":
        cassete_id = dados.get("cassete_id")
        qtd_blocos = int(dados.get("quantidade_blocos") or 1)
        stmt_c = select(CasseteSAP).where(CasseteSAP.exame_id == exame.id)
        if cassete_id:
            stmt_c = stmt_c.where(CasseteSAP.id == int(cassete_id))
        cassetes = list((await db.execute(stmt_c)).scalars().all())
        if not cassetes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cassete não encontrado.")

        total_criados = 0
        for c in cassetes:
            c.identificado_processamento = True
            c.processamento_iniciado = True
            c.status_cassete = "Incluído em Bloco de Parafina"
            existentes = list((await db.execute(select(BlocoSAP).where(BlocoSAP.cassete_id == c.id))).scalars().all())
            for i in range(qtd_blocos):
                num_b = len(existentes) + i + 1
                cod_bloco = f"{c.codigo_cassete}-B{num_b}"
                bloco = BlocoSAP(
                    exame_id=exame.id,
                    cassete_id=c.id,
                    codigo_bloco=cod_bloco,
                    qr_code=f"BLK-{cod_bloco}",
                    responsavel_inclusao=operador,
                    data_inclusao=agora,
                )
                db.add(bloco)
                total_criados += 1

        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "BLOCO", "Inclusão em Parafina",
            f"Inclusão realizada: {total_criados} bloco(s) de parafina gerado(s) e vinculado(s) aos cassetes.",
            "Técnico de Laboratório", operador,
        )

    elif acao_proc == "CORTE_GERAR_LAMINAS":
        bloco_id = dados.get("bloco_id")
        qtd_laminas = int(dados.get("quantidade_laminas") or 1)
        coloracao = dados.get("tipo_coloracao") or "H&E (Hematoxilina-Eosina)"
        marcador_ihq = dados.get("marcador_ihq")

        stmt_b = select(BlocoSAP).where(BlocoSAP.exame_id == exame.id)
        if bloco_id:
            stmt_b = stmt_b.where(BlocoSAP.id == int(bloco_id))
        blocos = list((await db.execute(stmt_b)).scalars().all())
        if not blocos:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gere os blocos de parafina primeiro.")

        total_laminas = 0
        for b in blocos:
            b.realizou_corte = True
            b.data_corte = agora
            b.responsavel_corte = operador
            existentes = list((await db.execute(select(LaminaSAP).where(LaminaSAP.bloco_id == b.id))).scalars().all())
            for i in range(qtd_laminas):
                num_l = len(existentes) + i + 1
                cod_lamina = f"{b.codigo_bloco}-L{num_l}"
                lam = LaminaSAP(
                    exame_id=exame.id,
                    bloco_id=b.id,
                    codigo_lamina=cod_lamina,
                    qr_code=f"LAM-{cod_lamina}",
                    tipo_coloracao=coloracao,
                    marcador_ihq=marcador_ihq,
                    status_lamina="Corte Realizado (Aguardando Coloração)",
                )
                db.add(lam)
                total_laminas += 1

        # Se havia pedidos de complemento pendentes para este exame, marca como atendidos
        complementos = list(
            (await db.execute(
                select(ComplementoSAP).where(
                    ComplementoSAP.exame_id == exame.id,
                    ComplementoSAP.status_pedido == "Pendente no Processamento",
                )
            )).scalars().all()
        )
        for comp in complementos:
            comp.status_pedido = "Atendido — Lâminas Recortadas"
            comp.responsavel_atendimento = operador
            comp.data_conclusao = agora

        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "LAMINA", "Microtomia / Corte",
            f"Corte realizado e {total_laminas} lâmina(s) gerada(s) ({coloracao}"
            f"{f' - Marcador: {marcador_ihq}' if marcador_ihq else ''}).",
            "Técnico de Laboratório", operador,
        )

    elif acao_proc == "COLORACAO_E_LIBERACAO":
        laminas = list((await db.execute(select(LaminaSAP).where(LaminaSAP.exame_id == exame.id))).scalars().all())
        if not laminas:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gere as lâminas no corte primeiro.")
        for l in laminas:
            l.coloracao_montagem_ok = True
            l.data_coloracao = agora
            l.responsavel_coloracao = operador
            l.liberada_tecnica = True
            l.data_liberacao_tecnica = agora
            l.responsavel_liberacao = operador
            l.status_lamina = "Corada, Montada e Liberada pela Técnica"

        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "LAMINA", "Coloração, Montagem e Liberação Técnica",
            f"Coloração, montagem e liberação técnica concluídas para {len(laminas)} lâmina(s).",
            "Técnico de Laboratório", operador,
        )

    elif acao_proc == "ENVIAR_MICROSCOPIA":
        laminas = list((await db.execute(select(LaminaSAP).where(LaminaSAP.exame_id == exame.id))).scalars().all())
        if not laminas:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma lâmina disponível para envio.")
        for l in laminas:
            l.coloracao_montagem_ok = True
            l.liberada_tecnica = True
            l.identidade_confirmada = True
            l.enviada_microscopia = True
            l.status_lamina = "Enviada para Microscopia"
        exame.etapa_atual = "Microscopia"
        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "LAMINA", "Processamento → Microscopia",
            f"Identidade confirmada (RF028) e {len(laminas)} lâmina(s) encaminhada(s) para Microscopia (RF030).",
            "Técnico de Laboratório", operador,
        )

    elif acao_proc == "ARQUIVAR_BLOCOS":
        local_arq = dados.get("local_arquivo") or "Bloco-Arquivo-Gaveta-01"
        blocos = list((await db.execute(select(BlocoSAP).where(BlocoSAP.exame_id == exame.id))).scalars().all())
        if not blocos:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum bloco para arquivar.")
        for b in blocos:
            b.identidade_confirmada_arquivo = True
            b.arquivado = True
            b.local_arquivo = local_arq
            b.data_arquivamento = agora
        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "BLOCO", "Arquivamento de Blocos",
            f"Identidade confirmada (RF029) e {len(blocos)} bloco(s) arquivado(s) em '{local_arq}' (RF031).",
            "Técnico de Laboratório", operador,
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ação desconhecida: {acao_proc}")

    await db.commit()
    return await montar_visao_unificada_exame(exame, db)


# =====================================================================
# 6. MICROSCOPIA, LAUDO PRÉVIO, REVISÃO E COMPLEMENTOS (RF033 a RF039)
# =====================================================================

async def registrar_acao_microscopia(dados: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """
    Executa as operações da Microscopia (RF033 a RF039):
    - 'IDENTIFICAR_LAMINA' (RF033)
    - 'SALVAR_LAUDO_PREVIO' (RF034 - Residente)
    - 'REVISAR_PATOLOGISTA' (RF035 - Aprovar / Reprovar / Inacabado)
    - 'SOLICITAR_COMPLEMENTO' (RF032, RF036, RF037 - IHQ, Novos Cortes, Coloração Especial, Revisão Macro)
    - 'LIBERAR_EXAME' (RF038 - Marcação de exame como liberado + vínculo CO->HP se aplicável)
    - 'ARQUIVAR_LAMINAS' (RF039 - Encaminhamento de lâminas para arquivo físico)
    - 'REGISTRAR_SISCAN' (Lançamento no SISCAN para casos de mama e colo de útero)
    """
    acao = (dados.get("acao_microscopia") or "").upper()
    exame_id = int(dados["exame_id"])
    operador = dados.get("operador") or "patologista.sap"
    perfil = dados.get("perfil") or "Médico Patologista"
    agora = _agora_str()

    exame = (await db.execute(select(ExameSAP).where(ExameSAP.id == exame_id))).scalar_one_or_none()
    if not exame:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exame não encontrado.")

    if acao == "IDENTIFICAR_LAMINA":
        laminas = list((await db.execute(select(LaminaSAP).where(LaminaSAP.exame_id == exame.id))).scalars().all())
        for l in laminas:
            l.identificada_microscopia = True
            l.status_lamina = "Em Análise na Microscopia"
        exame.etapa_atual = "Microscopia"
        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "LAMINA", "Microscopia",
            f"Lâmina(s) identificada(s) no microscópio para análise diagnóstica (RF033).",
            perfil, operador,
        )

    elif acao == "SALVAR_LAUDO_PREVIO":
        texto_laudo = (dados.get("laudo_previo") or "").strip()
        if not texto_laudo:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Digite o texto do laudo prévio.")
        exame.laudo_previo_residente = texto_laudo
        exame.diagnostico_associado = (dados.get("diagnostico_associado") or "").strip() or exame.diagnostico_associado
        exame.residente_responsavel = operador
        exame.data_laudo_previo = agora
        exame.status_revisao_patologista = "PENDENTE"
        exame.etapa_atual = "Revisão Patologista"
        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "EXAME", "Laudo Prévio (Residente)",
            "Laudo prévio elaborado pelo residente e encaminhado para revisão do Médico Patologista (RF034).",
            "Residente", operador,
        )

    elif acao == "REVISAR_PATOLOGISTA":
        decisao = (dados.get("decisao") or "APROVADO").upper()  # APROVADO, REPROVADO, INACABADO
        exame.status_revisao_patologista = decisao
        exame.observacao_revisao = dados.get("observacao_revisao")
        exame.patologista_revisor = operador
        if dados.get("diagnostico_associado"):
            exame.diagnostico_associado = dados.get("diagnostico_associado")
        if decisao == "REPROVADO":
            exame.etapa_atual = "Microscopia"
        elif decisao == "INACABADO":
            exame.etapa_atual = "Processamento Técnico"
        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "EXAME", "Revisão do Patologista",
            f"Laudo prévio avaliado pelo Médico Patologista: {decisao} (RF035). "
            f"{dados.get('observacao_revisao') or ''}".strip(),
            "Médico Patologista", operador,
        )

    elif acao == "SOLICITAR_COMPLEMENTO":
        tipo_pedido = (dados.get("tipo_pedido") or "IHQ").upper()
        marcadores = (dados.get("marcadores") or "").strip()
        justificativa = (dados.get("justificativa") or "Elucidação diagnóstica complementar").strip()

        comp = ComplementoSAP(
            exame_id=exame.id,
            bloco_id=dados.get("bloco_id"),
            tipo_pedido=tipo_pedido,
            marcadores=marcadores,
            justificativa=justificativa,
            solicitante=operador,
            data_solicitacao=agora,
            status_pedido="Pendente no Processamento",
        )
        exame.status_revisao_patologista = "INACABADO"

        # Se for pedido de IHQ, permite abrir automaticamente um exame IHQ vinculado (RN-05 / Reunião pág. 36)
        if tipo_pedido == "IHQ" and dados.get("gerar_exame_ihq_vinculado", True):
            cod_ihq = await _gerar_proximo_codigo_sap(db, "IHQ")
            exame_ihq = ExameSAP(
                codigo_sap=cod_ihq,
                qr_code=f"SAP-QR-{cod_ihq}",
                codigo_solicitacao=exame.codigo_solicitacao,
                origem_peca=exame.origem_peca,
                nome_paciente=exame.nome_paciente,
                prontuario_paciente=exame.prontuario_paciente,
                cpf_paciente=exame.cpf_paciente,
                cns_paciente=exame.cns_paciente,
                data_nascimento=exame.data_nascimento,
                sexo_paciente=exame.sexo_paciente,
                data_solicitacao=agora[:10],
                origem_unidade=exame.origem_unidade,
                especialidade=exame.especialidade,
                informacoes_clinicas=f"IHQ vinculada ao exame {exame.codigo_sap}. Marcadores: {marcadores}. {justificativa}",
                sigla_exame="IHQ",
                tipo_exame="Imuno-histoquímica",
                tipo_peca="Painel Imuno-histoquímico",
                urgente=exame.urgente,
                suspeita_neoplasia=exame.suspeita_neoplasia,
                requer_siscan=False,
                estagio_entrada="Bloco de Parafina Interno (Para Recorte/IHQ)",
                etapa_atual="Processamento Técnico",
                status_exame="ATIVO",
                exame_origem_codigo=exame.codigo_sap,
                responsavel_recepcao=operador,
                data_recebimento=agora,
            )
            db.add(exame_ihq)
            await db.flush()
            comp.exame_ihq_gerado = cod_ihq

        if tipo_pedido == "REVISAO_MACRO":
            exame.etapa_atual = "Macroscopia"
        else:
            exame.etapa_atual = "Processamento Técnico"

        db.add(comp)
        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "EXAME", "Solicitação de Complemento / IHQ",
            f"Solicitado complemento '{tipo_pedido}' ({marcadores or 'Recorte/Coloração'}): {justificativa}. "
            f"Reintroduzido no fluxo técnico (RF032, RF036, RF037).",
            perfil, operador,
        )

    elif acao == "LIBERAR_EXAME":
        exame.status_revisao_patologista = "APROVADO"
        exame.patologista_revisor = operador
        exame.data_liberacao = agora
        exame.etapa_atual = "Concluído / Laudo Liberado"
        exame.status_exame = "CONCLUIDO"
        if dados.get("diagnostico_associado"):
            exame.diagnostico_associado = dados.get("diagnostico_associado")

        # RN-04: Se for Congelação (CO), garante vínculo/abertura automática da reentrada HP definitiva!
        if exame.sigla_exame == "CO":
            hp_vinculado = (
                await db.execute(
                    select(ExameSAP).where(
                        ExameSAP.codigo_solicitacao == exame.codigo_solicitacao,
                        ExameSAP.sigla_exame == "HP",
                    )
                )
            ).scalar_one_or_none()
            if not hp_vinculado:
                cod_hp = await _gerar_proximo_codigo_sap(db, "HP")
                novo_hp = ExameSAP(
                    codigo_sap=cod_hp,
                    qr_code=f"SAP-QR-{cod_hp}",
                    codigo_solicitacao=exame.codigo_solicitacao,
                    origem_peca=exame.origem_peca,
                    nome_paciente=exame.nome_paciente,
                    prontuario_paciente=exame.prontuario_paciente,
                    data_nascimento=exame.data_nascimento,
                    data_solicitacao=exame.data_solicitacao,
                    origem_unidade=exame.origem_unidade,
                    especialidade=exame.especialidade,
                    informacoes_clinicas=f"Reentrada automática pós-Congelação ({exame.codigo_sap}). {exame.informacoes_clinicas or ''}",
                    sigla_exame="HP",
                    tipo_exame="Histopatológico",
                    tipo_peca=exame.tipo_peca,
                    urgente=True,
                    suspeita_neoplasia=exame.suspeita_neoplasia,
                    requer_siscan=exame.requer_siscan,
                    estagio_entrada="Peça Pós-Congelação (Para Parafina Definitiva)",
                    etapa_atual="Macroscopia",
                    status_exame="ATIVO",
                    exame_origem_codigo=exame.codigo_sap,
                    responsavel_recepcao=operador,
                    data_recebimento=agora,
                )
                db.add(novo_hp)

        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "EXAME", "Liberação de Laudo (AGHU)",
            "Laudo oficial liberado no AGHU e exame marcado como Liberado no SAP (RF038).",
            "Médico Patologista", operador,
        )

    elif acao == "ARQUIVAR_LAMINAS":
        local_arq = dados.get("local_arquivo") or "Laminário-Armário-A1"
        laminas = list((await db.execute(select(LaminaSAP).where(LaminaSAP.exame_id == exame.id))).scalars().all())
        for l in laminas:
            l.arquivada = True
            l.local_arquivo = local_arq
            l.data_arquivamento = agora
            l.status_lamina = f"Arquivada ({local_arq})"
        exame.laminas_arquivadas = True
        exame.local_arquivo_laminas = local_arq
        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "LAMINA", "Arquivamento Físico de Lâminas",
            f"Lâminas encaminhadas e arquivadas no arquivo físico '{local_arq}' (RF039).",
            perfil, operador,
        )

    elif acao == "REGISTRAR_SISCAN":
        exame.siscan_lancado = True
        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "EXAME", "SISCAN (Ministério da Saúde)",
            "Resultado lançado no SISCAN (Sistema de Informação do Câncer — Mama/Colo Uterino).",
            perfil, operador,
        )

    elif acao == "CANCELAR_EXAME":
        motivo_canc = (dados.get("motivo_cancelamento") or "").strip()
        if not motivo_canc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe o motivo do cancelamento.")
        exame.status_exame = "CANCELADO"
        exame.etapa_atual = "Cancelado"
        exame.motivo_cancelamento = motivo_canc
        await _registrar_movimentacao(
            db, exame.id, exame.codigo_sap, "EXAME", "Cancelamento de Exame",
            f"Exame {exame.codigo_sap} cancelado individualmente: {motivo_canc}.",
            perfil, operador,
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ação inválida: {acao}")

    await db.commit()
    return await montar_visao_unificada_exame(exame, db)


# =====================================================================
# 7. VISÃO UNIFICADA, ÁRVORE HIERÁRQUICA E RASTREABILIDADE (RF040 a RF043)
# =====================================================================

async def montar_visao_unificada_exame(exame: ExameSAP, db: AsyncSession) -> Dict[str, Any]:
    """
    Constrói o objeto completo de um ExameSAP com sua Árvore Hierárquica
    (Frascos -> Cassetes -> Blocos -> Lâminas), pedidos de complementos, rejeições superadas,
    status de pré-laudo (seguro para a recepção) e histórico imutável (RF040, RF041, RF042).
    """
    frascos = list(
        (await db.execute(select(AmostraFrasco).where(AmostraFrasco.exame_id == exame.id))).scalars().all()
    )
    cassetes = list(
        (await db.execute(select(CasseteSAP).where(CasseteSAP.exame_id == exame.id))).scalars().all()
    )
    blocos = list(
        (await db.execute(select(BlocoSAP).where(BlocoSAP.exame_id == exame.id))).scalars().all()
    )
    laminas = list(
        (await db.execute(select(LaminaSAP).where(LaminaSAP.exame_id == exame.id))).scalars().all()
    )
    complementos = list(
        (await db.execute(select(ComplementoSAP).where(ComplementoSAP.exame_id == exame.id))).scalars().all()
    )
    movimentacoes = list(
        (await db.execute(
            select(MovimentacaoSAP).where(MovimentacaoSAP.exame_id == exame.id).order_by(MovimentacaoSAP.id.asc())
        )).scalars().all()
    )
    rejeicoes = list(
        (await db.execute(
            select(RejeicaoSAP).where(RejeicaoSAP.codigo_solicitacao == exame.codigo_solicitacao)
        )).scalars().all()
    )
    exames_relacionados = list(
        (await db.execute(
            select(ExameSAP).where(
                or_(
                    ExameSAP.codigo_solicitacao == exame.codigo_solicitacao,
                    ExameSAP.exame_origem_codigo == exame.codigo_sap,
                    ExameSAP.codigo_sap == (exame.exame_origem_codigo or ""),
                ),
                ExameSAP.id != exame.id,
            )
        )).scalars().all()
    )

    hoje = date.today()
    dt_base = _parse_data_br_ou_iso(exame.data_recebimento) or _parse_data_br_ou_iso(exame.data_solicitacao) or hoje
    dias_decorridos = max(0, (hoje - dt_base).days)
    limite_etapa = PRAZO_ETAPA_DIAS.get(exame.etapa_atual, 5)
    alerta_retencao_etapa = (exame.status_exame == "ATIVO") and (dias_decorridos > limite_etapa)

    # Monta a Árvore Hierárquica (Frasco -> Cassetes -> Blocos -> Lâminas) elogiada na reunião (pág. 28)
    arvore_frascos: List[Dict[str, Any]] = []
    for f in frascos:
        cassetes_do_frasco = [c for c in cassetes if c.frasco_id == f.id]
        arvore_cassetes = []
        for c in cassetes_do_frasco:
            blocos_do_cassete = [b for b in blocos if b.cassete_id == c.id]
            arvore_blocos = []
            for b in blocos_do_cassete:
                laminas_do_bloco = [l for l in laminas if l.bloco_id == b.id]
                arvore_blocos.append({
                    "id": b.id,
                    "codigo_bloco": b.codigo_bloco,
                    "qr_code": b.qr_code,
                    "realizou_corte": b.realizou_corte,
                    "data_corte": b.data_corte,
                    "responsavel_corte": b.responsavel_corte,
                    "arquivado": b.arquivado,
                    "local_arquivo": b.local_arquivo,
                    "laminas": [
                        {
                            "id": l.id,
                            "codigo_lamina": l.codigo_lamina,
                            "qr_code": l.qr_code,
                            "tipo_coloracao": l.tipo_coloracao,
                            "marcador_ihq": l.marcador_ihq,
                            "coloracao_montagem_ok": l.coloracao_montagem_ok,
                            "liberada_tecnica": l.liberada_tecnica,
                            "identidade_confirmada": l.identidade_confirmada,
                            "enviada_microscopia": l.enviada_microscopia,
                            "identificada_microscopia": l.identificada_microscopia,
                            "arquivada": l.arquivada,
                            "local_arquivo": l.local_arquivo,
                            "status_lamina": l.status_lamina,
                            "zpl": gerar_zpl_etiqueta(
                                codigo_principal=l.codigo_lamina,
                                qr_code=l.qr_code,
                                nome_paciente=exame.nome_paciente,
                                segundo_identificador=f"Pront: {exame.prontuario_paciente}",
                                descricao_item=f"{l.tipo_coloracao} {l.marcador_ihq or ''}".strip(),
                                solicitacao_aghu=exame.codigo_solicitacao,
                            ),
                        }
                        for l in laminas_do_bloco
                    ],
                })
            arvore_cassetes.append({
                "id": c.id,
                "codigo_cassete": c.codigo_cassete,
                "qr_code": c.qr_code,
                "sigla_cassete": c.sigla_cassete,
                "descricao_fragmentos": c.descricao_fragmentos,
                "identidade_confirmada_macro": c.identidade_confirmada_macro,
                "enviado_processamento": c.enviado_processamento,
                "processamento_iniciado": c.processamento_iniciado,
                "status_cassete": c.status_cassete,
                "zpl": gerar_zpl_etiqueta(
                    codigo_principal=c.codigo_cassete,
                    qr_code=c.qr_code,
                    nome_paciente=exame.nome_paciente,
                    segundo_identificador=f"Pront: {exame.prontuario_paciente}",
                    descricao_item=c.descricao_fragmentos or f"Cassete {c.sigla_cassete}",
                    solicitacao_aghu=exame.codigo_solicitacao,
                ),
                "blocos": arvore_blocos,
            })
        arvore_frascos.append({
            "id": f.id,
            "numero_amostra": f.numero_amostra,
            "codigo_bipagem": f.codigo_bipagem,
            "qr_code": f.qr_code,
            "sigla_aghu": f.sigla_aghu,
            "descricao_material": f.descricao_material,
            "status_frasco": f.status_frasco,
            "identificado_macroscopia": f.identificado_macroscopia,
            "zpl": gerar_zpl_etiqueta(
                codigo_principal=f"{exame.codigo_sap} (F#{f.numero_amostra})",
                qr_code=f.qr_code,
                nome_paciente=exame.nome_paciente,
                segundo_identificador=f"Pront: {exame.prontuario_paciente}",
                descricao_item=f"Amostra {f.numero_amostra}: {f.descricao_material}",
                solicitacao_aghu=exame.codigo_solicitacao,
            ),
            "cassetes": arvore_cassetes,
        })

    # Status de Pré-laudo visível para a Recepção dar posição ao paciente sem entregar laudo aberto (Reunião pág. 26-28)
    if exame.status_exame == "CONCLUIDO":
        status_pre_laudo = "Liberado no AGHU (Pronto para entrega)"
    elif exame.laudo_previo_residente:
        status_pre_laudo = f"Pré-laudado em {exame.data_laudo_previo} — Aguardando liberação final do Patologista"
    else:
        status_pre_laudo = "Ainda sem pré-laudo digitado"

    materiais = [f.descricao_material for f in frascos]
    ultimo_mov = movimentacoes[-1] if movimentacoes else None

    return {
        "id": exame.id,
        "codigo_sap": exame.codigo_sap,
        "qr_code": exame.qr_code,
        "codigo_solicitacao": exame.codigo_solicitacao,
        "origem_peca": exame.origem_peca,
        "nome_paciente": exame.nome_paciente,
        "prontuario_paciente": exame.prontuario_paciente,
        "cpf_paciente": exame.cpf_paciente,
        "cns_paciente": exame.cns_paciente,
        "data_nascimento": exame.data_nascimento,
        "sexo_paciente": exame.sexo_paciente,
        "data_solicitacao": exame.data_solicitacao,
        "data_recebimento": exame.data_recebimento,
        "origem": exame.origem_unidade,
        "especialidade": exame.especialidade,
        "informacoes_clinicas": exame.informacoes_clinicas,
        "tipo_exame": exame.tipo_exame,
        "sigla_exame": exame.sigla_exame,
        "tipo_peca": exame.tipo_peca,
        "urgente": exame.urgente,
        "motivo_urgencia": exame.motivo_urgencia,
        "suspeita_neoplasia": exame.suspeita_neoplasia,
        "requer_siscan": exame.requer_siscan,
        "siscan_lancado": exame.siscan_lancado,
        "exame_origem_codigo": exame.exame_origem_codigo,
        "quantidade_amostras": len(frascos) or 1,
        "quantidade_cassetes": len(cassetes),
        "quantidade_blocos": len(blocos),
        "quantidade_laminas": len(laminas),
        "descricao_material": " | ".join(materiais) or "Material Anatômico",
        "etapa_atual": exame.etapa_atual,
        "status_exame": exame.status_exame,
        "concluido": exame.status_exame == "CONCLUIDO",
        "cancelado": exame.status_exame == "CANCELADO",
        "motivo_cancelamento": exame.motivo_cancelamento,
        "dias_decorridos": dias_decorridos,
        "meta_dias_limite": META_DIAS_LIMITE,
        "lei_onco_limite": LEI_ONCO_LIMITE,
        "alerta_retencao_etapa": alerta_retencao_etapa,
        "limite_dias_etapa": limite_etapa,
        "ultimo_operador": ultimo_mov.operador if ultimo_mov else exame.responsavel_recepcao,
        "descricao_macroscopica": exame.descricao_macroscopica,
        "data_macroscopia": exame.data_macroscopia,
        "responsavel_macroscopia": exame.responsavel_macroscopia,
        "laudo_macroscopico_formal": exame.descricao_macroscopica or f"Material recebido: {' | '.join(materiais)}",
        "laudo_previo_residente": exame.laudo_previo_residente,
        "diagnostico_associado": exame.diagnostico_associado,
        "residente_responsavel": exame.residente_responsavel,
        "data_laudo_previo": exame.data_laudo_previo,
        "status_revisao_patologista": exame.status_revisao_patologista,
        "observacao_revisao": exame.observacao_revisao,
        "patologista_revisor": exame.patologista_revisor,
        "data_liberacao": exame.data_liberacao,
        "status_pre_laudo": status_pre_laudo,
        "laudo_final_aghu": status_pre_laudo,
        "laminas_arquivadas": exame.laminas_arquivadas,
        "local_arquivo_laminas": exame.local_arquivo_laminas,
        "arvore_subprodutos": arvore_frascos,
        "complementos": [
            {
                "id": comp.id,
                "tipo_pedido": comp.tipo_pedido,
                "marcadores": comp.marcadores,
                "justificativa": comp.justificativa,
                "solicitante": comp.solicitante,
                "data_solicitacao": comp.data_solicitacao,
                "status_pedido": comp.status_pedido,
                "exame_ihq_gerado": comp.exame_ihq_gerado,
                "responsavel_atendimento": comp.responsavel_atendimento,
                "data_conclusao": comp.data_conclusao,
            }
            for comp in complementos
        ],
        "rejeicoes_historico": [
            {
                "id": r.id,
                "tipo_inconformidade": r.tipo_inconformidade,
                "motivo_padrao": r.motivo_padrao,
                "detalhe_outros": r.detalhe_outros,
                "data_rejeicao": r.data_rejeicao,
                "responsavel": r.responsavel,
                "superada": r.superada,
                "data_superacao": r.data_superacao,
            }
            for r in rejeicoes
        ],
        "exames_relacionados": [
            {
                "id": er.id,
                "codigo_sap": er.codigo_sap,
                "sigla_exame": er.sigla_exame,
                "tipo_exame": er.tipo_exame,
                "etapa_atual": er.etapa_atual,
                "status_exame": er.status_exame,
            }
            for er in exames_relacionados
        ],
        "historico": [
            {
                "id": m.id,
                "codigo_subproduto": m.codigo_subproduto,
                "tipo_subproduto": m.tipo_subproduto,
                "etapa": m.etapa,
                "acao": m.acao,
                "perfil": m.perfil,
                "operador": m.operador,
                "timestamp": m.timestamp,
            }
            for m in movimentacoes
        ],
    }


async def consultar_rastreabilidade_unificada(
    termo: str,
    provider: SapCsvProvider,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    RF041 e RF042: Localiza um exame e retorna a Visão Unificada cruzando o histórico local
    com os dados clínicos do AGHU em tempo real a partir do escaneamento do QR Code de QUALQUER
    subproduto (exame, frasco, cassete, bloco, lâmina), código de bipagem de 10 dígitos,
    número de solicitação, prontuário, CPF ou CNS.
    """
    q = (termo or "").strip()
    if not q:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Informe ou bipe um código para rastrear.")

    sol_bip, _ = _interpretar_codigo_bipado(q)
    exame: Optional[ExameSAP] = None

    # 1. Busca direta no ExameSAP
    exame = (
        await db.execute(
            select(ExameSAP).where(
                or_(
                    ExameSAP.codigo_sap.ilike(q),
                    ExameSAP.qr_code.ilike(q),
                    ExameSAP.codigo_solicitacao == sol_bip,
                    ExameSAP.prontuario_paciente == q,
                    ExameSAP.cpf_paciente == q,
                    ExameSAP.cns_paciente == q,
                )
            )
        )
    ).scalars().first()

    # 2. Busca por QR Code de Frasco
    if not exame:
        frasco = (
            await db.execute(
                select(AmostraFrasco).where(
                    or_(AmostraFrasco.qr_code.ilike(q), AmostraFrasco.codigo_bipagem == q)
                )
            )
        ).scalars().first()
        if frasco:
            exame = (await db.execute(select(ExameSAP).where(ExameSAP.id == frasco.exame_id))).scalar_one_or_none()

    # 3. Busca por QR Code / Código de Cassete
    if not exame:
        cassete = (
            await db.execute(
                select(CasseteSAP).where(or_(CasseteSAP.qr_code.ilike(q), CasseteSAP.codigo_cassete.ilike(q)))
            )
        ).scalars().first()
        if cassete:
            exame = (await db.execute(select(ExameSAP).where(ExameSAP.id == cassete.exame_id))).scalar_one_or_none()

    # 4. Busca por QR Code / Código de Bloco
    if not exame:
        bloco = (
            await db.execute(
                select(BlocoSAP).where(or_(BlocoSAP.qr_code.ilike(q), BlocoSAP.codigo_bloco.ilike(q)))
            )
        ).scalars().first()
        if bloco:
            exame = (await db.execute(select(ExameSAP).where(ExameSAP.id == bloco.exame_id))).scalar_one_or_none()

    # 5. Busca por QR Code / Código de Lâmina
    if not exame:
        lamina = (
            await db.execute(
                select(LaminaSAP).where(or_(LaminaSAP.qr_code.ilike(q), LaminaSAP.codigo_lamina.ilike(q)))
            )
        ).scalars().first()
        if lamina:
            exame = (await db.execute(select(ExameSAP).where(ExameSAP.id == lamina.exame_id))).scalar_one_or_none()

    if exame:
        return await montar_visao_unificada_exame(exame, db)

    # 6. Se ainda não foi recebido no SAP local, busca na base do AGHU (CSV) para mostrar status do AGHU
    sol = await obter_solicitacao(sol_bip, provider, db)
    hoje = date.today()
    dt_sol = _parse_data_br_ou_iso(sol["data_solicitacao"]) or hoje
    return {
        "id": None,
        "codigo_sap": f"AGUARDANDO RECEPÇÃO (#{sol['codigo_solicitacao']})",
        "qr_code": f"SAP-QR-{sol['codigo_solicitacao']}",
        "codigo_solicitacao": sol["codigo_solicitacao"],
        "origem_peca": "HC",
        "nome_paciente": sol["nome_paciente"],
        "prontuario_paciente": sol["prontuario"],
        "data_nascimento": sol["data_nascimento"],
        "data_solicitacao": sol["data_solicitacao"],
        "origem": f"{sol['origem']} — {sol['unidade']}",
        "especialidade": sol["especialidade"],
        "informacoes_clinicas": sol["informacoes_clinica"],
        "tipo_exame": sol["tipo_exame"],
        "sigla_exame": sol["prefixo_sugerido"],
        "tipo_peca": sol["tipo_peca"],
        "urgente": sol["urgente_sugerido"],
        "suspeita_neoplasia": sol["suspeita_neoplasia_sugerida"],
        "requer_siscan": sol["requer_siscan"],
        "quantidade_amostras": sol["total_amostras"],
        "quantidade_cassetes": 0,
        "quantidade_blocos": 0,
        "quantidade_laminas": 0,
        "descricao_material": " | ".join(a["descricao_material"] for a in sol["amostras"]),
        "etapa_atual": "Aguardando Recebimento (AGHU)",
        "status_exame": "NAO_RECEBIDO",
        "concluido": False,
        "cancelado": False,
        "dias_decorridos": max(0, (hoje - dt_sol).days),
        "meta_dias_limite": META_DIAS_LIMITE,
        "lei_onco_limite": LEI_ONCO_LIMITE,
        "alerta_retencao_etapa": False,
        "status_pre_laudo": "Amostra ainda não recebida fisicamente na Triagem do SAP",
        "laudo_macroscopico_formal": "Aguardando entrada na Recepção/Triagem.",
        "laudo_final_aghu": ", ".join({a["status_item_exame"] for a in sol["amostras"]}),
        "arvore_subprodutos": [
            {
                "id": idx + 1,
                "numero_amostra": a["numero_amostra"],
                "codigo_bipagem": a["codigo_bipagem"],
                "qr_code": f"AGHU-{sol['codigo_solicitacao']}-{a['numero_amostra']}",
                "sigla_aghu": a["sigla_exame"],
                "descricao_material": a["descricao_material"],
                "status_frasco": f"Status AGHU: {a['status_item_exame']}",
                "identificado_macroscopia": False,
                "cassetes": [],
            }
            for idx, a in enumerate(sol["amostras"])
        ],
        "complementos": [],
        "rejeicoes_historico": sol["rejeicoes_historico"],
        "exames_relacionados": [],
        "historico": [
            {
                "etapa": "Solicitação AGHU",
                "perfil": sol["especialidade"] or "Médico Solicitante",
                "timestamp": sol["data_solicitacao"],
                "acao": f"Requisição #{sol['codigo_solicitacao']} aberta no AGHU ({sol['total_amostras']} amostra(s)).",
                "operador": "AGHU",
            }
        ],
    }


# =====================================================================
# 8. PAINEL SAP E BUSCA NO ACERVO CIENTÍFICO (RF004, RF044 a RF050)
# =====================================================================

def _agrupar_solicitacoes_csv(itens: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Agrupa as linhas do CSV do AGHU por codigo_solicitacao."""
    grupos: Dict[str, List[Dict[str, str]]] = {}
    for item in itens:
        grupos.setdefault(item["codigo_solicitacao"], []).append(item)
    return grupos


_cache_aghu_exames: Optional[List[Dict[str, Any]]] = None
_cache_aghu_data: Optional[date] = None


def _obter_exames_aghu_em_cache(itens_csv: List[Dict[str, str]], hoje: date) -> List[Dict[str, Any]]:
    """Mantém as 21.176 solicitações do CSV pré-processadas em memória para resposta instantânea (<50ms)."""
    global _cache_aghu_exames, _cache_aghu_data
    if _cache_aghu_exames is None or _cache_aghu_data != hoje:
        _cache_aghu_exames = [
            _montar_exame_aghu_nao_recebido(cod, grupo, hoje)
            for cod, grupo in _agrupar_solicitacoes_csv(itens_csv).items()
        ]
        _cache_aghu_data = hoje
    return _cache_aghu_exames


def _montar_exame_aghu_nao_recebido(codigo: str, itens: List[Dict[str, str]], hoje: date) -> Dict[str, Any]:
    """Formata uma solicitação do CSV do AGHU para exibição no Painel SAP e no Acervo."""
    primeiro = itens[0]
    prefixo, tipo, peca = _classificar_item(
        primeiro.get("sigla_exame", ""), primeiro.get("descricao_material", "")
    )
    codigos_status = {i.get("cod_status_item", "") for i in itens}
    cod_etapa = next((c for c in PRIORIDADE_ETAPA_AGHU if c in codigos_status), "PE")
    if codigos_status <= {"LI", "CA"} and "LI" in codigos_status:
        cod_etapa = "LI"

    data_sol = _parse_data_br_ou_iso(primeiro.get("data_solicitacao", ""))
    dias = (hoje - data_sol).days if data_sol else 0
    concluido = cod_etapa in ("LI", "CA")
    onco = _suspeita_neoplasia(itens)
    ano = data_sol.year if data_sol else hoje.year
    materiais = list(dict.fromkeys(i.get("descricao_material", "") for i in itens if i.get("descricao_material")))
    siglas = list(dict.fromkeys(i.get("sigla_exame", "") for i in itens))
    tem_congelacao = "CONGE" in siglas or prefixo == "CO"
    siscan = _requer_siscan(siglas, " ".join(materiais))

    return {
        "id": None,
        "recebido_no_sap": False,
        "codigo_sap": f"{prefixo} {codigo}/{str(ano)[-2:]}",
        "codigo_solicitacao": codigo,
        "origem_peca": "HC",
        "nome_paciente": primeiro.get("nome_paciente") or "Não informado",
        "prontuario_paciente": primeiro.get("prontuario") or "",
        "cpf_paciente": None,
        "cns_paciente": None,
        "tipo_exame": tipo,
        "sigla_exame": prefixo,
        "tipo_peca": peca,
        "siglas_aghu": siglas,
        "urgente": tem_congelacao,
        "suspeita_neoplasia": onco,
        "requer_siscan": siscan,
        "siscan_lancado": False,
        "quantidade_amostras": len(itens),
        "quantidade_cassetes": 0,
        "quantidade_blocos": 0,
        "quantidade_laminas": 0,
        "descricao_material": " | ".join(materiais) or "Não informado",
        "origem": " — ".join(filter(None, [primeiro.get("origem"), primeiro.get("unidade")])),
        "especialidade": primeiro.get("especialidade", ""),
        "data_solicitacao": primeiro.get("data_solicitacao", ""),
        "data_recebimento": None,
        "data_macroscopia": None,
        "data_liberacao": primeiro.get("data_solicitacao", "") if cod_etapa == "LI" else None,
        "diagnostico_associado": primeiro.get("informacoes_clinica", "")[:120] if cod_etapa == "LI" else None,
        "marcadores_ihq": "Painel IHQ (AGHU)" if "IMUHI" in siglas else None,
        "etapa_atual": ETAPAS_STATUS_AGHU.get(cod_etapa, cod_etapa),
        "status_pre_laudo": "Liberado no AGHU" if cod_etapa == "LI" else "Aguardando Recebimento Físico",
        "concluido": concluido,
        "cancelado": cod_etapa == "CA",
        "dias_decorridos": dias,
        "meta_dias_limite": META_DIAS_LIMITE,
        "lei_onco_limite": LEI_ONCO_LIMITE,
        "alerta_retencao_etapa": (not concluido) and (dias >= ALERTA_PREVENTIVO_DIAS),
        "ultimo_operador": "AGHU",
        "qr_code": f"SAP-QR-{codigo}",
        "laudo_macroscopico_formal": f"Material AGHU: {' | '.join(materiais) or 'Não informado'}",
        "laudo_final_aghu": ", ".join(sorted({i.get("status_item_exame", "") for i in itens})),
        "historico": [
            {
                "etapa": "Solicitação AGHU",
                "perfil": primeiro.get("especialidade") or "Solicitante",
                "timestamp": primeiro.get("data_solicitacao", ""),
                "acao": f"Solicitação {codigo} registrada no AGHU ({len(itens)} amostra(s)).",
                "operador": "AGHU",
            }
        ],
    }


async def listar_exames_painel(
    provider: SapCsvProvider,
    db: AsyncSession,
    limite: int = 100,
    offset: int = 0,
    busca: Optional[str] = None,
    etapa: Optional[str] = None,
    tipo_exame: Optional[str] = None,
    somente_ativos: bool = True,
) -> Dict[str, Any]:
    """
    Lista os exames unificando os registros já recebidos no banco local SQLite (com prioridade no topo)
    e as solicitações vindas do AGHU (CSV), destacando Congelação (CO) sempre no topo da fila (Reunião pág. 42).
    """
    itens_csv = await provider.listar_itens()
    hoje = date.today()

    exames_db = list((await db.execute(select(ExameSAP).order_by(ExameSAP.id.desc()))).scalars().all())
    solicitacoes_no_db = {e.codigo_solicitacao for e in exames_db}

    lista_db: List[Dict[str, Any]] = []
    for e in exames_db:
        visao = await montar_visao_unificada_exame(e, db)
        visao["recebido_no_sap"] = True
        lista_db.append(visao)

    todos_aghu = _obter_exames_aghu_em_cache(itens_csv, hoje)
    lista_aghu = [
        ex for ex in todos_aghu
        if ex["codigo_solicitacao"] not in solicitacoes_no_db
    ]

    todos = lista_db + lista_aghu
    ativos = [e for e in todos if not e["concluido"] and not e["cancelado"]]

    kpis = {
        "total_exames": len(todos),
        "recebidos_sap_local": len(lista_db),
        "em_andamento": len(ativos),
        "congelacoes_urgentes": sum(1 for e in ativos if e["sigla_exame"] == "CO" or e.get("urgente")),
        "alerta_meta_20_dias": sum(1 for e in ativos if e["dias_decorridos"] >= ALERTA_PREVENTIVO_DIAS),
        "monitorados_lei_60_dias": sum(1 for e in ativos if e["suspeita_neoplasia"]),
        "pendentes_siscan": sum(1 for e in todos if e.get("requer_siscan") and not e.get("siscan_lancado")),
        "concluidos": sum(1 for e in todos if e["concluido"] and not e["cancelado"]),
    }

    fila = ativos if somente_ativos else todos
    if etapa:
        fila = [e for e in fila if etapa.lower() in (e.get("etapa_atual") or "").lower()]
    if tipo_exame:
        fila = [e for e in fila if (e.get("sigla_exame") or "").upper() == tipo_exame.upper()]
    if busca:
        termo = _normalizar(busca.strip())
        fila = [
            e for e in fila
            if termo in _normalizar(
                f"{e['codigo_solicitacao']} {e['codigo_sap']} {e['nome_paciente']} "
                f"{e.get('prontuario_paciente', '')} {e.get('descricao_material', '')} "
                f"{e.get('ultimo_operador', '')}"
            )
        ]

    # Ordenação: 1º Recebidos no SAP local, 2º Congelação (CO) / Urgente no topo (Reunião pág. 42), 3º Oncológicos
    fila.sort(
        key=lambda e: (
            not e.get("recebido_no_sap", False),
            not (e.get("sigla_exame") == "CO" or e.get("urgente", False)),
            not e.get("suspeita_neoplasia", False),
            e.get("dias_decorridos", 0),
        )
    )

    return {
        "kpis": kpis,
        "exames": fila[offset: offset + limite],
        "total_filtrado": len(fila),
        "limite": limite,
        "offset": offset,
    }


async def pesquisar_acervo(
    provider: SapCsvProvider,
    db: AsyncSession,
    numero_solicitacao: Optional[str] = None,
    paciente: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    tipo_data: str = "recebimento",  # recebimento, macroscopia, liberacao, solicitacao
    tipo_peca: Optional[str] = None,
    sigla_exame: Optional[str] = None,
    diagnostico: Optional[str] = None,
    marcador_complemento: Optional[str] = None,
    limite: int = 100,
) -> Dict[str, Any]:
    """
    RF044 a RF050: Pesquisa avançada no acervo patológico para assistência e pesquisa científica.
    """
    res = await listar_exames_painel(provider, db, limite=25000, offset=0, somente_ativos=False)
    resultados = res["exames"]

    if numero_solicitacao:
        q_sol = _normalizar(numero_solicitacao.strip())
        resultados = [
            e for e in resultados
            if q_sol in _normalizar(f"{e['codigo_solicitacao']} {e['codigo_sap']}")
        ]

    if paciente:
        q_pac = _normalizar(paciente.strip())
        resultados = [
            e for e in resultados
            if q_pac in _normalizar(
                f"{e.get('nome_paciente', '')} {e.get('prontuario_paciente', '')} "
                f"{e.get('cpf_paciente', '')} {e.get('cns_paciente', '')}"
            )
        ]

    if tipo_peca:
        q_peca = _normalizar(tipo_peca.strip())
        resultados = [
            e for e in resultados
            if q_peca in _normalizar(f"{e.get('tipo_peca', '')} {e.get('descricao_material', '')}")
        ]

    if sigla_exame:
        resultados = [e for e in resultados if (e.get("sigla_exame") or "").upper() == sigla_exame.upper()]

    if diagnostico:
        q_diag = _normalizar(diagnostico.strip())
        resultados = [
            e for e in resultados
            if q_diag in _normalizar(
                f"{e.get('diagnostico_associado', '')} {e.get('laudo_previo_residente', '')} "
                f"{e.get('informacoes_clinicas', '')} {e.get('descricao_macroscopica', '')}"
            )
        ]

    if marcador_complemento:
        q_marc = _normalizar(marcador_complemento.strip())
        filtrados_marc = []
        for e in resultados:
            comp_str = " ".join(
                f"{c.get('tipo_pedido', '')} {c.get('marcadores', '')}" for c in (e.get("complementos") or [])
            )
            if (
                q_marc in _normalizar(comp_str)
                or q_marc in _normalizar(e.get("marcadores_ihq") or "")
                or (q_marc == "IHQ" and e.get("sigla_exame") == "IHQ")
            ):
                filtrados_marc.append(e)
        resultados = filtrados_marc

    dt_ini = _parse_data_br_ou_iso(data_inicio)
    dt_fim = _parse_data_br_ou_iso(data_fim)
    if dt_ini or dt_fim:
        campo_map = {
            "recebimento": "data_recebimento",
            "macroscopia": "data_macroscopia",
            "liberacao": "data_liberacao",
            "solicitacao": "data_solicitacao",
        }
        campo = campo_map.get(tipo_data, "data_solicitacao")
        filtrados_data = []
        for e in resultados:
            valor_dt = e.get(campo) or e.get("data_solicitacao")
            dt_item = _parse_data_br_ou_iso(valor_dt)
            if not dt_item:
                continue
            if dt_ini and dt_item < dt_ini:
                continue
            if dt_fim and dt_item > dt_fim:
                continue
            filtrados_data.append(e)
        resultados = filtrados_data

    return {
        "total_encontrado": len(resultados),
        "resultados": resultados[:limite],
    }


def exportar_acervo_csv(itens: List[Dict[str, Any]]) -> str:
    """RF050: Exporta os resultados da busca no acervo em formato CSV para pesquisa científica."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "codigo_sap",
        "codigo_solicitacao",
        "origem_peca",
        "nome_paciente",
        "prontuario",
        "tipo_exame",
        "tipo_peca",
        "descricao_material",
        "diagnostico_associado",
        "etapa_atual",
        "data_solicitacao",
        "data_recebimento",
        "data_macroscopia",
        "data_liberacao",
        "suspeita_neoplasia",
        "requer_siscan",
    ])
    for e in itens:
        writer.writerow([
            e.get("codigo_sap", ""),
            e.get("codigo_solicitacao", ""),
            e.get("origem_peca", "HC"),
            e.get("nome_paciente", ""),
            e.get("prontuario_paciente", ""),
            e.get("tipo_exame", ""),
            e.get("tipo_peca", ""),
            e.get("descricao_material", ""),
            e.get("diagnostico_associado") or "",
            e.get("etapa_atual", ""),
            e.get("data_solicitacao", ""),
            e.get("data_recebimento") or "",
            e.get("data_macroscopia") or "",
            e.get("data_liberacao") or "",
            "SIM" if e.get("suspeita_neoplasia") else "NAO",
            "SIM" if e.get("requer_siscan") else "NAO",
        ])
    return output.getvalue()
