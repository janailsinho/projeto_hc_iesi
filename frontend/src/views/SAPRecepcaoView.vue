<template>
  <div class="min-h-screen bg-slate-50 p-3 sm:p-6 space-y-4 sm:space-y-6">
    <!-- Cabeçalho da Tela de Recepção -->
    <header class="flex flex-col justify-between gap-3 lg:flex-row lg:items-center bg-white p-4 sm:p-5 rounded-xl shadow-sm border border-slate-200">
      <div>
        <h1 class="text-lg sm:text-2xl md:text-3xl font-extrabold text-blue-900 tracking-tight">
          Recepção e Triagem de Amostras (HC / AGHU & SUS)
        </h1>
        <p class="text-sm text-slate-600 mt-1">
          Leitura via bipador (7 ou 10 dígitos), conferência por amostra, controle de rejeições, etiquetas Zebra/Argox (Norma Zero) e Ficha de Trabalho
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <!-- Simulador de Perfil de Acesso (RBAC - RF002) -->
        <div class="bg-slate-100 px-3 py-2 rounded-lg border border-slate-300 flex items-center gap-2">
          <span class="text-xs font-bold uppercase text-slate-500">Perfil Ativo:</span>
          <select v-model="perfilAtivo" class="bg-transparent text-xs font-bold text-blue-900 focus:outline-none cursor-pointer">
            <option value="Recepcionista">Recepcionista (Triagem)</option>
            <option value="Macroscopista">Macroscopista</option>
            <option value="Técnico de Laboratório">Técnico de Laboratório</option>
            <option value="Residente">Residente</option>
            <option value="Médico Patologista">Médico Patologista</option>
          </select>
        </div>

        <router-link
          to="/sap"
          class="bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold px-4 py-2 rounded-lg transition text-sm">
          ← Painel SAP
        </router-link>
      </div>
    </header>

    <!-- Alerta RBAC (RF002) -->
    <div v-if="perfilAtivo !== 'Recepcionista' && perfilAtivo !== 'Médico Patologista'" class="p-4 bg-rose-50 border-l-4 border-rose-600 text-rose-900 rounded-lg text-sm shadow-sm">
      ⚠️ <strong>Controle de Acesso por Perfil (RBAC - RF002):</strong> O perfil <strong>{{ perfilAtivo }}</strong> possui acesso somente leitura na Triagem. Altere para <strong>Recepcionista</strong> para registrar recebimentos ou rejeições.
    </div>

    <!-- Abas de Fluxo da Recepção (RF005: Identificação da Origem HC vs SUS + Devoluções) -->
    <div class="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
      <button
        @click="abaAtiva = 'HC'"
        :class="abaAtiva === 'HC' ? 'bg-blue-800 text-white shadow' : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-300'"
        class="px-4 py-2.5 rounded-xl font-bold text-xs transition">
        🏥 1. Peça Interna HC-UFPE (Importação AGHU / Bipador)
      </button>
      <button
        @click="abaAtiva = 'SUS'"
        :class="abaAtiva === 'SUS' ? 'bg-emerald-700 text-white shadow' : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-300'"
        class="px-4 py-2.5 rounded-xl font-bold text-xs transition">
        🚑 2. Peça Externa SUS / Prefeituras (Cadastro CNS/CPF)
      </button>
      <button
        @click="abaAtiva = 'REJEICOES'; carregarRejeicoes()"
        :class="abaAtiva === 'REJEICOES' ? 'bg-rose-700 text-white shadow' : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-300'"
        class="px-4 py-2.5 rounded-xl font-bold text-xs transition">
        📋 3. Relação de Amostras Rejeitadas / Devolvidas ({{ listaRejeicoes.filter(r => !r.superada).length }})
      </button>
    </div>

    <!-- Alertas de Erro -->
    <div v-if="erroRecebimento" class="p-4 bg-rose-100 border-l-4 border-rose-600 text-rose-800 text-sm rounded-lg">
      {{ erroRecebimento }}
    </div>

    <!-- CARD DE SUCESSO: ETIQUETAS INDIVIDUAIS (NORMA ZERO) + FICHA DE TRABALHO ÚNICA -->
    <div v-if="exameRecemGerado" class="p-5 bg-emerald-50 border-2 border-emerald-500 text-emerald-950 rounded-xl shadow-sm space-y-4">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <span class="text-xs font-extrabold uppercase bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded">
            Recebimento Concluído & Encaminhado para {{ exameRecemGerado.etapa_atual }}
          </span>
          <h3 class="text-xl font-extrabold mt-1">
            Código SAP Gerado: <span class="font-mono text-blue-900">{{ exameRecemGerado.codigo_sap }}</span>
            <span v-if="exameRecemGerado.urgente" class="ml-2 px-2 py-0.5 bg-red-600 text-white text-xs rounded">URGENTE</span>
          </h3>
          <p class="text-xs text-slate-700 mt-0.5">
            QR Code: <code class="bg-white px-2 py-0.5 rounded border font-mono">{{ exameRecemGerado.qr_code }}</code> • Solicitação #{{ exameRecemGerado.codigo_solicitacao }}
            <span v-if="exameRecemGerado.exame_origem_codigo"> • Vínculo: <strong>{{ exameRecemGerado.exame_origem_codigo }}</strong></span>
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button
            @click="modalFichaAberta = true"
            class="bg-blue-700 hover:bg-blue-800 text-white font-bold px-4 py-2 rounded-lg text-xs shadow transition">
            🖨️ Imprimir Ficha de Trabalho (Única da Recepção)
          </button>
          <router-link
            to="/bancadas"
            class="bg-indigo-700 hover:bg-indigo-800 text-white font-bold px-4 py-2 rounded-lg text-xs shadow transition">
            Ir para Macroscopia →
          </router-link>
        </div>
      </div>

      <!-- Impressão Individual de Etiqueta por Frasco (Pedido de Rodolfo na reunião pág. 19 + Norma Zero Jaque) -->
      <div class="bg-white p-4 rounded-xl border border-emerald-200">
        <h4 class="text-xs font-bold uppercase text-slate-700 mb-2">
          🏷️ Etiquetas Térmicas Zebra/Argox por Frasco (Norma Zero: Nome do Paciente + Prontuário/Nasc) — Reimprima individualmente se rasgar/molhar:
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <div
            v-for="etq in exameRecemGerado.etiquetas_frascos"
            :key="etq.qr_code"
            class="p-3 bg-slate-50 rounded-lg border border-slate-300 text-xs flex flex-col justify-between gap-2"
          >
            <div>
              <div class="flex justify-between font-mono font-extrabold text-blue-900">
                <span>{{ exameRecemGerado.codigo_sap }} (Frasco #{{ etq.numero_amostra }})</span>
                <span>AGHU #{{ exameRecemGerado.codigo_solicitacao }}</span>
              </div>
              <p class="font-bold text-slate-900 mt-1">Pac: {{ etq.nome_paciente }}</p>
              <p class="text-[11px] text-slate-600">{{ etq.segundo_identificador }}</p>
              <p class="text-[11px] text-emerald-800 font-semibold mt-1">Mat: {{ etq.descricao_material }}</p>
              <p class="font-mono text-[10px] text-slate-500 mt-1">QR: {{ etq.qr_code }} | Bip: {{ etq.codigo_bipagem }}</p>
            </div>
            <button
              @click="etiquetaSelecionadaZPL = etq"
              class="w-full bg-slate-800 hover:bg-slate-900 text-white font-semibold py-1.5 rounded text-xs transition">
              🖨️ Imprimir Somente Etiqueta #{{ etq.numero_amostra }} (ZPL)
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- ABA 1: PEÇA INTERNA HC (INTEGRAÇÃO AGHU + BIPADOR 7 OU 10 DÍGITOS)     -->
    <!-- ======================================================================= -->
    <div v-if="abaAtiva === 'HC'" class="space-y-6">
      <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <label class="block text-xs font-bold uppercase text-slate-700 mb-2">
          1. Bipar Código de Barras (7 dígitos da Solicitação ou 10 dígitos Solicitação+Amostra) ou Buscar Prontuário:
        </label>
        <div class="flex flex-col sm:flex-row gap-3">
          <input
            v-model="inputCodigoSolicitacao"
            @keyup.enter="consultarSolicitacaoCSV"
            type="text"
            placeholder="Bipe com a pistola HID (ex: 1479367001 ou 1479367) ou digite nº da solicitação / prontuário..."
            class="flex-1 border border-slate-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
          />
          <button
            @click="consultarSolicitacaoCSV"
            class="bg-blue-700 hover:bg-blue-800 text-white font-semibold px-6 py-2.5 rounded-lg text-sm shadow transition">
            🔍 Consultar no AGHU
          </button>
        </div>

        <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span>💡 <strong>Casos reais do CSV para testar cenários da reunião:</strong></span>
          <button @click="testarCodigo('1479367')" class="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-900 rounded border border-indigo-300 font-mono font-semibold">
            1479367 (Misto: HP + IHQ na mesma solicitação)
          </button>
          <button @click="testarCodigo('1479377001')" class="px-2.5 py-1 bg-blue-50 hover:bg-blue-100 text-blue-900 rounded border border-blue-300 font-mono font-semibold">
            1479377001 (Bipador 10 dígitos: Amostra 001)
          </button>
          <button @click="testarCodigo('1479445')" class="px-2.5 py-1 bg-slate-100 hover:bg-blue-50 text-blue-800 rounded border border-slate-300 font-mono font-semibold">
            1479445 (1 amostra - HP Onco)
          </button>
          <button @click="testarCodigo('1479326')" class="px-2.5 py-1 bg-slate-100 hover:bg-blue-50 text-blue-800 rounded border border-slate-300 font-mono font-semibold">
            1479326 (Múltiplos frascos - Colonoscopia)
          </button>
        </div>
      </div>

      <!-- Resultado da Consulta AGHU -->
      <div v-if="solicitacaoEncontrada" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Coluna Esquerda: Dados do Paciente e da Solicitação AGHU -->
        <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4">
          <div class="flex justify-between items-center border-b border-slate-100 pb-3">
            <h2 class="text-base font-bold text-slate-800">2. Dados Importados do AGHU</h2>
            <span class="font-mono font-bold text-blue-800 bg-blue-50 px-2.5 py-1 rounded text-xs">
              #{{ solicitacaoEncontrada.codigo_solicitacao }}
            </span>
          </div>

          <div class="space-y-3 text-xs">
            <div>
              <span class="text-slate-400 uppercase font-semibold block">Paciente / Prontuário (Norma Zero)</span>
              <p class="text-sm font-bold text-slate-800 mt-0.5">{{ solicitacaoEncontrada.nome_paciente }}</p>
              <p class="text-slate-600">Prontuário: <strong>{{ solicitacaoEncontrada.prontuario }}</strong> • Nasc: <strong>{{ solicitacaoEncontrada.data_nascimento }}</strong></p>
            </div>

            <div>
              <span class="text-slate-400 uppercase font-semibold block">Data / Origem / Especialidade</span>
              <p class="font-semibold text-slate-700 mt-0.5">
                {{ solicitacaoEncontrada.data_solicitacao }} — {{ solicitacaoEncontrada.origem }} ({{ solicitacaoEncontrada.unidade }} / {{ solicitacaoEncontrada.especialidade }})
              </p>
            </div>

            <div>
              <span class="text-slate-400 uppercase font-semibold block">Informações Clínicas (AGHU)</span>
              <p class="text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-200 mt-1 leading-relaxed">
                {{ solicitacaoEncontrada.informacoes_clinica || 'Sem informações clínicas adicionais registradas.' }}
              </p>
            </div>

            <div class="bg-blue-50 p-4 rounded-xl border border-blue-200 flex justify-between items-center">
              <div>
                <span class="text-[11px] uppercase font-bold text-blue-800 block">Total de Amostras na Requisição</span>
                <span class="text-xs text-slate-600">Tipo: <strong>{{ solicitacaoEncontrada.tipo_peca }}</strong></span>
                <span v-if="solicitacaoEncontrada.requer_siscan" class="block text-[11px] font-bold text-pink-700 mt-0.5">
                  🎗️ Caso Monitorado SISCAN (Mama / Colo Uterino)
                </span>
              </div>
              <span class="text-3xl font-extrabold text-blue-900">{{ solicitacaoEncontrada.total_amostras }}</span>
            </div>

            <!-- Histórico de Rejeições anteriores desta solicitação -->
            <div v-if="solicitacaoEncontrada.rejeicoes_historico && solicitacaoEncontrada.rejeicoes_historico.length" class="p-3 bg-rose-50 border border-rose-200 rounded-xl">
              <span class="font-bold text-rose-900 block mb-1">⚠️ Histórico de Rejeições desta Solicitação:</span>
              <div v-for="r in solicitacaoEncontrada.rejeicoes_historico" :key="r.id" class="text-[11px] text-rose-800 border-t border-rose-200 pt-1 mt-1">
                <strong>{{ r.motivo_padrao }}</strong> ({{ r.data_rejeicao }}) —
                <span class="font-semibold">{{ r.superada ? 'Superada ✓' : 'Aguardando correção' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Coluna Direita (2/3): Reconhecimento de Tipos de Exame, Checklist de Frascos e Recebimento/Rejeição -->
        <div class="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between space-y-5">
          <div>
            <!-- Alerta de Solicitação Mista (Ex: HP + IHQ ou CO + HP na mesma solicitação — Reunião págs. 34-40) -->
            <div v-if="solicitacaoEncontrada.multiplos_tipos_exame" class="mb-4 p-4 bg-indigo-50 border-l-4 border-indigo-600 rounded-lg text-xs text-indigo-950">
              <p class="font-bold text-sm mb-2">
                🔀 Solicitação com Múltiplos Tipos de Exame Detectados (Recepção Individualizada por Exame):
              </p>
              <p class="mb-2">
                Esta requisição possui exames distintos (ex: Histopatológico + Imuno-histoquímica). Você pode receber apenas um tipo agora (o outro ficará como <em>Aguardando Recebimento</em>, sem constar em atraso) ou receber cada código separadamente:
              </p>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="grp in solicitacaoEncontrada.grupos_exame"
                  :key="grp.prefixo_sap"
                  type="button"
                  @click="selecionarGrupoExame(grp)"
                  :class="prefixoFiltroSelecionado === grp.prefixo_sap ? 'bg-indigo-800 text-white' : 'bg-white text-indigo-900 border border-indigo-300'"
                  class="px-3 py-1.5 rounded-lg font-bold transition"
                >
                  {{ grp.prefixo_sap }} — {{ grp.tipo_exame }} ({{ grp.amostras.length }} amostra[s])
                  <span v-if="grp.ja_recebido" class="ml-1 text-emerald-300">✓ Recebido ({{ grp.codigo_sap }})</span>
                </button>
              </div>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-3 mb-4 gap-2">
              <div>
                <h2 class="text-base font-bold text-slate-800">
                  3. Conferência Física de Frascos e Descrição por Amostra ({{ amostrasMarcadas.length }} de {{ solicitacaoEncontrada.total_amostras }} selecionadas)
                </h2>
                <p class="text-xs text-slate-500">
                  Verifique se a identificação e a topografia do frasco (Amostra 1, 2, 3...) conferem com a descrição abaixo
                </p>
              </div>
              <div class="flex gap-2">
                <button
                  @click="marcarTodasAmostras"
                  type="button"
                  class="text-xs bg-blue-50 hover:bg-blue-100 text-blue-800 font-bold px-3 py-1.5 rounded-lg border border-blue-200 transition">
                  ☑️ Selecionar Pendentes
                </button>
                <button
                  @click="modalRejeicaoAberto = true"
                  type="button"
                  class="text-xs bg-rose-50 hover:bg-rose-100 text-rose-800 font-bold px-3 py-1.5 rounded-lg border border-rose-300 transition">
                  🚫 Registrar Não Conformidade / Rejeitar
                </button>
              </div>
            </div>

            <!-- Lista de Amostras / Frascos do CSV com Descrição Individual Editável -->
            <div class="space-y-2.5 max-h-80 overflow-y-auto pr-1">
              <div
                v-for="item in solicitacaoEncontrada.amostras"
                :key="item.numero_amostra"
                class="flex items-start gap-3 p-3.5 rounded-xl border transition text-xs"
                :class="[
                  item.ja_recebida
                    ? 'bg-slate-100 border-slate-300 opacity-75'
                    : amostrasMarcadas.includes(item.numero_amostra)
                    ? 'bg-emerald-50/80 border-emerald-500 shadow-sm'
                    : 'bg-slate-50 border-slate-200 hover:bg-slate-100',
                  solicitacaoEncontrada.amostra_bipada_foco === item.numero_amostra ? 'ring-2 ring-blue-600' : ''
                ]"
              >
                <input
                  type="checkbox"
                  :value="item.numero_amostra"
                  v-model="amostrasMarcadas"
                  :disabled="item.ja_recebida"
                  class="mt-1 h-4 w-4 text-emerald-600 rounded cursor-pointer"
                />
                <div class="flex-1 space-y-1.5">
                  <div class="flex flex-wrap justify-between gap-2">
                    <span class="font-bold text-slate-900 text-sm">
                      Frasco / Amostra #{{ String(item.numero_amostra).padStart(3, '0') }} — {{ item.nome_exame }} ({{ item.prefixo_sap }})
                    </span>
                    <div class="flex items-center gap-1.5">
                      <span class="font-mono text-[10px] bg-white px-2 py-0.5 rounded border border-slate-300">
                        Bip: {{ item.codigo_bipagem }}
                      </span>
                      <span
                        class="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                        :class="item.ja_recebida ? 'bg-emerald-200 text-emerald-900' : 'bg-amber-100 text-amber-900'"
                      >
                        {{ item.ja_recebida ? `Recebida (${item.codigo_sap_recebido})` : `Status AGHU: ${item.status_item_exame}` }}
                      </span>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="font-bold text-slate-700 shrink-0">Descrição da Amostra #{{ item.numero_amostra }}:</span>
                    <input
                      v-model="descricoesEditadas[item.numero_amostra]"
                      :disabled="item.ja_recebida"
                      type="text"
                      class="flex-1 bg-white border border-slate-300 rounded px-2.5 py-1 text-xs font-semibold text-slate-800"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Parâmetros de Triagem, Urgência e Botão Único de Confirmação -->
          <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-4 text-xs">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block font-bold text-slate-700 mb-1">Condição / Destino Após Triagem (RF012):</label>
                <select v-model="estagioEntrada" class="w-full border border-slate-300 rounded-lg px-3 py-2 bg-white">
                  <option value="Peça a Fresco / Formol (Para Macroscopia)">Peça em Formol / Fresco → Enviar para Macroscopia</option>
                  <option value="Bloco de Parafina Externo (Para Recorte/IHQ)">Bloco de Parafina → Enviar para Processamento Técnico</option>
                  <option value="Lâmina Pronta (Para Revisão/Microscopia)">Lâmina Externa Pronta → Enviar para Microscopia</option>
                </select>
              </div>
              <div>
                <label class="block font-bold text-slate-700 mb-1">Observações da Triagem (Opcional):</label>
                <input
                  v-model="observacaoRecepcao"
                  type="text"
                  placeholder="Opcional: observações da conferência física..."
                  class="w-full border border-slate-300 rounded-lg px-3 py-2 bg-white"
                />
              </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
              <div class="flex items-center gap-2">
                <input type="checkbox" id="checkOncoPage" v-model="flagNeoplasia" class="h-4 w-4 text-purple-600 rounded" />
                <label for="checkOncoPage" class="font-bold text-purple-900 cursor-pointer">
                  🎗️ Suspeita Oncológica (Monitorar Lei dos 60 Dias)
                </label>
              </div>
              <div class="flex items-center gap-2">
                <input type="checkbox" id="checkUrgentePage" v-model="flagUrgente" class="h-4 w-4 text-red-600 rounded" />
                <label for="checkUrgentePage" class="font-bold text-red-800 cursor-pointer">
                  🚨 Marcar como Urgente (Congelação / Paciente com Consulta Próxima)
                </label>
              </div>
            </div>

            <div v-if="flagUrgente" class="pt-1">
              <input
                v-model="motivoUrgencia"
                type="text"
                placeholder="Motivo da urgência (ex: Congelação Intraoperatória, Consulta agendada na próxima semana...)"
                class="w-full border border-red-300 rounded-lg px-3 py-1.5 bg-red-50/40 text-xs"
              />
            </div>

            <div class="flex justify-end pt-2 border-t border-slate-200">
              <button
                @click="confirmarRecebimentoHC"
                :disabled="(perfilAtivo !== 'Recepcionista' && perfilAtivo !== 'Médico Patologista') || solicitacaoEncontrada.ja_recebida || amostrasMarcadas.length === 0"
                class="w-full sm:w-auto px-6 py-3 rounded-xl text-white text-sm font-bold shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed bg-emerald-600 hover:bg-emerald-700">
                ✅ Confirmar Recebimento ({{ amostrasMarcadas.length }} amostra[s]) e Gerar Código {{ prefixoFiltroSelecionado || solicitacaoEncontrada.prefixo_sugerido }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- ABA 2: PEÇA EXTERNA SUS / PREFEITURAS (RF005, RF006)                    -->
    <!-- ======================================================================= -->
    <div v-if="abaAtiva === 'SUS'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4 text-xs">
        <h2 class="text-base font-bold text-slate-800 border-b pb-2">
          1. Identificação / Cadastro do Paciente SUS (CNS ou CPF — RF006)
        </h2>
        <p class="text-slate-500">
          O sistema verifica automaticamente se já existe registro pelo CPF ou CNS antes de criar um novo.
        </p>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="font-bold text-slate-700 block mb-1">CPF (11 dígitos):</label>
            <input v-model="formSUS.cpf" type="text" placeholder="Ex: 12345678901" class="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Cartão SUS / CNS (15 dígitos):</label>
            <input v-model="formSUS.cns" type="text" placeholder="Ex: 700001234567890" class="w-full border rounded-lg px-3 py-2" />
          </div>
          <div class="sm:col-span-2">
            <label class="font-bold text-slate-700 block mb-1">Nome Completo do Paciente:</label>
            <input v-model="formSUS.nome" type="text" placeholder="Nome completo sem abreviações" class="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Data de Nascimento:</label>
            <input v-model="formSUS.data_nascimento" type="text" placeholder="dd/mm/aaaa" class="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Município / Unidade Solicitante SUS:</label>
            <input v-model="formSUS.municipio_origem" type="text" placeholder="Ex: Prefeitura de Caruaru / UBS Centro" class="w-full border rounded-lg px-3 py-2" />
          </div>
        </div>
      </div>

      <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4 text-xs">
        <h2 class="text-base font-bold text-slate-800 border-b pb-2">
          2. Dados da Peça Externa SUS e Geração de Protocolo SAP (RF009, RF010)
        </h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="font-bold text-slate-700 block mb-1">Tipo de Exame SAP:</label>
            <select v-model="formSUS.prefixo_exame" class="w-full border rounded-lg px-3 py-2 bg-white">
              <option value="HP">HP — Histopatológico</option>
              <option value="CCV">CCV — Citologia Cérvico-Vaginal (Preventivo)</option>
              <option value="CG">CG — Citopatologia Geral</option>
              <option value="IHQ">IHQ — Imuno-histoquímica (Bloco Externo)</option>
            </select>
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Estágio Físico na Entrada:</label>
            <select v-model="formSUS.estagio_entrada" class="w-full border rounded-lg px-3 py-2 bg-white">
              <option value="Peça a Fresco / Formol (Para Macroscopia)">Frasco em Formol (Para Macroscopia)</option>
              <option value="Bloco de Parafina Externo (Para Recorte/IHQ)">Bloco de Parafina Externo (Para Recorte/IHQ)</option>
              <option value="Lâmina Pronta (Para Revisão/Microscopia)">Lâmina Externa (Para Revisão)</option>
            </select>
          </div>
          <div class="sm:col-span-2">
            <label class="font-bold text-slate-700 block mb-1">Descrição do Material por Amostra (separe múltiplos frascos por | ):</label>
            <input v-model="formSUS.descricao_material" type="text" placeholder="Ex: Biópsia de Próstata Base Direita | Biópsia Base Esquerda" class="w-full border rounded-lg px-3 py-2" />
          </div>
          <div class="sm:col-span-2">
            <label class="font-bold text-slate-700 block mb-1">Informações Clínicas / Hipótese Diagnóstica:</label>
            <textarea v-model="formSUS.informacoes_clinicas" rows="2" placeholder="Resumo clínico da guia SIA/SUS..." class="w-full border rounded-lg px-3 py-2"></textarea>
          </div>
        </div>

        <button
          @click="confirmarRecebimentoSUS"
          class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl text-sm shadow transition">
          ✅ Cadastrar Paciente SUS, Receber Amostra e Imprimir Etiqueta
        </button>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- ABA 3: RELAÇÃO DE AMOSTRAS REJEITADAS / DEVOLVIDAS                      -->
    <!-- ======================================================================= -->
    <div v-if="abaAtiva === 'REJEICOES'" class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4">
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-lg font-bold text-slate-800">Relação de Amostras Rejeitadas e Devoluções ao Setor</h2>
          <p class="text-xs text-slate-500">
            Quando uma amostra rejeitada retorna corrigida e é recebida, ela sai das pendências ativas (status Superada), mas permanece registrada no histórico do caso.
          </p>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="bg-slate-100 text-slate-700 uppercase">
              <th class="p-3">Data / Hora</th>
              <th class="p-3">Solicitação / Amostra</th>
              <th class="p-3">Paciente / Prontuário</th>
              <th class="p-3">Tipo / Motivo da Não Conformidade</th>
              <th class="p-3">Responsável</th>
              <th class="p-3">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200">
            <tr v-for="rej in listaRejeicoes" :key="rej.id">
              <td class="p-3 font-mono">{{ rej.data_rejeicao }}</td>
              <td class="p-3 font-bold text-blue-900">#{{ rej.codigo_solicitacao }} (Amostra: {{ rej.numero_amostra }})</td>
              <td class="p-3">{{ rej.nome_paciente }} (Pront: {{ rej.prontuario }})</td>
              <td class="p-3">
                <span class="font-semibold text-rose-800">{{ rej.tipo_inconformidade }}: {{ rej.motivo_padrao }}</span>
                <span v-if="rej.detalhe_outros" class="block text-slate-600">Obs: {{ rej.detalhe_outros }}</span>
              </td>
              <td class="p-3">{{ rej.responsavel }}</td>
              <td class="p-3">
                <span
                  class="px-2 py-0.5 rounded font-bold"
                  :class="rej.superada ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'"
                >
                  {{ rej.superada ? `Superada (${rej.data_superacao})` : 'Devolvida / Aguardando Retorno' }}
                </span>
              </td>
            </tr>
            <tr v-if="!listaRejeicoes.length">
              <td colspan="6" class="p-6 text-center text-slate-400">Nenhuma rejeição registrada até o momento.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- MODAL: REGISTRAR NÃO CONFORMIDADE / REJEIÇÃO (LISTA FECHADA + OUTROS) -->
    <div v-if="modalRejeicaoAberto && solicitacaoEncontrada" class="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 text-xs">
        <div class="flex justify-between items-center border-b pb-3">
          <h3 class="text-base font-extrabold text-rose-800">
            🚫 Registrar Não Conformidade / Rejeição (#{{ solicitacaoEncontrada.codigo_solicitacao }})
          </h3>
          <button @click="modalRejeicaoAberto = false" class="text-slate-400 hover:text-slate-700 text-lg font-bold">✕</button>
        </div>

        <div class="space-y-3">
          <div>
            <label class="font-bold text-slate-700 block mb-1">Tipo de Erro (Solicitação vs Frasco Físico):</label>
            <select v-model="formRejeicao.tipo_inconformidade" class="w-full border rounded-lg px-3 py-2 bg-white">
              <option value="Frasco / Material Físico">Erro no Frasco / Material Físico (Pode retornar com a mesma solicitação)</option>
              <option value="Solicitação AGHU">Erro na Solicitação AGHU (Exige nova solicitação)</option>
            </select>
          </div>

          <div>
            <label class="font-bold text-slate-700 block mb-1">Motivo Padronizado (Para Relatórios Gerenciais):</label>
            <select v-model="formRejeicao.motivo_padrao" class="w-full border rounded-lg px-3 py-2 bg-white">
              <option v-for="m in motivosRejeicao" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>

          <!-- Campo de texto livre exibido APENAS quando seleciona "Outros" (Reunião pág. 9) -->
          <div v-if="formRejeicao.motivo_padrao === 'Outros'">
            <label class="font-bold text-rose-800 block mb-1">Descreva o Motivo Específico (Obrigatório para 'Outros'):</label>
            <textarea
              v-model="formRejeicao.detalhe_outros"
              rows="2"
              placeholder="Descreva detalhadamente a não conformidade..."
              class="w-full border border-rose-300 rounded-lg px-3 py-2"
            ></textarea>
          </div>

          <div>
            <label class="font-bold text-slate-700 block mb-1">Setor de Devolução / Contínuo:</label>
            <input v-model="formRejeicao.setor_devolucao" type="text" class="w-full border rounded-lg px-3 py-2" />
          </div>
        </div>

        <div class="flex justify-end gap-2 pt-3 border-t">
          <button @click="modalRejeicaoAberto = false" class="px-4 py-2 rounded-lg bg-slate-200 text-slate-700 font-semibold">
            Cancelar
          </button>
          <button @click="salvarRejeicao" class="px-5 py-2 rounded-lg bg-rose-700 hover:bg-rose-800 text-white font-bold">
            Confirmar Rejeição e Devolução
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL: VISUALIZAÇÃO DE ETIQUETA ZPL INDIVIDUAL -->
    <div v-if="etiquetaSelecionadaZPL" class="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 text-xs">
        <div class="flex justify-between items-center border-b pb-2">
          <h3 class="text-base font-bold text-slate-800">🖨️ Etiqueta Térmica Zebra/Argox (Frasco #{{ etiquetaSelecionadaZPL.numero_amostra }})</h3>
          <button @click="etiquetaSelecionadaZPL = null" class="text-lg font-bold text-slate-400">✕</button>
        </div>
        <div class="p-4 bg-slate-100 rounded-xl border-2 border-dashed border-slate-400 space-y-1">
          <p class="text-sm font-extrabold font-mono text-blue-900">{{ exameRecemGerado?.codigo_sap }} — Frasco #{{ etiquetaSelecionadaZPL.numero_amostra }}</p>
          <p class="font-bold text-slate-900">Paciente: {{ etiquetaSelecionadaZPL.nome_paciente }}</p>
          <p class="text-slate-700">{{ etiquetaSelecionadaZPL.segundo_identificador }}</p>
          <p class="font-semibold text-emerald-900">Material: {{ etiquetaSelecionadaZPL.descricao_material }}</p>
          <p class="font-mono text-[11px] text-slate-600">QR Code: {{ etiquetaSelecionadaZPL.qr_code }} | AGHU #{{ exameRecemGerado?.codigo_solicitacao }}</p>
        </div>
        <div>
          <span class="font-bold text-slate-600 block mb-1">Comando Nativo ZPL II enviado para a Impressora da Triagem:</span>
          <pre class="bg-slate-900 text-emerald-400 p-3 rounded-lg font-mono text-[11px] overflow-x-auto">{{ etiquetaSelecionadaZPL.zpl }}</pre>
        </div>
        <div class="flex justify-end gap-2">
          <button @click="imprimirJanela" class="bg-blue-700 text-white px-4 py-2 rounded-lg font-bold">🖨️ Enviar para Impressora</button>
          <button @click="etiquetaSelecionadaZPL = null" class="bg-slate-200 text-slate-800 px-4 py-2 rounded-lg font-semibold">Fechar</button>
        </div>
      </div>
    </div>

    <!-- MODAL: FICHA DE TRABALHO ÚNICA DA RECEPÇÃO (Reunião págs. 20-22) -->
    <div v-if="modalFichaAberta && exameRecemGerado?.ficha_trabalho" class="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 text-xs max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-center border-b pb-3">
          <div>
            <h3 class="text-base font-extrabold text-blue-900">{{ exameRecemGerado.ficha_trabalho.titulo }}</h3>
            <p class="text-[11px] text-slate-500">Impressa exclusivamente na Recepção — acompanha os frascos com a descrição individual de cada amostra</p>
          </div>
          <button @click="modalFichaAberta = false" class="text-lg font-bold text-slate-400">✕</button>
        </div>

        <div class="grid grid-cols-2 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-300">
          <p><strong>Código SAP:</strong> <span class="font-mono text-sm font-extrabold text-blue-900">{{ exameRecemGerado.ficha_trabalho.codigo_sap }}</span></p>
          <p><strong>Solicitação AGHU:</strong> #{{ exameRecemGerado.ficha_trabalho.codigo_solicitacao }}</p>
          <p><strong>Paciente:</strong> {{ exameRecemGerado.ficha_trabalho.nome_paciente }}</p>
          <p><strong>Prontuário / Nasc:</strong> {{ exameRecemGerado.ficha_trabalho.prontuario }} ({{ exameRecemGerado.ficha_trabalho.data_nascimento }})</p>
          <p><strong>Origem / Especialidade:</strong> {{ exameRecemGerado.ficha_trabalho.origem_unidade }} ({{ exameRecemGerado.ficha_trabalho.especialidade }})</p>
          <p><strong>Recebido em:</strong> {{ exameRecemGerado.ficha_trabalho.data_recebimento }} por {{ exameRecemGerado.ficha_trabalho.responsavel_recepcao }}</p>
        </div>

        <div>
          <strong class="block text-slate-700 mb-1">Informações Clínicas:</strong>
          <p class="p-3 bg-slate-50 rounded border border-slate-200">{{ exameRecemGerado.ficha_trabalho.informacoes_clinicas }}</p>
        </div>

        <div>
          <strong class="block text-slate-700 mb-2">Relação Numerada de Amostras e Descrição do Material (Para Conferência na Macroscopia):</strong>
          <table class="w-full border-collapse border border-slate-300 text-xs">
            <thead>
              <tr class="bg-slate-100">
                <th class="border border-slate-300 p-2">Amostra #</th>
                <th class="border border-slate-300 p-2">QR Code do Frasco</th>
                <th class="border border-slate-300 p-2">Descrição do Material Anatômico</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="am in exameRecemGerado.ficha_trabalho.amostras" :key="am.qr_code">
                <td class="border border-slate-300 p-2 font-bold">Amostra {{ String(am.numero_amostra).padStart(3, '0') }}</td>
                <td class="border border-slate-300 p-2 font-mono">{{ am.qr_code }}</td>
                <td class="border border-slate-300 p-2 font-semibold">{{ am.descricao_material }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button @click="imprimirJanela" class="bg-blue-700 text-white px-4 py-2 rounded-lg font-bold">🖨️ Imprimir Ficha</button>
          <button @click="modalFichaAberta = false" class="bg-slate-200 text-slate-800 px-4 py-2 rounded-lg font-semibold">Fechar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const abaAtiva = ref<'HC' | 'SUS' | 'REJEICOES'>('HC')
const perfilAtivo = ref<string>('Recepcionista')
const inputCodigoSolicitacao = ref<string>('')
const solicitacaoEncontrada = ref<any>(null)
const amostrasMarcadas = ref<string[]>([])
const descricoesEditadas = ref<Record<string, string>>({})
const prefixoFiltroSelecionado = ref<string>('')
const estagioEntrada = ref<string>('Peça a Fresco / Formol (Para Macroscopia)')
const observacaoRecepcao = ref<string>('')
const flagNeoplasia = ref<boolean>(false)
const flagUrgente = ref<boolean>(false)
const motivoUrgencia = ref<string>('')
const erroRecebimento = ref<string>('')
const exameRecemGerado = ref<any>(null)

const motivosRejeicao = ref<string[]>([])
const listaRejeicoes = ref<any[]>([])
const modalRejeicaoAberto = ref(false)
const etiquetaSelecionadaZPL = ref<any>(null)
const modalFichaAberta = ref(false)

const formRejeicao = ref({
  tipo_inconformidade: 'Frasco / Material Físico',
  motivo_padrao: 'Quantidade de frascos divergente da solicitação',
  detalhe_outros: '',
  setor_devolucao: 'Contínuo / Setor Solicitante'
})

const formSUS = ref({
  cpf: '',
  cns: '',
  nome: '',
  data_nascimento: '',
  municipio_origem: 'Secretaria Municipal de Saúde (SUS)',
  prefixo_exame: 'HP',
  estagio_entrada: 'Peça a Fresco / Formol (Para Macroscopia)',
  descricao_material: '',
  informacoes_clinicas: ''
})

const testarCodigo = (codigo: string) => {
  inputCodigoSolicitacao.value = codigo
  consultarSolicitacaoCSV()
}

const consultarSolicitacaoCSV = async () => {
  erroRecebimento.value = ''
  exameRecemGerado.value = null
  solicitacaoEncontrada.value = null
  amostrasMarcadas.value = []
  descricoesEditadas.value = {}
  prefixoFiltroSelecionado.value = ''

  if (!inputCodigoSolicitacao.value.trim()) {
    erroRecebimento.value = 'Digite ou bipe um número de solicitação válido.'
    return
  }

  try {
    const res = await api.get(`/api/sap/solicitacao/${encodeURIComponent(inputCodigoSolicitacao.value.trim())}`)
    const data = res.data
    solicitacaoEncontrada.value = data
    flagNeoplasia.value = data.suspeita_neoplasia_sugerida
    flagUrgente.value = data.urgente_sugerido
    motivoUrgencia.value = data.urgente_sugerido ? 'Congelação Intraoperatória' : ''

    for (const am of data.amostras) {
      descricoesEditadas.value[am.numero_amostra] = am.descricao_material
    }

    // Se bipou código de 10 dígitos focado em uma amostra específica, seleciona ela; senão, seleciona pendentes do 1º grupo
    if (data.amostra_bipada_foco) {
      amostrasMarcadas.value = [String(data.amostra_bipada_foco)]
    } else if (data.grupos_exame && data.grupos_exame.length) {
      const primeiroGrupoPendente = data.grupos_exame.find((g: any) => !g.ja_recebido) || data.grupos_exame[0]
      selecionarGrupoExame(primeiroGrupoPendente)
    }
  } catch (err: any) {
    erroRecebimento.value = err.response?.data?.detail || 'Erro ao consultar solicitação no AGHU.'
  }
}

const selecionarGrupoExame = (grupo: any) => {
  prefixoFiltroSelecionado.value = grupo.prefixo_sap
  flagUrgente.value = grupo.urgente_padrao
  if (solicitacaoEncontrada.value) {
    amostrasMarcadas.value = solicitacaoEncontrada.value.amostras
      .filter((a: any) => a.prefixo_sap === grupo.prefixo_sap && !a.ja_recebida)
      .map((a: any) => String(a.numero_amostra))
  }
}

const marcarTodasAmostras = () => {
  if (solicitacaoEncontrada.value) {
    prefixoFiltroSelecionado.value = ''
    amostrasMarcadas.value = solicitacaoEncontrada.value.amostras
      .filter((a: any) => !a.ja_recebida)
      .map((a: any) => String(a.numero_amostra))
  }
}

const confirmarRecebimentoHC = async () => {
  erroRecebimento.value = ''
  exameRecemGerado.value = null
  if (!solicitacaoEncontrada.value) return

  try {
    const payload = {
      origem_peca: 'HC',
      codigo_solicitacao: solicitacaoEncontrada.value.codigo_solicitacao,
      amostras_conferidas: amostrasMarcadas.value.map(String),
      descricoes_amostras: descricoesEditadas.value,
      prefixo_exame: prefixoFiltroSelecionado.value || undefined,
      estagio_entrada: estagioEntrada.value,
      urgente: flagUrgente.value,
      motivo_urgencia: motivoUrgencia.value || undefined,
      suspeita_neoplasia: flagNeoplasia.value,
      observacao_recepcao: observacaoRecepcao.value,
      perfil_usuario: perfilAtivo.value,
      operador: 'recepcionista.hc'
    }
    const res = await api.post('/api/sap/receber', payload)
    exameRecemGerado.value = res.data.exame
    await consultarSolicitacaoCSV()
    exameRecemGerado.value = res.data.exame
  } catch (err: any) {
    erroRecebimento.value = err.response?.data?.detail || 'Falha ao registrar o recebimento da amostra.'
  }
}

const confirmarRecebimentoSUS = async () => {
  erroRecebimento.value = ''
  exameRecemGerado.value = null
  try {
    const partes = (formSUS.value.descricao_material || 'Peça Externa SUS')
      .split('|')
      .map(s => s.trim())
      .filter(Boolean)
    const amostras_sus = partes.map((desc, i) => ({
      numero_amostra: String(i + 1),
      descricao_material: desc
    }))

    const res = await api.post('/api/sap/receber', {
      origem_peca: 'SUS',
      prefixo_exame: formSUS.value.prefixo_exame,
      estagio_entrada: formSUS.value.estagio_entrada,
      informacoes_clinicas: formSUS.value.informacoes_clinicas,
      paciente_sus: {
        cpf: formSUS.value.cpf,
        cns: formSUS.value.cns,
        nome: formSUS.value.nome,
        data_nascimento: formSUS.value.data_nascimento,
        municipio_origem: formSUS.value.municipio_origem
      },
      amostras_sus,
      perfil_usuario: perfilAtivo.value,
      operador: 'recepcionista.sus'
    })
    exameRecemGerado.value = res.data.exame
  } catch (err: any) {
    erroRecebimento.value = err.response?.data?.detail || 'Erro ao registrar recebimento externo SUS.'
  }
}

const salvarRejeicao = async () => {
  if (!solicitacaoEncontrada.value) return
  erroRecebimento.value = ''
  try {
    await api.post('/api/sap/rejeicoes', {
      codigo_solicitacao: solicitacaoEncontrada.value.codigo_solicitacao,
      numero_amostra: amostrasMarcadas.value.join(', ') || 'Todas',
      nome_paciente: solicitacaoEncontrada.value.nome_paciente,
      prontuario: solicitacaoEncontrada.value.prontuario,
      origem_unidade: `${solicitacaoEncontrada.value.origem} - ${solicitacaoEncontrada.value.unidade}`,
      tipo_inconformidade: formRejeicao.value.tipo_inconformidade,
      motivo_padrao: formRejeicao.value.motivo_padrao,
      detalhe_outros: formRejeicao.value.detalhe_outros,
      setor_devolucao: formRejeicao.value.setor_devolucao,
      operador: 'recepcionista.hc'
    })
    modalRejeicaoAberto.value = false
    await consultarSolicitacaoCSV()
    await carregarRejeicoes()
  } catch (err: any) {
    erroRecebimento.value = err.response?.data?.detail || 'Erro ao registrar rejeição.'
  }
}

const carregarRejeicoes = async () => {
  try {
    const res = await api.get('/api/sap/rejeicoes')
    listaRejeicoes.value = res.data.rejeicoes
  } catch {
    // ignore
  }
}

const imprimirJanela = () => {
  window.print()
}

onMounted(async () => {
  try {
    const resMot = await api.get('/api/sap/motivos-rejeicao')
    motivosRejeicao.value = resMot.data.motivos
  } catch {
    motivosRejeicao.value = ['Quantidade de frascos divergente da solicitação', 'Amostra sem formol / fixador inadequado', 'Outros']
  }
  await carregarRejeicoes()
  if (route.query.solicitacao) {
    inputCodigoSolicitacao.value = String(route.query.solicitacao)
    await consultarSolicitacaoCSV()
  }
})
</script>
