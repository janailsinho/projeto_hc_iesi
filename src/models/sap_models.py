"""
Modelos SQLAlchemy do Sistema de Gestão Digital da Anatomia Patológica (SISPATO / SAP)
======================================================================================
Cobre os requisitos RF001 a RF055 e RNF001 a RNF017:
- PacienteSUS (RF005, RF006): Pacientes externos oriundos do SUS/Prefeituras.
- ExameSAP (RF007-RF012, RF038, RF040-RF043): Exame anatomopatológico (HP, CO, IHQ, CG, CCV).
- AmostraFrasco (RF008-RF013): Frascos/amostras vinculados ao exame, com descrição individual.
- RejeicaoSAP (Transcrição HC): Registro de não conformidades e devoluções na recepção/bancada.
- CasseteSAP (RF014-RF018): Cassetes gerados na Macroscopia (1:N com Frasco).
- BlocoSAP (RF021-RF022, RF029, RF031): Blocos de parafina gerados na Inclusão (1:N com Cassete).
- LaminaSAP (RF023-RF028, RF030, RF033, RF039): Lâminas geradas no Corte/Coloração (1:N com Bloco).
- ComplementoSAP (RF032, RF036-RF037): Pedidos de IHQ, novos cortes ou colorações especiais.
- MovimentacaoSAP (RF040-RF042, RNF010): Trilha imutável de transição de etapas.
- ImpressoraEstacaoSAP (RF054-RF055): Configuração de impressoras Zebra/Argox por estação.
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from ..resources.database import Base


def _agora() -> datetime:
    """Retorna o timestamp UTC atual."""
    return datetime.now(timezone.utc)


class PacienteSUS(Base):
    """Cadastro local de pacientes externos do SUS (RF005, RF006)."""
    __tablename__ = "sap_pacientes_sus"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String, nullable=False, index=True)
    cpf = Column(String, nullable=True, unique=True, index=True)
    cns = Column(String, nullable=True, unique=True, index=True)
    data_nascimento = Column(String, nullable=False)
    sexo = Column(String, nullable=True, default="N/I")
    telefone = Column(String, nullable=True)
    municipio_origem = Column(String, nullable=True)
    unidade_solicitante = Column(String, nullable=True)
    created_at = Column(DateTime, default=_agora, nullable=False)


class ExameSAP(Base):
    """Exame anatomopatológico recebido no SAP (RF007 a RF039)."""
    __tablename__ = "sap_exames"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo_sap = Column(String, unique=True, nullable=False, index=True)  # Ex: HP-2026-001
    qr_code = Column(String, unique=True, nullable=False, index=True)     # Ex: SAP-QR-HP-2026-001
    codigo_solicitacao = Column(String, nullable=False, index=True)       # Nº AGHU ou protocolo SUS
    origem_peca = Column(String, nullable=False, default="HC")            # 'HC' ou 'SUS'
    nome_paciente = Column(String, nullable=False, index=True)
    prontuario_paciente = Column(String, nullable=True, index=True)
    cpf_paciente = Column(String, nullable=True, index=True)
    cns_paciente = Column(String, nullable=True, index=True)
    data_nascimento = Column(String, nullable=True)
    sexo_paciente = Column(String, nullable=True)
    data_solicitacao = Column(String, nullable=True)
    origem_unidade = Column(String, nullable=True)
    especialidade = Column(String, nullable=True)
    informacoes_clinicas = Column(Text, nullable=True)

    sigla_exame = Column(String, nullable=False, index=True)  # HP, CO, IHQ, CG, CCV
    tipo_exame = Column(String, nullable=False)
    tipo_peca = Column(String, nullable=True, index=True)     # Mama, Colo Uterino, Próstata, Geral
    urgente = Column(Boolean, default=False, nullable=False)
    motivo_urgencia = Column(String, nullable=True)
    suspeita_neoplasia = Column(Boolean, default=False, nullable=False)
    requer_siscan = Column(Boolean, default=False, nullable=False)
    siscan_lancado = Column(Boolean, default=False, nullable=False)

    estagio_entrada = Column(String, nullable=True)
    observacao_recepcao = Column(Text, nullable=True)
    etapa_atual = Column(String, nullable=False, default="Recepção / Triagem", index=True)
    status_exame = Column(String, nullable=False, default="ATIVO")  # ATIVO, CONCLUIDO, CANCELADO
    motivo_cancelamento = Column(Text, nullable=True)

    # Vínculo entre exames (ex: CO -> HP ou HP -> IHQ)
    exame_origem_codigo = Column(String, nullable=True, index=True)

    # Macroscopia (RF014)
    descricao_macroscopica = Column(Text, nullable=True)
    data_macroscopia = Column(String, nullable=True)
    responsavel_macroscopia = Column(String, nullable=True)

    # Microscopia / Laudo Prévio / Revisão (RF034, RF035, RF038)
    laudo_previo_residente = Column(Text, nullable=True)
    diagnostico_associado = Column(String, nullable=True, index=True)
    residente_responsavel = Column(String, nullable=True)
    data_laudo_previo = Column(String, nullable=True)
    status_revisao_patologista = Column(String, nullable=True)  # PENDENTE, APROVADO, REPROVADO, INACABADO
    observacao_revisao = Column(Text, nullable=True)
    patologista_revisor = Column(String, nullable=True)
    data_liberacao = Column(String, nullable=True)
    laminas_arquivadas = Column(Boolean, default=False, nullable=False)
    local_arquivo_laminas = Column(String, nullable=True)

    responsavel_recepcao = Column(String, nullable=False)
    data_recebimento = Column(String, nullable=False)
    created_at = Column(DateTime, default=_agora, nullable=False)
    updated_at = Column(DateTime, default=_agora, onupdate=_agora, nullable=False)


class AmostraFrasco(Base):
    """Frasco/amostra física vinculada a um ExameSAP (RF008-RF013)."""
    __tablename__ = "sap_amostras_frascos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exame_id = Column(Integer, ForeignKey("sap_exames.id"), nullable=False, index=True)
    codigo_solicitacao = Column(String, nullable=False, index=True)
    numero_amostra = Column(String, nullable=False)
    codigo_bipagem = Column(String, nullable=False, index=True)  # 7 dígitos sol + 3 dígitos amostra
    qr_code = Column(String, unique=True, nullable=False, index=True)
    sigla_aghu = Column(String, nullable=True)
    nome_exame_aghu = Column(String, nullable=True)
    descricao_material = Column(String, nullable=False)
    status_frasco = Column(String, nullable=False, default="Na Recepção")
    identificado_macroscopia = Column(Boolean, default=False, nullable=False)
    responsavel_atual = Column(String, nullable=True)
    created_at = Column(DateTime, default=_agora, nullable=False)


class RejeicaoSAP(Base):
    """Registro de rejeição / não conformidade de amostras (preserva histórico para SLA)."""
    __tablename__ = "sap_rejeicoes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    codigo_solicitacao = Column(String, nullable=False, index=True)
    numero_amostra = Column(String, nullable=True)
    nome_paciente = Column(String, nullable=True)
    prontuario = Column(String, nullable=True)
    origem_unidade = Column(String, nullable=True)
    tipo_inconformidade = Column(String, nullable=False)  # Solicitação ou Frasco
    motivo_padrao = Column(String, nullable=False)
    detalhe_outros = Column(Text, nullable=True)
    setor_devolucao = Column(String, nullable=True)
    responsavel = Column(String, nullable=False)
    data_rejeicao = Column(String, nullable=False)
    superada = Column(Boolean, default=False, nullable=False)
    data_superacao = Column(String, nullable=True)
    created_at = Column(DateTime, default=_agora, nullable=False)


class CasseteSAP(Base):
    """Cassete gerado na Macroscopia vinculado hierarquicamente ao Frasco (RF015-RF020)."""
    __tablename__ = "sap_cassetes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exame_id = Column(Integer, ForeignKey("sap_exames.id"), nullable=False, index=True)
    frasco_id = Column(Integer, ForeignKey("sap_amostras_frascos.id"), nullable=False, index=True)
    codigo_cassete = Column(String, unique=True, nullable=False, index=True)  # Ex: HP-2026-001-F1-A
    qr_code = Column(String, unique=True, nullable=False, index=True)
    sigla_cassete = Column(String, nullable=False)  # A, B, C...
    descricao_fragmentos = Column(String, nullable=True)
    identidade_confirmada_macro = Column(Boolean, default=False, nullable=False)
    enviado_processamento = Column(Boolean, default=False, nullable=False)
    identificado_processamento = Column(Boolean, default=False, nullable=False)
    processamento_iniciado = Column(Boolean, default=False, nullable=False)
    data_inicio_processamento = Column(String, nullable=True)
    tecnico_processamento = Column(String, nullable=True)
    status_cassete = Column(String, nullable=False, default="Gerado na Macroscopia")
    responsavel_criacao = Column(String, nullable=False)
    created_at = Column(DateTime, default=_agora, nullable=False)


class BlocoSAP(Base):
    """Bloco de parafina vinculado hierarquicamente ao Cassete (RF021-RF022, RF029, RF031)."""
    __tablename__ = "sap_blocos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exame_id = Column(Integer, ForeignKey("sap_exames.id"), nullable=False, index=True)
    cassete_id = Column(Integer, ForeignKey("sap_cassetes.id"), nullable=False, index=True)
    codigo_bloco = Column(String, unique=True, nullable=False, index=True)  # Ex: HP-2026-001-F1-A-B1
    qr_code = Column(String, unique=True, nullable=False, index=True)
    realizou_corte = Column(Boolean, default=False, nullable=False)
    data_corte = Column(String, nullable=True)
    responsavel_corte = Column(String, nullable=True)
    identidade_confirmada_arquivo = Column(Boolean, default=False, nullable=False)
    arquivado = Column(Boolean, default=False, nullable=False)
    local_arquivo = Column(String, nullable=True)
    data_arquivamento = Column(String, nullable=True)
    responsavel_inclusao = Column(String, nullable=False)
    data_inclusao = Column(String, nullable=False)
    created_at = Column(DateTime, default=_agora, nullable=False)


class LaminaSAP(Base):
    """Lâmina vinculada hierarquicamente ao Bloco de Parafina (RF024-RF028, RF030, RF033, RF039)."""
    __tablename__ = "sap_laminas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exame_id = Column(Integer, ForeignKey("sap_exames.id"), nullable=False, index=True)
    bloco_id = Column(Integer, ForeignKey("sap_blocos.id"), nullable=False, index=True)
    codigo_lamina = Column(String, unique=True, nullable=False, index=True)  # Ex: HP-2026-001-F1-A-B1-L1
    qr_code = Column(String, unique=True, nullable=False, index=True)
    tipo_coloracao = Column(String, nullable=False, default="H&E (Hematoxilina-Eosina)")
    marcador_ihq = Column(String, nullable=True, index=True)
    coloracao_montagem_ok = Column(Boolean, default=False, nullable=False)
    data_coloracao = Column(String, nullable=True)
    responsavel_coloracao = Column(String, nullable=True)
    liberada_tecnica = Column(Boolean, default=False, nullable=False)
    data_liberacao_tecnica = Column(String, nullable=True)
    responsavel_liberacao = Column(String, nullable=True)
    identidade_confirmada = Column(Boolean, default=False, nullable=False)
    enviada_microscopia = Column(Boolean, default=False, nullable=False)
    identificada_microscopia = Column(Boolean, default=False, nullable=False)
    arquivada = Column(Boolean, default=False, nullable=False)
    local_arquivo = Column(String, nullable=True)
    data_arquivamento = Column(String, nullable=True)
    status_lamina = Column(String, nullable=False, default="Gerada no Corte")
    created_at = Column(DateTime, default=_agora, nullable=False)


class ComplementoSAP(Base):
    """Solicitação de Imuno-histoquímica ou complementos originada na Microscopia (RF032, RF036, RF037)."""
    __tablename__ = "sap_complementos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exame_id = Column(Integer, ForeignKey("sap_exames.id"), nullable=False, index=True)
    bloco_id = Column(Integer, ForeignKey("sap_blocos.id"), nullable=True)
    tipo_pedido = Column(String, nullable=False)  # 'IHQ', 'NOVO_CORTE', 'COLORACAO_ESPECIAL', 'REVISAO_MACRO'
    marcadores = Column(String, nullable=True, index=True)  # Ex: Ki-67, CD20, RE, RP, HER2
    justificativa = Column(Text, nullable=False)
    solicitante = Column(String, nullable=False)
    data_solicitacao = Column(String, nullable=False)
    status_pedido = Column(String, nullable=False, default="Pendente no Processamento")
    exame_ihq_gerado = Column(String, nullable=True)
    responsavel_atendimento = Column(String, nullable=True)
    data_conclusao = Column(String, nullable=True)
    created_at = Column(DateTime, default=_agora, nullable=False)


class MovimentacaoSAP(Base):
    """Histórico imutável de transições de etapas da peça e subprodutos (RF040, RNF010)."""
    __tablename__ = "sap_movimentacoes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    exame_id = Column(Integer, ForeignKey("sap_exames.id"), nullable=False, index=True)
    codigo_subproduto = Column(String, nullable=False, index=True)
    tipo_subproduto = Column(String, nullable=False)  # EXAME, FRASCO, CASSETE, BLOCO, LAMINA
    etapa = Column(String, nullable=False)
    acao = Column(Text, nullable=False)
    perfil = Column(String, nullable=False)
    operador = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)
    created_at = Column(DateTime, default=_agora, nullable=False)


class ImpressoraEstacaoSAP(Base):
    """Configuração de impressoras térmicas Zebra/Argox por ponto de uso (RF054, RF055)."""
    __tablename__ = "sap_impressoras_estacao"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    estacao = Column(String, unique=True, nullable=False, index=True)  # Triagem, Macroscopia, Processamento, Microscopia
    nome_impressora = Column(String, nullable=False)
    fabricante_modelo = Column(String, nullable=False)                 # Zebra ZD220 (ZPL) / Argox OS-214 (PPLA)
    linguagem = Column(String, nullable=False, default="ZPL")
    endereco_conexao = Column(String, nullable=False)                  # Ex: tcp://10.22.14.51:9100 ou USB001
    dpi = Column(Integer, nullable=False, default=203)
    tamanho_etiqueta = Column(String, nullable=False, default="40x25mm (Resistente Xilol/Álcool)")
    impressao_automatica = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=_agora, onupdate=_agora, nullable=False)
