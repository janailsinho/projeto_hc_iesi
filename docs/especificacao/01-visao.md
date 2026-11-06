# Documento de Visão — SISPATO (HC-UFPE / EBSERH)

## 1. Problema e Oportunidade
- **O Problema**: O sistema hospitalar nacional utilizado pelo HC-UFPE (AGHU/AGHUx da EBSERH) não dispõe de um módulo de Anatomia Patológica. Como consequência, o Serviço de Anatomia Patológica (SAP) opera de maneira descentralizada, utilizando múltiplas telas do AGHU apenas para consultas básicas, combinadas com planilhas paralelas no Microsoft Teams, livros de protocolo em papel, marcações manuais em frascos e pranchetas físicas para controle de urgências.
- **Impacto**: Retrabalho diário de digitação na recepção e na macroscopia, alto risco de perda de rastreabilidade física de amostras (especialmente na transição de exames de Congelação para Histopatológico e em solicitações de Imunohistoquímica), demora no atendimento de amostras externas (Prefeituras) e ausência de alertas automatizados para evitar o descumprimento da meta interna de 20 dias e da **Lei Federal nº 12.732/12 (Lei dos 60 Dias para pacientes oncológicos)**.
- **Solução Proposta**: Desenvolvimento do **SISPATO**, uma aplicação web construída sobre o framework oficial do SETISD/HC-UFPE (FastAPI + Vue 3), integrada à base de dados do AGHU (AGHU Slave), para gerir de ponta a ponta o fluxo *To-Be* do laboratório: recepção automatizada com geração de QR Code, rastreabilidade de bancadas, controle estruturado de macroscopia/microscopia e painel gerencial de SLAs em tempo real.

## 2. Partes Interessadas (Stakeholders)
- **Usuários Finais Operacionais**: Recepcionistas do SAP, Técnicos de Laboratório (Histotécnicos/Citotécnicos), Médicos Residentes de Patologia e Médicos Patologistas/Citopatologistas.
- **Gestão e Preceptoria**: Chefia da Unidade de Anatomia Patológica, Divisão de Apoio Diagnóstico e Terapêutico (DADT) e Gerência de Atenção à Saúde (GAS).
- **Áreas Parceiras e Patrocinadores Técnicos**: Setor de Tecnologia da Informação e Saúde Digital (SETISD / HC-UFPE — Liderança Técnica: Daniel Turmina), Central de Marcação/Regulação e Equipe 6 da disciplina de IESI (CIn/UFPE).
- **Beneficiários Finais**: Médicos assistentes/cirurgiões das clínicas do HC-UFPE e pacientes do SUS (internos e oriundos de Prefeituras parceiras), especialmente pacientes em investigação ou tratamento oncológico.

## 3. Escopo do Produto
- **Funcionalidades Principais (Dentro do Escopo)**:
  - **Painel Gerencial e de Filas (Painel SAP)**: Dashboard em tempo real com KPIs de volume, exames em processamento, alertas da Meta de 20 dias, monitoramento da Lei dos 60 dias (Oncologia) e exames concluídos/arquivados.
  - **Recepção e Triagem Integrada**: Consulta unificada de pacientes e requisições via AGHU Slave, suporte aos 5 tipos de exames (Histopatológico, Congelação, Imunohistoquímica, Citopatologia Geral e Citologia Cérvico-Vaginal) e geração de código anual (`SAP-AAAA-NNN`) com QR Code.
  - **Rastreabilidade e Auditoria por Etapa**: Registro completo de movimentação da amostra pelas etapas do processo (*Recepção / Triagem*, *Macroscopia*, *Processamento Técnico*, *Microscopia / Laudo* e *Arquivamento*), gravando operador, perfil, data/hora e ação.
  - **Gestão de Fluxos Especiais**: Sinalização visual automática para casos oncológicos (`Onco`), controle de vínculo entre Congelação (CO) e Histopatológico (HP), e acompanhamento de demandas complementares (recortes, colorações especiais e IHQ interna ou externa via A.C. Camargo).
  - **Autenticação e Governança de Acesso (RBAC)**: Login institucional integrado (AD/LDAP do hospital) com restrição de telas e ações conforme o perfil do usuário.
- **Limites do Projeto (Fora do Escopo)**:
  - Substituição do prontuário eletrônico oficial do paciente no AGHU (o SISPATO atua como sistema especialista complementar, mantendo o AGHU como repositório final do prontuário médico).
  - Faturamento hospitalar direto no SIA/SIH-SUS (que permanece sob responsabilidade dos módulos administrativos nativos da EBSERH).

## 4. Metas e Objetivos de Negócio
- **Redução de 60% no tempo de recepção e triagem de amostras**: Eliminar a navegação fragmentada em 3 telas do AGHU e a redigitação manual em planilhas do Microsoft Teams e livros físicos.
- **100% de visibilidade e rastreabilidade digital**: Garantir que toda amostra receba identificador único (QR Code) e possua histórico auditável de quem a manipulou em cada etapa técnica.
- **Conformidade com SLAs Clínicos e Legais**: Monitorar 100% dos exames com suspeita de neoplasia sob o teto da **Lei dos 60 Dias** e reduzir atrasos na meta interna de **20 dias** por meio de alertas visuais preventivos no Painel SAP.
- **Eliminação de falhas na transição de exames críticos**: Assegurar que 100% das peças submetidas a Congelação intraoperatória (CO) reingressem automaticamente na fila de análise Histopatológica (HP).