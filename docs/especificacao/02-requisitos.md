# Especificação de Requisitos — SISPATO (HC-UFPE / EBSERH)

## 1. Requisitos Funcionais (RF)

| ID | Título | Descrição | Prioridade |
| :--- | :--- | :--- | :---: |
| **RF001** | Autenticação e Controle de Acesso (RBAC) | Login via LDAP/AD do hospital (`EBSERHNET`) com distinção de permissões por perfil (Recepção, Técnico, Residente/Patologista e Chefia/Admin). | Essencial |
| **RF002** | Consulta Integrada de Pacientes (AGHU Slave) | Busca de pacientes e requisições médicas diretamente na base replicada do AGHU (ou carga estruturada CSV/PostgreSQL) por prontuário ou código. | Essencial |
| **RF003** | Recepção de Amostras e Geração de QR Code | Registro de entrada dos 5 tipos de exames (HP, CO, IHQ, CG, CCV), gerando código anual sequencial (`SAP-AAAA-NNN`) e código QR técnico vinculado à requisição AGHU. | Essencial |
| **RF004** | Painel SAP de Monitoramento e SLAs (KPIs) | Exibição em tempo real dos contadores estratégicos (Total, Em Processamento, Alerta Meta 20 Dias, Lei 60 Dias Oncologia e Concluídos) e fila de exames por etapa. | Essencial |
| **RF005** | Trilha de Rastreabilidade e Histórico do Exame | Visualização e registro detalhado do histórico de eventos da amostra (etapa, perfil, operador, data/hora e ação executada) e status dos laudos macroscópico e AGHU. | Essencial |
| **RF006** | Registro de Macroscopia e Controle de Cassetes | Inclusão de descrição macroscópica preliminar estruturada, contagem de fragmentos e identificação de cassetes/blocos para processamento técnico. | Importante |
| **RF007** | Vinculação Automática Congelação (CO) → HP | Garantia de transição automática da amostra da Solicitação 1 (Congelação intraoperatória) para a fila da Solicitação 2 (Histopatológico definitivo). | Importante |
| **RF008** | Gestão de Solicitações Internas e IHQ | Fluxo de retorno para bancada técnica (novos cortes, colorações especiais, revisão de peça) e abertura de exame independente de Imunohistoquímica (interna ou externa). | Desejável |

### 📌 Legenda de Níveis de Prioridade:
- **Essencial (Alta):** Funcionalidade indispensável para o funcionamento básico da aplicação e validação do MVP nos checkpoints. Sem ela, o sistema não atende ao fluxo mínimo de rastreabilidade.
- **Importante (Média):** Funcionalidade que agrega valor significativo ao negócio e consolida o fluxo *To-Be* das bancadas, mas cuja ausência temporária não impede a operação mínima do painel e da recepção.
- **Desejável (Baixa):** Funcionalidade complementar ou desdobramento de subfluxos específicos que podem ser implementados em sprints evolutivas futuras.

---

## 2. Requisitos Não Funcionais (RNF)

| ID | Categoria | Descrição |
| :--- | :--- | :--- |
| **RNF001** | Criptografia e Sessão | Tokens JWT assinados com HS256 e Cookies HttpOnly para Refresh Tokens, garantindo sessão segura entre o frontend Vue 3 e o backend FastAPI. |
| **RNF002** | LGPD / Auditoria Hospitalar | Trilha de auditoria obrigatória e imutável para todas as movimentações de amostras e alterações de status, identificando matrícula/operador e timestamp. |
| **RNF003** | Segurança HTTP | Middleware de Security Headers (anti-cache `no-store`, `X-Frame-Options: DENY`, proteção anti-XSS e configuração estrita de CORS). |
| **RNF004** | Governança de Segredos | Proibição de credenciais sensíveis hardcoded no código-fonte e validação estrita de variáveis de ambiente na inicialização (`src/config.py`). |
| **RNF005** | Usabilidade e Padronização UI | Interface responsiva aderente ao Design System do template oficial SETISD/HC-UFPE, apresentando nomenclatura de negócio limpa (sem jargões de modelagem como "Lanes"). |

---

## 3. Detalhamento SDD (CARE)

Para cada requisito essencial, a implementação e validação seguem o padrão CARE:

### [CARE-RF001] Autenticação LDAP e Controle de Perfis
- **Context (Contexto)**: Servidor LDAP/AD configurado (ou provedor Mock de desenvolvimento ativo) e rotas de autenticação (`/api/login`, `/api/token/refresh`, `/api/users/me`) disponíveis no backend FastAPI.
- **Action (Ação)**: Autenticar credenciais do usuário, gerar token JWT contendo os grupos de acesso (`ADMIN`, `SAP_GESTOR`, etc.) e aplicar guardas de rota no Vue Router e nos componentes visuais.
- **Result (Resultado)**: Usuário autenticado com sucesso é direcionado ao sistema; telas administrativas exibem trava de "Acesso Restrito" para perfis sem privilégio de administrador.
- **Evaluation (Avaliação)**: Testar o fluxo de login em `/login`, verificar a resposta `200 OK` nos endpoints de sessão e validar a restrição de perfil em `/configuracoes`.

### [CARE-RF002] Consulta Integrada de Pacientes (AGHU Slave / CSV)
- **Context (Contexto)**: Base de dados de pacientes e conexão de leitura com o AGHU Slave (ou repositório local de contingência) configuradas no módulo `src/routers/paciente.py`.
- **Action (Ação)**: Executar requisição `GET /api/pacientes` filtrando por código ou prontuário a partir da tela de consulta do frontend.
- **Result (Resultado)**: Listagem paginada e imediata contendo prontuário, nome do paciente, data de nascimento e nome da mãe, evitando redigitação manual na recepção.
- **Evaluation (Avaliação)**: Acessar a rota `/exemplo`, realizar busca por prontuário e confirmar retorno `200 OK` com renderização imediata na tabela.

### [CARE-RF003 / RF004 / RF005] Painel SAP, Filas do Processo e Auditoria de SLAs
- **Context (Contexto)**: Rotas do módulo SAP (`src/routers/sap.py`) registradas na aplicação principal (`src/main.py`) e view `SAPDashboardView.vue` integrada ao menu lateral do layout padrão.
- **Action (Ação)**: Consumir o endpoint `GET /api/sap/exames` ao carregar o Painel SAP (`/sap`) ou ao acionar o botão "Atualizar Painel", e abrir o modal "Visualizar Histórico" de cada exame.
- **Result (Resultado)**: Exibição dos 5 KPIs estratégicos (Total, Em Processamento, Alerta Meta 20 Dias, Lei 60 Dias Oncologia e Concluídos), tabela de exames com tags de prioridade (`Onco`), etapas do processo e modal contendo QR Code técnico, status dos laudos e trilha de auditoria completa.
- **Evaluation (Avaliação)**: Verificar resposta `200 OK` em `GET /api/sap/exames`, confirmar renderização sem erros de console em `http://localhost:5173/sap` e inspecionar os logs de auditoria no modal de detalhes.