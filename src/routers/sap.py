from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/sap", tags=["SAP"])

@router.get("/exames", response_model=Dict[str, Any])
async def listar_exames_sap():
    """Retorna os KPIs e a lista de exames/filas para o painel do SAP."""
    return {
        "kpis": {
            "total_exames": 2,
            "em_andamento": 2,
            "alerta_meta_20_dias": 1,
            "monitorados_lei_60_dias": 1,
            "concluidos": 0
        },
        "exames": [
            {
                "codigo_anual": "SAP-2026-001",
                "requisicao_aghu_id": "AGHU-98341",
                "nome_paciente": "Maria da Silva",
                "prontuario_paciente": "123456",
                "tipo_exame": "Biópsia de Mama",
                "suspeita_neoplasia": True,
                "origem": "Cirurgia Geral",
                "etapa_atual": "Recepção / Triagem",
                "meta_20_dias_restantes": 17,
                "lei_60_dias_restantes": 45,
                "qr_code": "QR98341-MACRO",
                "laudo_macroscopico_formal": "Fragmento irregular de coloração pardacenta...",
                "laudo_final_aghu": "Aguardando liberação definitiva.",
                "historico": [
                    {
                        "etapa": "Recepção / Triagem",
                        "perfil": "Recepção SAP",
                        "timestamp": "05/11/2026 10:30",
                        "acao": "Amostra cadastrada e etiquetada com QR Code.",
                        "operador": "Atendente SAP"
                    }
                ]
            },
            {
                "codigo_anual": "SAP-2026-002",
                "requisicao_aghu_id": "AGHU-98342",
                "nome_paciente": "José Santos",
                "prontuario_paciente": "654321",
                "tipo_exame": "Pele / Melanoma",
                "suspeita_neoplasia": True,
                "origem": "Dermatologia",
                "etapa_atual": "Processamento Técnico",
                "meta_20_dias_restantes": 8,
                "lei_60_dias_restantes": 30,
                "qr_code": "QR98342-HISTO",
                "laudo_macroscopico_formal": "Retalho cutâneo elíptico medindo 1,5 x 0,8 cm...",
                "laudo_final_aghu": "Em processamento técnico nas bancadas.",
                "historico": [
                    {
                        "etapa": "Recepção / Triagem",
                        "perfil": "Recepção SAP",
                        "timestamp": "05/11/2026 09:10",
                        "acao": "Amostra recebida e conferida com requisição AGHU.",
                        "operador": "Atendente SAP"
                    },
                    {
                        "etapa": "Processamento Técnico",
                        "perfil": "Técnico de Laboratório",
                        "timestamp": "05/11/2026 11:15",
                        "acao": "Inclusão em parafina e microtomia realizadas.",
                        "operador": "Técnico Lab"
                    }
                ]
            }
        ]
    }