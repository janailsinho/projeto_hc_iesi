import csv
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/api/sap", tags=["SAP"])

# Caminhos possíveis para localizar o CSV automaticamente
CSV_PATHS = [
    "data/vw_solicitacao_atualizado.csv",
    "vw_solicitacao_atualizado.csv",
    os.path.expanduser("~/Downloads/vw_solicitacao_atualizado.csv"),
]

def obter_caminho_csv() -> Optional[str]:
    for path in CSV_PATHS:
        if os.path.exists(path):
            return path
    return None

def mapear_prefixo_sap(sigla_exame: str, codigo_lab: str) -> str:
    """Converte a sigla/código do exame AGHU para o prefixo real usado pelo SAP (HP, IHQ, CO, CG, CCV)."""
    sigla = (sigla_exame or "").strip().upper()
    if sigla == "IMUHI" or str(codigo_lab) == "209":
        return "IHQ"
    if sigla == "CONGE" or str(codigo_lab) == "205":
        return "CO"
    if sigla == "CCVM" or str(codigo_lab) == "139":
        return "CCV"
    if sigla in ("CITOP", "CITO", "CPMAM") or str(codigo_lab) == "203":
        return "CG"
    return "HP"

def calcular_dias_corridos(data_str: str) -> int:
    """Calcula a contagem progressiva (para mais) de dias desde a solicitação/entrada."""
    try:
        dt = datetime.strptime(data_str.strip(), "%d/%m/%Y")
        hoje = datetime.now()
        dias = (hoje - dt).days
        return max(1, dias)
    except Exception:
        return 1

# Contadores sequenciais internos por tipo de exame (ano 26)
CONTADORES_SAP = {
    "HP": 886,
    "IHQ": 103,
    "CO": 15,
    "CG": 215,
    "CCV": 340,
}

# Fila inicial no Painel SAP com dados reais do CSV
EXAMES_FILA: List[Dict[str, Any]] = [
    {
        "codigo_sap": "HP 0884/26",
        "codigo_solicitacao": "1479377",
        "nome_paciente": "RAQUEL PEREIRA DOS SANTOS BARBOSA",
        "prontuario_paciente": "22389381",
        "data_nascimento": "05/04/1961",
        "sigla_exame": "APECR",
        "tipo_exame": "ANATOMOPATOLÓGICO - PEÇA CIRÚRGICA",
        "descricao_material": "PRODUTO DE RETOSSIGMOIDECTOMIA + AMPLIAÇÃO DE MARGEM PROXIMAL",
        "quantidade_amostras": 2,
        "suspeita_neoplasia": True,
        "origem": "Internação - 8º SUL (CIRURGIA GERAL)",
        "etapa_atual": "Recepção / Triagem",
        "dias_decorridos": 3,
        "meta_dias_limite": 20,
        "lei_onco_limite": 60,
        "qr_code": "QR-HP0884-26-SOL1479377",
        "laudo_macroscopico_formal": "Aguardando clivagem na bancada de Macroscopia.",
        "laudo_final_aghu": "Em processamento inicial.",
        "historico": [
            {
                "etapa": "Recepção / Triagem",
                "perfil": "Recepção SAP",
                "timestamp": "16/09/2026 10:30",
                "acao": "Solicitação 1479377 validada via AGHU/CSV (2 amostras conferidas) e etiquetada com código HP 0884/26.",
                "operador": "recepcao.sap"
            }
        ]
    },
    {
        "codigo_sap": "IHQ 0102/26",
        "codigo_solicitacao": "1479367",
        "nome_paciente": "MARIA CONCEIÇÃO DOS SANTOS",
        "prontuario_paciente": "21960174",
        "data_nascimento": "13/08/1954",
        "sigla_exame": "IMUHI",
        "tipo_exame": "IMUNO-HISTOQUÍMICA",
        "descricao_material": "LESÃO EM CABEÇA DE PÂNCREAS (Ref. HP 0885/25)",
        "quantidade_amostras": 2,
        "suspeita_neoplasia": True,
        "origem": "Ambulatório - ONCOLOGIA CLÍNICA",
        "etapa_atual": "Processamento Técnico",
        "dias_decorridos": 18,
        "meta_dias_limite": 20,
        "lei_onco_limite": 60,
        "qr_code": "QR-IHQ0102-26-SOL1479367",
        "laudo_macroscopico_formal": "Revisão de lâmina e bloco de lesão de cabeça de pâncreas.",
        "laudo_final_aghu": "Em processamento técnico de Imuno-histoquímica.",
        "historico": [
            {
                "etapa": "Recepção / Triagem",
                "perfil": "Recepção SAP",
                "timestamp": "01/09/2026 09:10",
                "acao": "Solicitação 1479367 recebida e conferida com 2 amostras.",
                "operador": "recepcao.sap"
            },
            {
                "etapa": "Processamento Técnico",
                "perfil": "Técnico de Laboratório",
                "timestamp": "05/09/2026 11:15",
                "acao": "Preparo de lâminas para painel de Imuno-histoquímica.",
                "operador": "tecnico.lab"
            }
        ]
    }
]


class RecebimentoAmostraInput(BaseModel):
    codigo_solicitacao: str
    amostras_conferidas: List[int]
    estagio_entrada: str
    suspeita_neoplasia: bool
    observacao_recepcao: Optional[str] = ""
    perfil_usuario: str
    operador: str


@router.get("/exames", response_model=Dict[str, Any])
async def listar_exames_sap():
    """Retorna os KPIs e a fila de exames com contagem progressiva de dias."""
    total = len(EXAMES_FILA)
    concluidos = sum(1 for e in EXAMES_FILA if "Concluído" in e["etapa_atual"] or "Arquivado" in e["etapa_atual"])
    em_andamento = total - concluidos
    alerta_20d = sum(1 for e in EXAMES_FILA if e["dias_decorridos"] >= 15 and e["etapa_atual"] != "Concluído / Arquivado")
    onco_60d = sum(1 for e in EXAMES_FILA if e["suspeita_neoplasia"])

    return {
        "kpis": {
            "total_exames": total,
            "em_andamento": em_andamento,
            "alerta_meta_20_dias": alerta_20d,
            "monitorados_lei_60_dias": onco_60d,
            "concluidos": concluidos
        },
        "exames": EXAMES_FILA
    }


@router.get("/solicitacao/{codigo_solicitacao}", response_model=Dict[str, Any])
async def buscar_solicitacao_csv(codigo_solicitacao: str):
    """Busca os dados da solicitação e suas amostras diretamente no CSV do AGHU."""
    csv_path = obter_caminho_csv()
    if not csv_path:
        raise HTTPException(
            status_code=404,
            detail="Arquivo vw_solicitacao_atualizado.csv não encontrado na pasta data/."
        )

    codigo_busca = codigo_solicitacao.strip()
    amostras_encontradas = []
    dados_gerais = None

    with open(csv_path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("codigo_solicitacao", "")).strip() == codigo_busca:
                if not dados_gerais:
                    prefixo = mapear_prefixo_sap(row.get("sigla_exame", ""), row.get("codigo_lab", ""))
                    info_clinica = (row.get("informacoes_clinica") or "").strip()
                    onco_auto = any(
                        termo in info_clinica.lower() or termo in (row.get("unidade") or "").lower()
                        for termo in ["tumor", "neoplasia", "onco", "carcinoma", "melanoma", "malign", "lesão"]
                    )
                    # Pega o nome completo exatamente como vem no CSV do AGHU
                    nome_completo = (row.get("nome_paciente") or "").strip()
                    
                    dados_gerais = {
                        "codigo_solicitacao": codigo_busca,
                        "data_solicitacao": row.get("data_solicitacao", ""),
                        "nome_paciente": nome_completo,
                        "data_nascimento": row.get("data_nascimento", ""),
                        "prontuario": str(row.get("prontuario", "")).replace(".0", ""),
                        "especialidade": row.get("especialidade", ""),
                        "convenio": row.get("convenio", ""),
                        "origem": row.get("origem", ""),
                        "unidade": row.get("unidade", ""),
                        "informacoes_clinica": info_clinica,
                        "prefixo_sugerido": prefixo,
                        "suspeita_neoplasia_sugerida": onco_auto
                    }
                amostras_encontradas.append({
                    "numero_amostra": int(row.get("numero_amostra", 1)),
                    "cod_status_item": row.get("cod_status_item", ""),
                    "status_item_exame": row.get("status_item_exame", ""),
                    "codigo_lab": row.get("codigo_lab", ""),
                    "sigla_exame": row.get("sigla_exame", ""),
                    "nome_exame": row.get("nome_exame", ""),
                    "descricao_material": row.get("descricao_material", "")
                })

    if not dados_gerais:
        raise HTTPException(
            status_code=404,
            detail=f"Solicitação AGHU nº {codigo_busca} não encontrada na base CSV."
        )

    amostras_encontradas.sort(key=lambda x: x["numero_amostra"])
    dados_gerais["total_amostras"] = len(amostras_encontradas)
    dados_gerais["amostras"] = amostras_encontradas
    dados_gerais["ja_recebida"] = any(e["codigo_solicitacao"] == codigo_busca for e in EXAMES_FILA)
    return dados_gerais


@router.post("/receber", response_model=Dict[str, Any])
async def receber_amostra_sap(payload: RecebimentoAmostraInput):
    """Valida o perfil de acesso, confere todas as amostras da solicitação e gera o código oficial do SAP."""
    if payload.perfil_usuario not in ("Recepção SAP", "Chefia SAP / Admin"):
        raise HTTPException(
            status_code=403,
            detail=f"Acesso Negado: O perfil '{payload.perfil_usuario}' não possui permissão para receber amostras na triagem."
        )

    dados_sol = await buscar_solicitacao_csv(payload.codigo_solicitacao)
    if dados_sol["ja_recebida"]:
        raise HTTPException(
            status_code=400,
            detail=f"A solicitação {payload.codigo_solicitacao} já foi recebida anteriormente no SISPATO."
        )

    total_esperado = dados_sol["total_amostras"]
    if len(payload.amostras_conferidas) < total_esperado:
        raise HTTPException(
            status_code=400,
            detail=f"Validação incompleta: foram conferidas {len(payload.amostras_conferidas)} de {total_esperado} amostras físicas."
        )

    prefixo = dados_sol["prefixo_sugerido"]
    CONTADORES_SAP[prefixo] = CONTADORES_SAP.get(prefixo, 100) + 1
    novo_codigo_sap = f"{prefixo} {CONTADORES_SAP[prefixo]:04d}/26"

    primeira_amostra = dados_sol["amostras"][0]
    materiais_concat = " + ".join(a["descricao_material"] for a in dados_sol["amostras"])
    agora_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    novo_exame = {
        "codigo_sap": novo_codigo_sap,
        "codigo_solicitacao": payload.codigo_solicitacao,
        "nome_paciente": dados_sol["nome_paciente"],
        "prontuario_paciente": dados_sol["prontuario"],
        "data_nascimento": dados_sol["data_nascimento"],
        "sigla_exame": primeira_amostra["sigla_exame"],
        "tipo_exame": primeira_amostra["nome_exame"],
        "descricao_material": materiais_concat,
        "quantidade_amostras": total_esperado,
        "suspeita_neoplasia": payload.suspeita_neoplasia,
        "origem": f"{dados_sol['origem']} — {dados_sol['unidade']} ({dados_sol['especialidade']})",
        "etapa_atual": "Recepção / Triagem",
        "dias_decorridos": 1,
        "meta_dias_limite": 20,
        "lei_onco_limite": 60,
        "qr_code": f"QR-{novo_codigo_sap.replace(' ', '').replace('/', '-')}-SOL{payload.codigo_solicitacao}",
        "laudo_macroscopico_formal": "Aguardando clivagem na Macroscopia.",
        "laudo_final_aghu": "Recebido no SAP — Em processamento.",
        "historico": [
            {
                "etapa": "Recepção / Triagem",
                "perfil": payload.perfil_usuario,
                "timestamp": agora_str,
                "acao": (
                    f"Recebimento validado no SISPATO: {total_esperado} amostra(s) física(s) conferida(s) "
                    f"[{payload.estagio_entrada}]. Gerado protocolo {novo_codigo_sap}. "
                    f"{('Obs: ' + payload.observacao_recepcao) if payload.observacao_recepcao else ''}"
                ).strip(),
                "operador": payload.operador
            }
        ]
    }

    EXAMES_FILA.insert(0, novo_exame)
    return {
        "mensagem": f"Solicitação {payload.codigo_solicitacao} recebida com sucesso sob o código {novo_codigo_sap}!",
        "exame": novo_exame
    }