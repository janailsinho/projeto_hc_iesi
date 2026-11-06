# SISPATO (HC-UFPE) — Documento de Validação e Especificação de Negócio

> **Padrão Oficial SETISD / HC-UFPE (HU Brasil) — Fase 0 (Alinhamento de Negócio)**  
> **Público-alvo:** Profissionais das áreas envolvidas e Equipe de TI.  
> **Objetivo:** Descrever o processo de trabalho em **linguagem pura de negócio** (sem jargões técnicos de programação ou banco de dados) para validação, alinhamento de expectativas e tomada de decisão antes de qualquer codificação.

---

## 1. Identificação do Projeto e Contexto Institucional

| Campo | Descrição |
| :--- | :--- |
| **Nome do Sistema** | SISPATO — Sistema Integrado de Gestão do Serviço de Anatomia Patológica |
| **Área Solicitante / Cliente** | Unidade de Anatomia Patológica — Serviço de Anatomia Patológica (SAP / HC-UFPE) |
| **Instância Superior Competente** | Divisão de Apoio Diagnóstico e Terapêutico (DADT) / Gerência de Atenção à Saúde (GAS) |
| **Líder Técnico (SETISD)** | Daniel Turmina / Equipe SETISD — Equipe 6 (IESI - CIn/UFPE) |
| **Objetivo Estratégico HU Brasil** | Qualificar a assistência hospitalar, garantir a segurança do paciente oncológico e promover a transformação digital dos processos diagnósticos na rede EBSERH. |

---

## 2. O Problema que Queremos Resolver

> **Objetivo:** Dizer com clareza qual é o problema real de trabalho. Sem rodeios: o que hoje está quebrado, ineficiente ou gerando risco para o hospital?

- **A Dor Central:**  
  O sistema corporativo nacional da EBSERH (AGHU/AGHUx) não possui módulo nativo de Anatomia Patológica, obrigando o SAP do HC-UFPE a gerir amostras, bancadas técnicas e prazos de forma fragmentada e manual — dividindo a rotina entre 3 telas genéricas do AGHU, planilhas paralelas no Microsoft Teams, livros de protocolo físicos e fichas de papel.

- **Por que isso não pode continuar (Impactos Reais):**
  - **Sobrecarga de Trabalho:** Recepcionistas, técnicos e médicos residentes perdem horas redigitando dados de pacientes e exames em planilhas do Teams e livros de papel para suprir a falta de fluxo contínuo no AGHU.
  - **Falta de Visibilidade:** A chefia e os médicos assistentes não sabem em tempo real em qual bancada (Recepção, Macroscopia, Processamento Técnico ou Microscopia) a amostra está, exigindo buscas manuais em gavetas e arquivos físicos.
  - **Risco Institucional e Legal:** Inexistência de alertas automáticos para o cumprimento da **Lei Federal nº 12.732/12 (Lei dos 60 Dias para início do tratamento oncológico)** e da meta interna de **20 dias** para liberação de laudos, além do risco de atraso no reingresso de peças de Congelação (CO) para análise histopatológica definitiva.

---

## 3. Como o Processo Funciona Hoje (A Rotina Atual)

> **Objetivo:** Mapear a realidade crua de como as equipes se viram no dia a dia para realizar essa tarefa hoje.

- **Meios Utilizados Hoje:**  
  Telas avulsas do AGHU, planilhas compartilhadas no Microsoft Teams, livros de carga físicos impressos, caneta marcadora em frascos, pranchetas físicas com tarjas vermelhas (para sinalizar urgências oncológicas) e chamadas telefônicas (para resultados de congelação intraoperatória).

- **A Rotina Prática de Trabalho:**
  1. **Início (Recepção e Triagem):** Para amostras internas, o operador abre 3 telas distintas no AGHU para conferir o pedido, redigita tudo numa planilha do Teams para gerar o código anual sequencial, escreve o código à mão no frasco com caneta marcadora e anota no livro físico. Para amostras externas (Prefeituras), preenche outra planilha no Teams para que a Central de Regulação crie o prontuário no AGHU antes de poder dar entrada no exame.
  2. **Preenchimento (Macroscopia e Bancadas):** Residentes e técnicos clivam a peça cirúrgica, anotam manualmente a quantidade de fragmentos e cassetes (letras A, B, C...) na planilha do Teams, digitam o texto macroscópico no AGHU e usam pranchetas vermelhas físicas para destacar pacientes oncológicos ou internados. No caso de Congelação (CO), o resultado é passado por telefone ao cirurgião em 30 minutos, mas o retorno da amostra física para o fluxo Histopatológico (Solicitação 2) depende de controle manual.
  3. **Conferência (Microscopia e Solicitações Extras):** Os médicos patologistas e residentes avaliam as lâminas e digitam o laudo. Caso precisem de novos cortes, colorações especiais, revisão de peça ou Imunohistoquímica (IHQ — que exige laudo independente ou envio externo ao A.C. Camargo), o retorno da demanda ao laboratório técnico ocorre por comunicação verbal ou anotações em papel.
  4. **Entrega e Arquivo:** Após a liberação do laudo no AGHU, as fichas em papel, blocos de parafina e lâminas são guardados fisicamente em gavetas, tornando qualquer consulta de histórico ou rastreio de pendências lenta e dependente de busca presencial.

---

## 4. O Que a Nova Solução Deve Entregar (Resultado Esperado)

> **Objetivo:** Definir com clareza o que a solução digital deve trazer para eliminar a dor do processo atual.

- **A Proposta de Valor:** Centralizar toda a jornada da amostra anatomopatológica (Histopatológico, Congelação, Imunohistoquímica, Citopatologia Geral e Citologia Cérvico-Vaginal) em um ambiente web integrado ao banco de dados do AGHU, garantindo rastreabilidade por QR Code em cada bancada e monitoramento automático de SLAs.
- **Ganhos Práticos Imediatos:**
  - Fim do livro de protocolo físico, das planilhas paralelas no Microsoft Teams e das pranchetas vermelhas manuais.
  - Geração automática do código anual do SAP e de etiquetas com QR Code na recepção.
  - Alerta visual automático de prazos críticos (**Meta interna de 20 dias** e **Lei dos 60 dias da Oncologia**).
  - Rastreabilidade completa de check-in/check-out nas bancadas (quem manipulou, em qual etapa, data e hora).
  - Painel gerencial em tempo real com a fila de exames por etapa do processo para a chefia e equipe médica.

---

## 5. Como Será o Trabalho no Novo Sistema (O Novo Fluxo)

> **Objetivo:** Explicar em linguagem direta como o usuário vai interagir com o sistema, resolvendo a dor do processo manual de ponta a ponta.

- **1. Os dados já vêm prontos:** Ao informar o número da requisição ou prontuário do AGHU, o sistema puxa automaticamente os dados demográficos e clínicos do paciente, gera o protocolo anual (`SAP-AAAA-NNN`) e emite o QR Code de rastreabilidade sem redigitação.
- **2. Preenchimento rápido com travas contra erros:** Nas bancadas de Macroscopia e Processamento Técnico, os profissionais bipam o QR Code da amostra, registram a quantidade de cassetes/fragmentos e o laudo macroscópico preliminar com máscaras padronizadas. Em exames de Congelação, o sistema vincula automaticamente a Solicitação 1 (CO) à Solicitação 2 (HP), impedindo que a peça fique esquecida após a cirurgia.
- **3. Aprovação e fluxos de retorno com um clique:** Na análise microscópica, se o patologista precisar de recorte, coloração especial ou Imunohistoquímica (IHQ), solicita diretamente na tela, devolvendo o item para a fila técnica com alerta visual. Concluído o diagnóstico, a liberação registra a autoria, data e hora.
- **4. Informação pronta e disponível:** O **Painel SAP** exibe em tempo real os indicadores estratégicos (Total, Em Processamento, Alerta Meta 20 Dias, Lei 60 Dias Oncologia e Concluídos/Arquivados), permitindo localizar qualquer amostra ou histórico de auditoria com um clique.

---

## 6. Quem Participa do Processo (Atores: Como Faz Hoje vs. Como Fará no Sistema)

| Ator / Perfil no Hospital | O que faz HOJE (Rotina Manual) | O que passará a fazer no NOVO SISTEMA | O que NÃO poderá fazer |
| :--- | :--- | :--- | :--- |
| **Recepção do SAP** | Abre 3 telas no AGHU, digita em planilha do Teams, escreve no frasco à mão e preenche livro físico. | Consulta a requisição integrada do AGHU, valida o estágio da amostra e gera o protocolo anual com etiqueta QR Code em 1 clique. | Não preenche descrições macroscópicas nem emite ou altera laudos médicos. |
| **Técnico de Laboratório** | Controla cassetes e lâminas em planilhas e papel; recebe pedidos de recorte/coloração verbalmente. | Realiza a leitura do QR Code nas bancadas (inclusão, microtomia, coloração) e visualiza fila eletrônica de recortes e IHQ. | Não altera diagnósticos médicos nem homologa laudos finais. |
| **Médico Residente / Patologista** | Digita macroscopia em sistemas separados, usa pranchetas vermelhas físicas e solicita recortes em papel. | Registra a clivagem/macroscopia estruturada, acompanha prioridades oncológicas no painel, solicita IHQ/recortes e libera laudos. | Não exclui registros de auditoria nem pula etapas obrigatórias de conferência. |
| **Chefia do SAP / Preceptoria** | Não tem visão consolidada em tempo real; precisa cruzar planilhas do Teams para identificar atrasos. | Monitora o Painel SAP em tempo real (SLAs de 20 e 60 dias), audita gargalos por etapa e gere parâmetros do serviço. | Não apaga o histórico imutável de rastreabilidade das amostras. |
| **Central de Regulação / Médicos Assistentes** | Trocam planilhas no Teams para cadastrar pacientes externos ou ligam para o SAP perguntando sobre laudos. | Cadastram o prontuário no AGHU (consumido automaticamente pelo SISPATO) e consultam o status atualizado do exame sem ligar para o laboratório. | Não manipulam etapas internas de bancada do laboratório. |

---

## 7. Regras de Negócio Inegociáveis (RNs)

- **RN-01 (Identificação Institucional e Rastreabilidade Única):** Todo exame recebido deve possuir vínculo obrigatório com a requisição/prontuário do AGHU e receber um código anual sequencial único (`SAP-AAAA-NNN`) atrelado a um QR Code para leitura óptica em todas as etapas.
- **RN-02 (Monitoramento Automático de SLAs — Meta 20 Dias e Lei 60 Dias):** O sistema deve calcular automaticamente a contagem regressiva de prazos a partir da entrada da amostra, destacando visualmente casos com suspeita de neoplasia (Oncologia — Lei nº 12.732/12 de 60 dias) e exames próximos do limite interno de 20 dias.
- **RN-03 (Preservação e Imutabilidade do Histórico / Trilha de Auditoria):** Cada mudança de etapa na fila de trabalho (Recepção, Macroscopia, Processamento Técnico, Microscopia, Liberação e Arquivamento) grava um registro imutável contendo etapa, perfil, operador, data/hora e ação realizada.
- **RN-04 (Vínculo Obrigatório no Ciclo de Congelação — CO para HP):** Exames intraoperatórios de Congelação (Solicitação 1) não podem ser dados como encerrados definitivamente sem a geração ou vinculação automática da pendência de reentrada para o exame Histopatológico definitivo (Solicitação 2).
- **RN-05 (Autonomia Diagnóstica da Imunohistoquímica — IHQ):** Solicitações de Imunohistoquímica (originadas de casos internos do HC ou de blocos/lâminas externas) geram fluxo e laudo diagnóstico independentes, mantendo o vínculo referencial com o exame anatomopatológico de origem.
- **RN-06 (Autenticação Institucional e Controle por Perfil):** O acesso ao sistema exige autenticação institucional vinculada aos perfis do hospital (AD/LDAP e grupos de acesso), restringindo ações críticas de bancada e de gestão conforme o papel do usuário.

---

## 8. Painel de Gestão e Indicadores Estratégicos (KPIs)

O sistema disponibiliza no **Painel SAP** os seguintes indicadores em tempo real para a gestão e equipe operacional:
1. **Total no Sistema e Em Processamento:** Visão quantitativa imediata do volume total de exames ativos e de quantos encontram-se circulando nas bancadas técnicas.
2. **Alerta Meta 20 Dias:** Contador em destaque (com alerta visual pulsante) indicando quantos exames estão em faixa crítica para atingir o prazo interno de 20 dias de liberação do laudo.
3. **Lei 60 Dias (Oncologia):** Indicador dedicado exclusivamente aos exames com suspeita ou confirmação de neoplasia maligna, assegurando prioridade absoluta para cumprimento da legislação federal.
4. **Concluídos e Arquivados:** Totalizador de exames cujo ciclo diagnóstico e arquivamento físico de lâminas/blocos foram devidamente finalizados e homologados.

---

## 9. Matriz de Pontos de Decisão (Gabinete / Gestão do Negócio)

> *Itens de governança e operação acompanhados junto à gestão do SAP e SETISD:*

| # | Ponto a Decidir | Impacto no Processo | Quem deve decidir? | Status / Definição |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **Integração de Pacientes Externos (Prefeituras):** Momento exato do disparo da requisição após criação do prontuário pela Regulação. | Elimina a planilha intermediária do Teams entre a Recepção do SAP e a Central de Marcação. | Chefia do SAP / Regulação / SETISD | 🟢 Definido (Consulta via AGHU Slave) |
| **2** | **Faixa de Alerta Preventivo da Meta de 20 Dias:** Com quantos dias restantes o card do exame deve mudar para estado de alerta crítico? | Define a antecedência com que a chefia e os patologistas serão notificados sobre risco de atraso. | Chefia do SAP | 🟡 Em validação nos checkpoints |
| **3** | **Fluxo de Logística Externa (A.C. Camargo):** Padronização do status de suspensão de SLA quando o bloco segue para laboratório de apoio externo. | Evita penalização indevida nos indicadores internos da equipe durante o trânsito externo da amostra. | Chefia do SAP / DADT | 🟡 Em definição |
