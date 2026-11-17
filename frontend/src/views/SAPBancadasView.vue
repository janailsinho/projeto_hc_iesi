<template>
  <div class="min-h-screen bg-slate-50 p-6 space-y-6">
    <!-- Cabeçalho Operacional das Bancadas -->
    <header class="flex flex-col justify-between gap-4 lg:flex-row lg:items-center bg-white p-5 rounded-xl shadow-sm border border-slate-200">
      <div>
        <h1 class="text-2xl md:text-3xl font-extrabold text-blue-900 tracking-tight">
          Bancadas Laboratoriais e Diagnósticas (SAP)
        </h1>
        <p class="text-sm text-slate-600 mt-1">
          Macroscopia (RF013–RF018) • Processamento Técnico (RF019–RF032) • Microscopia, Laudo Prévio & Revisão (RF033–RF039)
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <!-- Simulador RBAC (RF002) -->
        <div class="bg-slate-100 px-3 py-2 rounded-lg border border-slate-300 flex items-center gap-2">
          <span class="text-xs font-bold uppercase text-slate-500">Perfil Logado:</span>
          <select v-model="perfilAtivo" class="bg-transparent text-xs font-bold text-blue-900 focus:outline-none cursor-pointer">
            <option value="Macroscopista">Macroscopista</option>
            <option value="Técnico de Laboratório">Técnico de Laboratório</option>
            <option value="Residente">Residente (Laudo Prévio)</option>
            <option value="Médico Patologista">Médico Patologista (Revisão / Liberação)</option>
          </select>
        </div>

        <input
          v-model="operadorLogado"
          type="text"
          placeholder="Operador (ex: dr.carlos)"
          class="border border-slate-300 rounded-lg px-3 py-1.5 text-xs bg-white w-40 font-semibold"
        />
      </div>
    </header>

    <!-- Abas das 3 Etapas Laboratoriais -->
    <div class="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
      <button
        @click="abaSetor = 'MACRO'"
        :class="abaSetor === 'MACRO' ? 'bg-blue-800 text-white shadow' : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-300'"
        class="px-4 py-2.5 rounded-xl font-bold text-xs transition">
        🔪 1.3 Macroscopia (Frascos → Cassetes 1:N)
      </button>
      <button
        @click="abaSetor = 'PROC'"
        :class="abaSetor === 'PROC' ? 'bg-indigo-700 text-white shadow' : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-300'"
        class="px-4 py-2.5 rounded-xl font-bold text-xs transition">
        🧪 1.4 Processamento Técnico (Cassetes → Blocos → Corte → Lâminas)
      </button>
      <button
        @click="abaSetor = 'MICRO'"
        :class="abaSetor === 'MICRO' ? 'bg-purple-800 text-white shadow' : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-300'"
        class="px-4 py-2.5 rounded-xl font-bold text-xs transition">
        🔬 1.5 Microscopia (Laudo Prévio, Revisão, IHQ & Liberação)
      </button>
    </div>

    <!-- Barra Universal de Bipagem QR Code / Código de Barras + Seleção da Fila Ativa -->
    <div class="bg-white p-5 rounded-xl shadow-sm border border-slate-200 grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2">
        <label class="block text-xs font-bold uppercase text-slate-700 mb-1.5">
          Bipar QR Code do Subproduto (Frasco, Cassete, Bloco ou Lâmina) ou Digitar Código SAP / Solicitação:
        </label>
        <div class="flex gap-2">
          <input
            v-model="codigoBipado"
            @keyup.enter="identificarSubproduto"
            type="text"
            placeholder="Bipe aqui com o leitor HID (ex: HP-2026-001, HP-2026-001-F1, CAS-..., LAM-...) ou clique em um exame ao lado"
            class="flex-1 border border-slate-300 rounded-lg px-3.5 py-2 text-sm focus:ring-2 focus:ring-blue-600 focus:outline-none"
          />
          <button
            @click="identificarSubproduto"
            class="bg-blue-700 hover:bg-blue-800 text-white font-bold px-5 py-2 rounded-lg text-xs shadow transition">
            📡 Identificar na Bancada
          </button>
        </div>
      </div>

      <div>
        <label class="block text-xs font-bold uppercase text-slate-700 mb-1.5">
          Exames Recebidos no SISPATO ({{ filaRecebidos.length }}):
        </label>
        <select
          @change="(e: any) => selecionarExameDaFila(e.target.value)"
          class="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs bg-white font-semibold"
        >
          <option value="">-- Selecionar exame recebido para abrir na bancada --</option>
          <option v-for="ex in filaRecebidos" :key="ex.codigo_sap" :value="ex.codigo_sap">
            {{ ex.codigo_sap }} (#{{ ex.codigo_solicitacao }}) — {{ ex.nome_paciente }} [{{ ex.etapa_atual }}]
          </option>
        </select>
      </div>
    </div>

    <!-- Mensagens de Feedback -->
    <div v-if="mensagemSucesso" class="p-4 bg-emerald-100 border-l-4 border-emerald-600 text-emerald-900 text-xs font-semibold rounded-lg">
      ✅ {{ mensagemSucesso }}
    </div>
    <div v-if="mensagemErro" class="p-4 bg-rose-100 border-l-4 border-rose-600 text-rose-900 text-xs font-semibold rounded-lg">
      ⚠️ {{ mensagemErro }}
    </div>

    <!-- Estado Vazio -->
    <div v-if="!exameAtivo" class="bg-white p-10 rounded-xl border border-slate-200 text-center space-y-2">
      <p class="text-base font-bold text-slate-700">Nenhum exame selecionado na bancada</p>
      <p class="text-xs text-slate-500">
        Bipe o QR Code do frasco/cassete/lâmina acima ou selecione um dos exames recebidos na caixa de seleção.
      </p>
    </div>

    <!-- ======================================================================= -->
    <!-- PAINEL DE TRABALHO DO EXAME IDENTIFICADO                                -->
    <!-- ======================================================================= -->
    <div v-if="exameAtivo" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Coluna Esquerda (1/3): Resumo Clínico + Árvore Hierárquica em Tempo Real -->
      <div class="bg-white p-5 rounded-xl shadow-sm border border-slate-200 space-y-4 text-xs">
        <div class="border-b pb-3">
          <div class="flex justify-between items-center">
            <span class="font-mono text-lg font-extrabold text-blue-900">{{ exameAtivo.codigo_sap }}</span>
            <span class="px-2.5 py-0.5 bg-blue-100 text-blue-800 rounded-full font-bold text-[11px]">
              {{ exameAtivo.etapa_atual }}
            </span>
          </div>
          <p class="font-bold text-slate-800 mt-1">{{ exameAtivo.nome_paciente }} (Pront: {{ exameAtivo.prontuario_paciente || 'SUS' }})</p>
          <p class="text-slate-500">Solicitação AGHU: #{{ exameAtivo.codigo_solicitacao }} • {{ exameAtivo.tipo_exame }}</p>
        </div>

        <div>
          <strong class="text-slate-500 uppercase block mb-1">Informações Clínicas (AGHU):</strong>
          <p class="p-2.5 bg-slate-50 rounded border border-slate-200 text-slate-700">
            {{ exameAtivo.informacoes_clinicas || 'Sem informações clínicas adicionais.' }}
          </p>
        </div>

        <!-- Árvore Hierárquica com Impressão de Etiquetas ZPL -->
        <div>
          <strong class="text-slate-700 uppercase block mb-2">
            🌳 Árvore de Subprodutos ({{ exameAtivo.quantidade_amostras }}F / {{ exameAtivo.quantidade_cassetes }}C / {{ exameAtivo.quantidade_blocos }}B / {{ exameAtivo.quantidade_laminas }}L):
          </strong>
          <div class="space-y-2.5 max-h-96 overflow-y-auto pr-1">
            <div v-for="f in exameAtivo.arvore_subprodutos" :key="f.qr_code" class="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
              <div class="flex justify-between items-center font-bold text-slate-900">
                <span>🧪 F#{{ f.numero_amostra }}: {{ f.descricao_material }}</span>
                <button @click="etiquetaModal = { titulo: `Frasco #${f.numero_amostra}`, qr: f.qr_code, zpl: f.zpl }" class="text-[10px] bg-slate-800 text-white px-2 py-0.5 rounded">
                  ZPL
                </button>
              </div>
              <div v-for="c in f.cassetes" :key="c.qr_code" class="mt-1.5 pl-3 border-l-2 border-blue-400 space-y-1">
                <div class="flex justify-between items-center text-indigo-900 font-semibold">
                  <span>🗂️ {{ c.codigo_cassete }} ({{ c.status_cassete }})</span>
                  <button @click="etiquetaModal = { titulo: c.codigo_cassete, qr: c.qr_code, zpl: c.zpl }" class="text-[10px] bg-indigo-700 text-white px-2 py-0.5 rounded">
                    ZPL
                  </button>
                </div>
                <div v-for="b in c.blocos" :key="b.qr_code" class="pl-3 border-l-2 border-amber-400 space-y-1">
                  <div class="text-amber-900 font-semibold">
                    🧊 {{ b.codigo_bloco }} {{ b.arquivado ? `[Arq: ${b.local_arquivo}]` : '' }}
                  </div>
                  <div v-for="l in b.laminas" :key="l.qr_code" class="pl-3 border-l-2 border-emerald-500 flex justify-between items-center text-emerald-900">
                    <span>🔬 {{ l.codigo_lamina }} ({{ l.tipo_coloracao }})</span>
                    <button @click="etiquetaModal = { titulo: l.codigo_lamina, qr: l.qr_code, zpl: l.zpl }" class="text-[10px] bg-emerald-700 text-white px-2 py-0.5 rounded">
                      ZPL
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Coluna Direita (2/3): Operações da Bancada Selecionada -->
      <div class="lg:col-span-2 space-y-6">
        <!-- =============================================================== -->
        <!-- BANCADA 1.3: MACROSCOPIA (RF013 a RF018)                        -->
        <!-- =============================================================== -->
        <div v-if="abaSetor === 'MACRO'" class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-5 text-xs">
          <div class="border-b pb-3 flex justify-between items-center">
            <div>
              <h2 class="text-base font-extrabold text-blue-900">1.3 Bancada de Macroscopia (RF013 a RF018)</h2>
              <p class="text-slate-500">Registro exclusivo da descrição macroscópica, geração de N cassetes (1:N) com etiquetas QR Code e envio para Processamento</p>
            </div>
          </div>

          <div class="space-y-4">
            <div>
              <label class="font-bold text-slate-700 block mb-1">1. Selecionar Frasco Identificado na Macroscopia (RF013):</label>
              <select v-model="formMacro.frasco_id" class="w-full border border-slate-300 rounded-lg px-3 py-2 bg-white font-semibold">
                <option v-for="f in exameAtivo.arvore_subprodutos" :key="f.id" :value="f.id">
                  Frasco #{{ f.numero_amostra }} — {{ f.descricao_material }} (QR: {{ f.qr_code }})
                </option>
              </select>
            </div>

            <div>
              <label class="font-bold text-slate-700 block mb-1">2. Descrição Macroscópica da Peça (Mantida exclusivamente no SISPATO — RF014):</label>
              <textarea
                v-model="formMacro.descricao_macroscopica"
                rows="4"
                placeholder="Descreva dimensões, peso, coloração, consistência, margens cirúrgicas e clivagem dos fragmentos..."
                class="w-full border border-slate-300 rounded-lg p-3"
              ></textarea>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="font-bold text-slate-700 block mb-1">3. Quantidade de Cassetes Gerados (Relação 1:N — RF015):</label>
                <input v-model.number="formMacro.quantidade_cassetes" type="number" min="1" max="26" class="w-full border border-slate-300 rounded-lg px-3 py-2" />
              </div>
              <div>
                <label class="font-bold text-slate-700 block mb-1">Identificação Topográfica dos Fragmentos:</label>
                <input v-model="formMacro.descricao_fragmentos" type="text" placeholder="Ex: Margem proximal, lesão central, base direita..." class="w-full border border-slate-300 rounded-lg px-3 py-2" />
              </div>
            </div>

            <div class="flex flex-wrap gap-3 pt-2">
              <button
                @click="salvarMacroscopiaGerarCassetes"
                class="bg-blue-700 hover:bg-blue-800 text-white font-bold px-5 py-2.5 rounded-xl shadow transition">
                🗂️ 1. Salvar Macroscopia e Gerar Cassetes + Etiquetas QR (RF014–RF016)
              </button>

              <button
                @click="confirmarEnviarCassetesProcessamento"
                :disabled="!exameAtivo.quantidade_cassetes"
                class="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-5 py-2.5 rounded-xl shadow transition disabled:opacity-50">
                ✅ 2. Confirmar Identidade dos Cassetes e Enviar ao Processamento Técnico (RF017–RF018)
              </button>
            </div>
          </div>
        </div>

        <!-- =============================================================== -->
        <!-- BANCADA 1.4: PROCESSAMENTO TÉCNICO (RF019 a RF032)              -->
        <!-- =============================================================== -->
        <div v-if="abaSetor === 'PROC'" class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-5 text-xs">
          <div class="border-b pb-3">
            <h2 class="text-base font-extrabold text-indigo-900">1.4 Bancada de Processamento Técnico (RF019 a RF032)</h2>
            <p class="text-slate-500">
              Processamento de tecidos, inclusão em blocos de parafina (1:N), microtomia/corte, geração de lâminas (1:N), coloração/montagem, envio para Microscopia e arquivamento de blocos
            </p>
          </div>

          <!-- Alerta de Pedidos de IHQ / Complementos vindos da Microscopia (RF032) -->
          <div v-if="exameAtivo.complementos && exameAtivo.complementos.length" class="p-4 bg-amber-50 border-l-4 border-amber-500 rounded-lg space-y-1.5">
            <p class="font-bold text-amber-900">🔔 Pedidos de Imuno-histoquímica / Complementos Originados na Microscopia (RF032):</p>
            <div v-for="comp in exameAtivo.complementos" :key="comp.id" class="text-amber-950 border-t border-amber-200 pt-1">
              <strong>{{ comp.tipo_pedido }}</strong> (Marcadores: {{ comp.marcadores || 'N/A' }}) — {{ comp.justificativa }}
              • Status: <span class="font-bold">{{ comp.status_pedido }}</span>
            </div>
          </div>

          <!-- Passo 1 e 2: Processamento de Tecidos e Inclusão em Blocos -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
              <h3 class="font-bold text-slate-800">Etapa A: Processamento de Tecidos (RF019, RF020)</h3>
              <p class="text-slate-500">Identifica os {{ exameAtivo.quantidade_cassetes }} cassete(s) e registra início do histotécnico.</p>
              <button
                @click="executarProcessamento('INICIAR_PROCESSAMENTO')"
                class="w-full bg-indigo-700 hover:bg-indigo-800 text-white font-bold py-2 rounded-lg transition">
                1. Confirmar Cassetes e Iniciar Processamento
              </button>
            </div>

            <div class="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
              <h3 class="font-bold text-slate-800">Etapa B: Inclusão em Parafina (RF021, RF022)</h3>
              <div class="flex items-center gap-2">
                <label class="font-semibold">Blocos por cassete (1:N):</label>
                <input v-model.number="formProc.quantidade_blocos" type="number" min="1" max="10" class="border rounded px-2 py-1 w-20 bg-white" />
              </div>
              <button
                @click="executarProcessamento('GERAR_BLOCOS')"
                class="w-full bg-amber-600 hover:bg-amber-700 text-white font-bold py-2 rounded-lg transition">
                🧊 2. Registrar Inclusão e Gerar Blocos de Parafina
              </button>
            </div>
          </div>

          <!-- Passo 3: Corte (Microtomia) e Geração de Lâminas -->
          <div class="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
            <h3 class="font-bold text-slate-800">Etapa C: Microtomia / Corte e Geração de Lâminas Vinculadas ao Bloco (RF023, RF024, RF027)</h3>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label class="font-semibold block mb-1">Nº de Lâminas por Bloco (1:N):</label>
                <input v-model.number="formProc.quantidade_laminas" type="number" min="1" max="20" class="w-full border rounded px-3 py-1.5 bg-white" />
              </div>
              <div>
                <label class="font-semibold block mb-1">Coloração / Técnica:</label>
                <select v-model="formProc.tipo_coloracao" class="w-full border rounded px-3 py-1.5 bg-white">
                  <option value="H&E (Hematoxilina-Eosina)">H&E (Hematoxilina-Eosina)</option>
                  <option value="Papanicolaou (Citologia)">Papanicolaou (Citologia)</option>
                  <option value="PAS / Ziehl-Neelsen / Giemsa">Coloração Especial (PAS / Ziehl / Giemsa)</option>
                  <option value="Imuno-histoquímica (IHQ)">Imuno-histoquímica (IHQ)</option>
                </select>
              </div>
              <div>
                <label class="font-semibold block mb-1">Marcador IHQ (Opcional):</label>
                <input v-model="formProc.marcador_ihq" type="text" placeholder="Ex: Ki-67, RE, RP, HER2..." class="w-full border rounded px-3 py-1.5 bg-white" />
              </div>
            </div>
            <button
              @click="executarProcessamento('CORTE_GERAR_LAMINAS')"
              class="bg-blue-700 hover:bg-blue-800 text-white font-bold px-5 py-2 rounded-lg transition">
              🔪 3. Registrar Corte e Gerar Lâminas + Etiquetas QR Code
            </button>
          </div>

          <!-- Passo 4, 5 e 6: Coloração, Envio para Microscopia e Arquivamento de Blocos -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button
              @click="executarProcessamento('COLORACAO_E_LIBERACAO')"
              class="bg-purple-700 hover:bg-purple-800 text-white font-bold p-3 rounded-xl transition">
              🎨 4. Registrar Coloração, Montagem e Liberação Técnica (RF025, RF026)
            </button>

            <button
              @click="executarProcessamento('ENVIAR_MICROSCOPIA')"
              class="bg-emerald-600 hover:bg-emerald-700 text-white font-bold p-3 rounded-xl transition">
              🔬 5. Confirmar Identidade das Lâminas e Enviar à Microscopia (RF028, RF030)
            </button>

            <button
              @click="executarProcessamento('ARQUIVAR_BLOCOS')"
              class="bg-slate-800 hover:bg-slate-900 text-white font-bold p-3 rounded-xl transition">
              🗄️ 6. Confirmar Identidade e Arquivar Blocos de Parafina (RF029, RF031)
            </button>
          </div>
        </div>

        <!-- =============================================================== -->
        <!-- BANCADA 1.5: MICROSCOPIA E LAUDOS (RF033 a RF039 + RNF009)      -->
        <!-- =============================================================== -->
        <div v-if="abaSetor === 'MICRO'" class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-5 text-xs">
          <div class="border-b pb-3 flex flex-wrap justify-between items-center gap-2">
            <div>
              <h2 class="text-base font-extrabold text-purple-900">1.5 Microscopia, Laudo Prévio, Revisão e Liberação (RF033 a RF039)</h2>
              <p class="text-slate-500">
                Laudo prévio do residente mantido no sistema; laudo definitivo pertence ao AGHU (RNF004, RNF012)
              </p>
            </div>
            <button
              @click="executarMicroscopia('IDENTIFICAR_LAMINA')"
              class="bg-purple-100 hover:bg-purple-200 text-purple-900 font-bold px-3 py-1.5 rounded-lg border border-purple-300">
              🔍 Confirmar Identificação da Lâmina no Microscópio (RF033)
            </button>
          </div>

          <!-- Bloco do Residente: Elaboração de Laudo Prévio (RF034) -->
          <div class="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
            <h3 class="font-bold text-slate-800">1. Elaboração de Laudo Prévio pelo Residente (RF034 — Exclusivo no Sistema)</h3>
            <div class="grid grid-cols-1 gap-3">
              <div>
                <label class="font-semibold block mb-1">Diagnóstico / Conclusão Principal (Para indexação no Acervo — RF048):</label>
                <input
                  v-model="formMicro.diagnostico_associado"
                  type="text"
                  placeholder="Ex: Adenocarcinoma invasivo moderadamente diferenciado..."
                  class="w-full border rounded-lg px-3 py-2 bg-white"
                />
              </div>
              <div>
                <label class="font-semibold block mb-1">Texto do Laudo Prévio Microscópico:</label>
                <textarea
                  v-model="formMicro.laudo_previo"
                  rows="3"
                  placeholder="Descreva os achados histopatológicos/citopatológicos para revisão do preceptor..."
                  class="w-full border rounded-lg p-3 bg-white"
                ></textarea>
              </div>
            </div>
            <button
              @click="executarMicroscopia('SALVAR_LAUDO_PREVIO')"
              class="bg-blue-700 hover:bg-blue-800 text-white font-bold px-4 py-2 rounded-lg transition">
              💾 Salvar Laudo Prévio e Enviar para Revisão do Patologista
            </button>
          </div>

          <!-- Bloco do Médico Patologista: Revisão, Complementos/IHQ e Liberação (RF035 a RF039) -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Revisão do Laudo Prévio (RF035) -->
            <div class="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
              <h3 class="font-bold text-slate-800">2. Revisão pelo Médico Patologista (RF035)</h3>
              <input
                v-model="formMicro.observacao_revisao"
                type="text"
                placeholder="Observações da preceptoria/revisão..."
                class="w-full border rounded-lg px-3 py-1.5 bg-white"
              />
              <div class="flex flex-wrap gap-2">
                <button
                  @click="formMicro.decisao = 'APROVADO'; executarMicroscopia('REVISAR_PATOLOGISTA')"
                  class="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-3 py-1.5 rounded-lg">
                  👍 Aprovar Laudo Prévio
                </button>
                <button
                  @click="formMicro.decisao = 'REPROVADO'; executarMicroscopia('REVISAR_PATOLOGISTA')"
                  class="bg-rose-600 hover:bg-rose-700 text-white font-bold px-3 py-1.5 rounded-lg">
                  👎 Reprovar / Devolver ao Residente
                </button>
              </div>
            </div>

            <!-- Solicitação de IHQ / Complementos (RF036, RF037) -->
            <div class="p-4 bg-amber-50/70 rounded-xl border border-amber-200 space-y-2.5">
              <h3 class="font-bold text-amber-950">3. Solicitar Imuno-histoquímica ou Complementos (RF036, RF037)</h3>
              <select v-model="formMicro.tipo_pedido" class="w-full border rounded-lg px-2.5 py-1.5 bg-white">
                <option value="IHQ">IHQ — Imuno-histoquímica (Gera código IHQ vinculado)</option>
                <option value="NOVO_CORTE">Novo Corte / Desbaste de Bloco (Retorno Técnico)</option>
                <option value="COLORACAO_ESPECIAL">Coloração Especial (PAS, Ziehl, Giemsa, Reticulina)</option>
                <option value="REVISAO_MACRO">Revisão de Peça na Macroscopia</option>
              </select>
              <input
                v-model="formMicro.marcadores"
                type="text"
                placeholder="Marcadores / Coloração (ex: RE, RP, HER2, Ki-67, CD20, p63)..."
                class="w-full border rounded-lg px-2.5 py-1.5 bg-white"
              />
              <button
                @click="executarMicroscopia('SOLICITAR_COMPLEMENTO')"
                class="w-full bg-amber-600 hover:bg-amber-700 text-white font-bold py-1.5 rounded-lg">
                🔄 Registrar Pedido e Reintroduzir no Processamento
              </button>
            </div>
          </div>

          <!-- Liberação Oficial (RF038 com Confirmação Explícita RNF009), Arquivamento de Lâminas (RF039) e Cancelamento -->
          <div class="p-4 bg-emerald-50 rounded-xl border border-emerald-300 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 class="font-bold text-emerald-950">4. Conclusão, Liberação no AGHU, SISCAN e Arquivamento Físico (RF038, RF039)</h3>
              <p class="text-[11px] text-emerald-800">
                Se este exame for uma Congelação (CO), a liberação gera automaticamente a pendência vinculada de Histopatológico (HP).
              </p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                @click="modalConfirmarLiberacao = true"
                class="bg-emerald-700 hover:bg-emerald-800 text-white font-bold px-4 py-2 rounded-lg shadow">
                ✅ Marcar Exame como Liberado (RF038)
              </button>
              <button
                @click="executarMicroscopia('ARQUIVAR_LAMINAS')"
                class="bg-slate-800 hover:bg-slate-900 text-white font-bold px-4 py-2 rounded-lg">
                🗄️ Arquivar Lâminas (RF039)
              </button>
              <button
                v-if="exameAtivo.requer_siscan && !exameAtivo.siscan_lancado"
                @click="executarMicroscopia('REGISTRAR_SISCAN')"
                class="bg-pink-700 hover:bg-pink-800 text-white font-bold px-4 py-2 rounded-lg">
                🎗️ Confirmar Lançamento SISCAN
              </button>
              <button
                @click="modalCancelarExame = true"
                class="bg-rose-100 hover:bg-rose-200 text-rose-800 border border-rose-300 font-bold px-3 py-2 rounded-lg">
                🚫 Cancelar Este Exame
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL DE CONFIRMAÇÃO EXPLÍCITA DE AÇÃO CRÍTICA (RNF009) -->
    <div v-if="modalConfirmarLiberacao && exameAtivo" class="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 text-xs">
        <h3 class="text-base font-extrabold text-emerald-900">⚠️ Confirmação Explícita de Liberação (RNF009)</h3>
        <p class="text-slate-700 leading-relaxed">
          Você confirma que o laudo oficial do exame <strong>{{ exameAtivo.codigo_sap }}</strong> (Paciente: <strong>{{ exameAtivo.nome_paciente }}</strong>) foi assinado e liberado no AGHU?
        </p>
        <div class="flex justify-end gap-2 pt-2">
          <button @click="modalConfirmarLiberacao = false" class="px-4 py-2 bg-slate-200 rounded-lg font-semibold">Voltar</button>
          <button @click="modalConfirmarLiberacao = false; executarMicroscopia('LIBERAR_EXAME')" class="px-5 py-2 bg-emerald-700 text-white rounded-lg font-bold">
            Sim, Confirmar Liberação
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL DE CANCELAMENTO INDIVIDUAL DE EXAME (Reunião págs. 32-35) -->
    <div v-if="modalCancelarExame && exameAtivo" class="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4 text-xs">
        <h3 class="text-base font-extrabold text-rose-900">🚫 Cancelar Exame Individualmente ({{ exameAtivo.codigo_sap }})</h3>
        <p class="text-slate-600">
          Cancela apenas o exame <strong>{{ exameAtivo.codigo_sap }}</strong> (ex: cancelar somente a IHQ mantendo o Histopatológico ativo), preservando o histórico.
        </p>
        <textarea
          v-model="formMicro.motivo_cancelamento"
          rows="2"
          placeholder="Informe o motivo do cancelamento ou devolução na bancada..."
          class="w-full border border-rose-300 rounded-lg p-2.5"
        ></textarea>
        <div class="flex justify-end gap-2">
          <button @click="modalCancelarExame = false" class="px-4 py-2 bg-slate-200 rounded-lg font-semibold">Voltar</button>
          <button @click="modalCancelarExame = false; executarMicroscopia('CANCELAR_EXAME')" class="px-5 py-2 bg-rose-700 text-white rounded-lg font-bold">
            Confirmar Cancelamento
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL DE IMPRESSÃO TÉRMICA ZPL -->
    <div v-if="etiquetaModal" class="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 text-xs">
        <div class="flex justify-between items-center border-b pb-2">
          <h3 class="text-base font-bold text-slate-800">🖨️ Etiqueta Térmica QR Code — {{ etiquetaModal.titulo }}</h3>
          <button @click="etiquetaModal = null" class="text-lg font-bold text-slate-400">✕</button>
        </div>
        <p class="font-mono text-slate-700">QR Code: <strong>{{ etiquetaModal.qr }}</strong></p>
        <pre class="bg-slate-900 text-emerald-400 p-3 rounded-lg font-mono text-[11px] overflow-x-auto">{{ etiquetaModal.zpl }}</pre>
        <div class="flex justify-end gap-2">
          <button @click="imprimirJanela" class="bg-blue-700 text-white px-4 py-2 rounded-lg font-bold">🖨️ Imprimir na Zebra/Argox</button>
          <button @click="etiquetaModal = null" class="bg-slate-200 px-4 py-2 rounded-lg font-semibold">Fechar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../services/api'

const abaSetor = ref<'MACRO' | 'PROC' | 'MICRO'>('MACRO')
const perfilAtivo = ref('Macroscopista')
const operadorLogado = ref('dr.patologia.hc')
const codigoBipado = ref('')
const filaRecebidos = ref<any[]>([])
const exameAtivo = ref<any>(null)
const mensagemSucesso = ref('')
const mensagemErro = ref('')
const etiquetaModal = ref<any>(null)
const modalConfirmarLiberacao = ref(false)
const modalCancelarExame = ref(false)

const formMacro = ref({
  frasco_id: 0,
  descricao_macroscopica: '',
  quantidade_cassetes: 2,
  descricao_fragmentos: 'Fragmentos representativos em totalidade'
})

const formProc = ref({
  quantidade_blocos: 1,
  quantidade_laminas: 2,
  tipo_coloracao: 'H&E (Hematoxilina-Eosina)',
  marcador_ihq: ''
})

const formMicro = ref({
  laudo_previo: '',
  diagnostico_associado: '',
  decisao: 'APROVADO',
  observacao_revisao: '',
  tipo_pedido: 'IHQ',
  marcadores: 'Ki-67, RE, RP, HER2',
  justificativa: 'Elucidação diagnóstica complementar solicitada pela preceptoria',
  motivo_cancelamento: ''
})

const carregarFilaRecebidos = async () => {
  try {
    const res = await api.get('/api/sap/exames', { params: { limite: 50, somente_ativos: false } })
    filaRecebidos.value = (res.data.exames || []).filter((e: any) => e.recebido_no_sap)
    if (!exameAtivo.value && filaRecebidos.value.length > 0) {
      await selecionarExameDaFila(filaRecebidos.value[0].codigo_sap)
    }
  } catch {
    // ignore
  }
}

const sincronizarFormularioComExame = (ex: any) => {
  exameAtivo.value = ex
  if (ex.arvore_subprodutos && ex.arvore_subprodutos.length > 0) {
    formMacro.value.frasco_id = ex.arvore_subprodutos[0].id
  }
  formMacro.value.descricao_macroscopica = ex.descricao_macroscopica || `Espécime recebido em formol referente a ${ex.descricao_material}, medindo 2,5 x 1,8 x 1,0 cm, superfície pardo-acastanhada e elástica.`
  formMicro.value.laudo_previo = ex.laudo_previo_residente || ''
  formMicro.value.diagnostico_associado = ex.diagnostico_associado || ''
}

const identificarSubproduto = async () => {
  mensagemErro.value = ''
  mensagemSucesso.value = ''
  if (!codigoBipado.value.trim()) return
  try {
    if (abaSetor.value === 'MACRO') {
      const res = await api.post('/api/sap/macroscopia/identificar', {
        codigo: codigoBipado.value.trim(),
        operador: operadorLogado.value
      })
      sincronizarFormularioComExame(res.data.exame)
      mensagemSucesso.value = `Frasco/Exame ${res.data.exame.codigo_sap} identificado na bancada de Macroscopia.`
    } else {
      const res = await api.get(`/api/sap/rastreabilidade/${encodeURIComponent(codigoBipado.value.trim())}`)
      sincronizarFormularioComExame(res.data.exame)
      mensagemSucesso.value = `Item vinculado ao exame ${res.data.exame.codigo_sap} carregado com sucesso.`
    }
  } catch (err: any) {
    mensagemErro.value = err.response?.data?.detail || 'Subproduto não encontrado.'
  }
}

const selecionarExameDaFila = async (codigoSap: string) => {
  if (!codigoSap) return
  codigoBipado.value = codigoSap
  await identificarSubproduto()
}

const salvarMacroscopiaGerarCassetes = async () => {
  if (!exameAtivo.value) return
  mensagemErro.value = ''
  mensagemSucesso.value = ''
  try {
    const res = await api.post('/api/sap/macroscopia/registrar', {
      exame_id: exameAtivo.value.id,
      frasco_id: formMacro.value.frasco_id,
      descricao_macroscopica: formMacro.value.descricao_macroscopica,
      quantidade_cassetes: formMacro.value.quantidade_cassetes,
      descricao_fragmentos: formMacro.value.descricao_fragmentos,
      operador: operadorLogado.value
    })
    sincronizarFormularioComExame(res.data.exame)
    mensagemSucesso.value = res.data.mensagem
    await carregarFilaRecebidos()
  } catch (err: any) {
    mensagemErro.value = err.response?.data?.detail || 'Erro ao salvar macroscopia.'
  }
}

const confirmarEnviarCassetesProcessamento = async () => {
  if (!exameAtivo.value) return
  mensagemErro.value = ''
  mensagemSucesso.value = ''
  try {
    const res = await api.post('/api/sap/macroscopia/enviar-processamento', {
      exame_id: exameAtivo.value.id,
      operador: operadorLogado.value
    })
    sincronizarFormularioComExame(res.data.exame)
    mensagemSucesso.value = res.data.mensagem
    abaSetor.value = 'PROC'
    await carregarFilaRecebidos()
  } catch (err: any) {
    mensagemErro.value = err.response?.data?.detail || 'Erro ao enviar cassetes.'
  }
}

const executarProcessamento = async (acao: string) => {
  if (!exameAtivo.value) return
  mensagemErro.value = ''
  mensagemSucesso.value = ''
  try {
    const res = await api.post('/api/sap/processamento/executar', {
      exame_id: exameAtivo.value.id,
      acao_processamento: acao,
      quantidade_blocos: formProc.value.quantidade_blocos,
      quantidade_laminas: formProc.value.quantidade_laminas,
      tipo_coloracao: formProc.value.tipo_coloracao,
      marcador_ihq: formProc.value.marcador_ihq || undefined,
      operador: operadorLogado.value
    })
    sincronizarFormularioComExame(res.data.exame)
    mensagemSucesso.value = res.data.mensagem
    if (acao === 'ENVIAR_MICROSCOPIA') {
      abaSetor.value = 'MICRO'
    }
    await carregarFilaRecebidos()
  } catch (err: any) {
    mensagemErro.value = err.response?.data?.detail || 'Erro no Processamento Técnico.'
  }
}

const executarMicroscopia = async (acao: string) => {
  if (!exameAtivo.value) return
  mensagemErro.value = ''
  mensagemSucesso.value = ''
  try {
    const res = await api.post('/api/sap/microscopia/executar', {
      exame_id: exameAtivo.value.id,
      acao_microscopia: acao,
      laudo_previo: formMicro.value.laudo_previo,
      diagnostico_associado: formMicro.value.diagnostico_associado,
      decisao: formMicro.value.decisao,
      observacao_revisao: formMicro.value.observacao_revisao,
      tipo_pedido: formMicro.value.tipo_pedido,
      marcadores: formMicro.value.marcadores,
      justificativa: formMicro.value.justificativa,
      motivo_cancelamento: formMicro.value.motivo_cancelamento,
      perfil: perfilAtivo.value,
      operador: operadorLogado.value
    })
    sincronizarFormularioComExame(res.data.exame)
    mensagemSucesso.value = res.data.mensagem
    await carregarFilaRecebidos()
  } catch (err: any) {
    mensagemErro.value = err.response?.data?.detail || 'Erro na operação de Microscopia.'
  }
}

const imprimirJanela = () => {
  window.print()
}

onMounted(() => {
  carregarFilaRecebidos()
})
</script>
