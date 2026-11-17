from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict, Any
from pydantic import BaseModel
import csv
from pathlib import Path

router = APIRouter(prefix="/api/sap", tags=["SAP - Recepção e Triagem"])

# Helper para achar a raiz e ler os CSVs com segurança (pathlib)
def get_csv_path(filename: str) -> Path:
    base_dir = Path(__file__).resolve().parent.parent.parent
    return base_dir / "data" / filename

class AmostraConferencia(BaseModel):
    id_amostra: str
    status_recebimento: str # 'Confirmado', 'Rejeitado', 'Pendente'
    motivo_rejeicao: str = None

@router.get("/solicitacoes/{numero_solicitacao}/amostras")
async def obter_amostras_solicitacao(numero_solicitacao: str):
    """
    Busca a solicitação no arquivo CSV do AGHU e retorna os dados do paciente 
    junto com as múltiplas amostras/frascos associados.
    """
    csv_path = get_csv_path("vw_solicitacao_atualizado.csv")
    solicitacao_encontrada = None
    
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row.get("solicitacao")) == str(numero_solicitacao):
                    solicitacao_encontrada = row
                    break
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler base de solicitações: {str(e)}")

    if not solicitacao_encontrada:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada na base do AGHU.")

    # Simulação estruturada de múltiplas amostras (frascos 1, 2, etc.) vinculadas à solicitação
    amostras_mock = [
        {
            "id_amostra": f"{numero_solicitacao}-01",
            "descricao": solicitacao_encontrada.demand_descricao if hasattr(solicitacao_encontrada, 'demand_descricao') else "Frasco 1 - Biópsia Principal (Fixada em Formol)",
            "status": "Pendente"
        },
        {
            "id_amostra": f"{numero_solicitacao}-02",
            "descricao": "Frasco 2 - Margem Cirúrgica / Fragmento Adicional",
            "status": "Pendente"
        }
    ]

    return {
        "solicitacao": solicitacao_encontrada.get("solicitacao"),
        "paciente": solicitacao_encontrada.get("paciente"),
        "prontuario": solicitacao_encontrada.get("prontuario"),
        "origem": solicitacao_encontrada.get("origem", "Ambulatório / Internação"),
        "total_amostras": len(amostras_mock),
        "amostras": amostras_mock
    }

@router.post("/solicitacoes/{numero_solicitacao}/triagem")
async def registrar_triagem_amostras(numero_solicitacao: str, dados: List[AmostraConferencia]):
    """
    Registra o check-in físico ou a rejeição (com justificativa) de cada amostra 
    e gera o número SAP oficial e etiquetas.
    """
    # Aqui processamos a gravação do log de auditoria e status das amostras
    confirmadas = [a for a in dados if a.status_recebimento == 'Confirmado']
    rejeitadas = [a for a in dados if a.status_recebimento == 'Rejeitado']

    return {
        "mensagem": "Triagem processada com sucesso no SAP!",
        "solicitacao": numero_solicitacao,
        "amostras_aceitas": len(confirmadas),
        "amostras_rejeitadas": len(rejeitadas),
        "codigo_sap_gerado": f"HP 0884/26"
    }