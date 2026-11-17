"""
Provider CSV do Serviço de Anatomia Patológica (SAP)
=====================================================
Lê a exportação da view de solicitações do AGHU (`data/vw_solicitacao_atualizado.csv`)
usando o NOME das colunas (csv.DictReader), evitando erros de mapeamento por índice.
O conteúdo é mantido em cache e recarregado automaticamente quando o arquivo muda.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

COLUNAS_OBRIGATORIAS = {
    "codigo_solicitacao",
    "numero_amostra",
    "cod_status_item",
    "status_item_exame",
    "data_solicitacao",
    "nome_paciente",
    "prontuario",
    "origem",
    "sigla_exame",
    "nome_exame",
    "descricao_material",
}


class SapCsvProvider:
    """Fornece as linhas (amostras/itens de exame) da view de solicitações do AGHU."""

    def __init__(self, csv_path: Optional[str] = None) -> None:
        """
        Inicializa o provider.

        Args:
            csv_path: Caminho do CSV. Se omitido, usa `data/vw_solicitacao_atualizado.csv`.
        """
        if csv_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            self.csv_path = base_dir / "data" / "vw_solicitacao_atualizado.csv"
        else:
            self.csv_path = Path(csv_path)
        self._cache: List[Dict[str, str]] = []
        self._cache_mtime: Optional[float] = None

    def _carregar(self) -> List[Dict[str, str]]:
        """Lê o CSV do disco, valida o cabeçalho e normaliza os valores (strip)."""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Arquivo CSV do SAP não encontrado: {self.csv_path}")

        # utf-8-sig remove um eventual BOM gerado por exportações do Excel/AGHU
        with open(self.csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            cabecalho = {c.strip() for c in (reader.fieldnames or [])}
            faltando = COLUNAS_OBRIGATORIAS - cabecalho
            if faltando:
                raise ValueError(f"CSV do SAP sem as colunas obrigatórias: {sorted(faltando)}")

            linhas: List[Dict[str, str]] = []
            for row in reader:
                item = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
                if item.get("codigo_solicitacao"):
                    linhas.append(item)
            return linhas

    async def listar_itens(self) -> List[Dict[str, str]]:
        """
        Retorna todas as linhas do CSV (uma por amostra/item de exame).

        Returns:
            Lista de dicionários indexados pelo nome da coluna.
        """
        mtime = self.csv_path.stat().st_mtime if self.csv_path.exists() else None
        if self._cache_mtime is None or mtime != self._cache_mtime:
            self._cache = self._carregar()
            self._cache_mtime = mtime
        return self._cache


sap_csv_provider = SapCsvProvider()
