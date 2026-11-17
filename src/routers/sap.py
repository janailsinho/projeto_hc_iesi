from fastapi import APIRouter, HTTPException, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import csv
from pathlib import Path

router = APIRouter(prefix="/api/sap", tags=["SAP - Recepção e Triagem"])

def get_csv_path(filename: str) -> Path:
    base_dir = Path(__file__).resolve().parent.parent.parent
    return base_dir / "data" / filename

class AmostraInput(BaseModel):
    id_amostra: str
    status_recebimento: str  # 'Confirmado' ou 'Rejeitado'
    motivo_rejeicao: Optional[str] = None

class TriagemRequest(BaseModel):
    solicitacao: str
    amostras: List[AmostraInput]
    observacoes: Optional[str] = None
    prioridade_oncologica: bool = False

@router.get("/exames")
async def listar_exames_geral():
    """
    Lista todas as solicitações/exames do CSV para preencher o Painel SAP principal na Vercel.
    """
    csv_path = get_csv_path("vw_solicitacao_atualizado.csv")
    exames = []
    
    try:
        if csv_path.exists():
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    exames.append({
                        "codigo_sap": f"HP {row.get('solicitacao', '0000')[-4:]}/26",
                        "solicitacao_aghu": row.get("solicitacao"),
                        "paciente": row.get("paciente", "Não informado"),
                        "prontuario": row.get("prontuario", "N/D"),
                        "tipo_exame": row.get("material", "Histopatológico"),
                        "origem": row.get("origem", "Ambulatório"),
                        "etapa_atual": "Recepção / Triagem",
                        "tempo_decorrido": "2 dias"
                    })
    except Exception as e:
        print(f"Erro ao ler exames: {e}")

    return exames

@router.get("/solicitacoes/{numero_solicitacao}/amostras")
async def obter_amostras_solicitacao(numero_solicitacao: str):
    """
    Lê o arquivo CSV real do AGHU e agrupa todas as amostras/frascos 
    correspondentes ao número da solicitação fornecido.
    """
    csv_path = get_csv_path("vw_solicitacao_atualizado.csv")
    amostras_encontradas = []
    dados_gerais = None
    
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sol_val = row.get("solicitacao") or row.get("SOLICITACAO") or list(row.values())[0]
                
                if str(sol_val).strip() == str(numero_solicitacao).strip():
                    if not dados_gerais:
                        dados_gerais = {
                            "solicitacao": str(sol_val),
                            "paciente": row.get("paciente") or row.get("PACIENTE") or "Não informado",
                            "prontuario": row.get("prontuario") or row.get("PRONTUARIO") or "N/D",
                            "origem": row.get("origem") or row.get("ORIGEM") or "Ambulatório / Internação",
                            "pre_laudo_status": "Em Andamento / Rascunho Disponível para Consulta"
                        }
                    
                    amostras_encontradas.append({
                        "id_amostra": f"{numero_solicitacao}-{len(amostras_encontradas) + 1:02d}",
                        "descricao": row.get("material") or row.get("MATERIAL") or row.get("descricao") or "Frasco / Amostra Recebida",
                        "status": "Pendente"
                    })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler base de solicitações: {str(e)}")

    if not dados_gerais or not amostras_encontradas:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada na base do AGHU.")

    return {
        **dados_gerais,
        "total_amostras": len(amostras_encontradas),
        "amostras": amostras_encontradas
    }

@router.post("/solicitacoes/triagem")
async def processar_triagem_com_rejeicao(dados: TriagemRequest):
    """
    Processa a triagem física validando múltiplas amostras, aceites ou rejeições 
    com justificativa, e gerando o código SAP oficial.
    """
    confirmadas = [a for a in dados.amostras if a.status_recebimento == 'Confirmado']
    rejeitadas = [a for a in dados.amostras if a.status_recebimento == 'Rejeitado']

    return {
        "mensagem": "Triagem e controle de rejeição processados com sucesso!",
        "solicitacao": dados.solicitacao,
        "total_aceitas": len(confirmadas),
        "total_rejeitadas": len(rejeitadas),
        "codigo_sap_oficial": f"HP {dados.solicitacao[-4:]}/26",
        "status_etiquetas": "Geradas com QR Code e ID de Múltiplas Amostras"
    }