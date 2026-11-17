<template>
  <div class="p-6 space-y-6">
    <!-- Cabeçalho do Painel SAP -->
    <header class="flex flex-col justify-between gap-4 lg:flex-row lg:items-center bg-white p-5 rounded-xl shadow-sm border border-slate-200">
      <div>
        <h1 class="text-2xl md:text-3xl font-extrabold text-blue-900 tracking-tight">
          HC-UFPE / EBSERH - Serviço de Anatomia Patológica (SAP)
        </h1>
        <p class="text-sm text-slate-600 mt-1">
          SISPATO — Monitoramento em Tempo Real de Amostras, Subprodutos, Laudos Prévios, SISCAN e Prazos Legais
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <router-link
          to="/recepcao"
          class="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-4 py-2 rounded-lg shadow transition text-sm">
          + Receber Amostra (AGHU / SUS)
        </router-link>
        <router-link
          to="/bancadas"
          class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-4 py-2 rounded-lg shadow transition text-sm">
          🔬 Bancadas (Macro / Proc / Micro)
        </router-link>
        <button
          @click="carregarDados()"
          class="bg-blue-700 hover:bg-blue-800 text-white font-medium px-4 py-2 rounded-lg shadow transition flex items-center gap-2 text-sm">
          🔄 Atualizar Painel
        </button>
      </div>
    </header>

    <!-- Indicadores / KPIs Estratégicos -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-blue-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Total no Sistema</span>
        <p class="text-2xl font-bold text-slate-800 mt-1">{{ kpis.total_exames || 0 }}</p>
        <span class="text-[11px] text-blue-700 font-semibold">
          {{ kpis.recebidos_sap_local || 0 }} recebidos nas bancadas SAP
        </span>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-amber-500">
        <span class="text-xs font-semibold uppercase text-slate-400">Em Processamento</span>
        <p class="text-2xl font-bold text-amber-600 mt-1">{{ kpis.em_andamento || 0 }}</p>
        <span class="text-[11px] text-slate-500">Fila ativa do laboratório</span>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-red-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Congelação / Urgentes</span>
        <p class="text-2xl font-bold text-red-600 mt-1">{{ kpis.congelacoes_urgentes || 0 }}</p>
        <span class="text-[11px] text-red-700 font-semibold">Prioridade máxima no topo</span>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-rose-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Alerta Prazo (≥15d)</span>
        <p class="text-2xl font-bold text-rose-600 mt-1">{{ kpis.alerta_meta_20_dias || 0 }}</p>
        <span class="text-[11px] text-slate-500">Meta interna: 20 dias</span>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-purple-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Casos Oncológicos</span>
        <p class="text-2xl font-bold text-purple-700 mt-1">{{ kpis.monitorados_lei_60_dias || 0 }}</p>
        <span class="text-[11px] text-purple-700 font-semibold">Lei Federal 60 Dias</span>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-emerald-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Concluídos e Liberados</span>
        <p class="text-2xl font-bold text-emerald-600 mt-1">{{ kpis.concluidos || 0 }}</p>
        <span class="text-[11px] text-slate-500">SISCAN pend.: {{ kpis.pendentes_siscan || 0 }}</span>
      </div>
    </div>

    <!-- Lista de Exames em Tempo Real -->
    <div class="bg-white rounded-xl shadow p-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-2">
        <h2 class="text-xl font-bold text-slate-800 flex items-center gap-2">
          <span>📋</span> Fila de Exames por Etapa do Processo
        </h2>
        <span class="text-xs text-slate-500">
          Códigos SAP: <strong>HP</strong> (Histopatológico) • <strong>IHQ</strong> (Imuno-histoquímica) • <strong>CO</strong> (Congelação - Topo) • <strong>CG / CCV</strong> (Citologia)
        </span>
      </div>

      <div v-if="erroCarga" class="mb-4 p-3 bg-rose-50 border border-rose-300 text-rose-800 rounded-lg text-sm">
        ⚠️ {{ erroCarga }}
      </div>

      <!-- Filtros Rápidos e Busca -->
      <form @submit.prevent="carregarDados()" class="mb-4 grid grid-cols-1 md:grid-cols-5 gap-2">
        <input
          v-model="busca"
          type="text"
          placeholder="Buscar por solicitação, código SAP, paciente, prontuário ou material..."
          class="md:col-span-2 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select v-model="filtroEtapa" @change="carregarDados()" class="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">Todas as Etapas</option>
          <option value="Recepção">Recepção / Triagem</option>
          <option value="Macroscopia">Macroscopia</option>
          <option value="Processamento">Processamento Técnico</option>
          <option value="Microscopia">Microscopia</option>
          <option value="Revisão">Revisão Patologista</option>
          <option value="A Coletar">A Coletar (AGHU)</option>
          <option value="Concluído">Concluído / Liberado</option>
        </select>
        <select v-model="filtroTipo" @change="carregarDados()" class="border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
          <option value="">Todos os Tipos (HP/CO/IHQ/CG/CCV)</option>
          <option value="CO">CO — Congelação (Urgente)</option>
          <option value="HP">HP — Histopatológico</option>
          <option value="IHQ">IHQ — Imuno-histoquímica</option>
          <option value="CG">CG — Citopatologia Geral</option>
          <option value="CCV">CCV — Citologia Cérvico-Vaginal</option>
        </select>
        <div class="flex items-center gap-2">
          <label class="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
            <input type="checkbox" v-model="somenteAtivos" @change="carregarDados()" class="rounded text-blue-600" />
            Somente em aberto
          </label>
          <button type="submit" class="ml-auto bg-blue-700 hover:bg-blue-800 text-white text-sm font-medium px-4 py-2 rounded-lg">
            Filtrar
          </button>
        </div>
      </form>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-100 text-slate-700 text-xs uppercase tracking-wider">
              <th class="p-3">Código SAP / Solicitação AGHU</th>
              <th class="p-3">Paciente / Prontuário</th>
              <th class="p-3">Tipo de Exame / Material</th>
              <th class="p-3">Origem / Último Operador</th>
              <th class="p-3">Etapa Atual & Pré-Laudo</th>
              <th class="p-3">Tempo Decorrido (SLA)</th>
              <th class="p-3">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-sm">
            <tr
              v-for="exame in exames"
              :key="`${exame.codigo_sap}-${exame.codigo_solicitacao}`"
              :class="[
                'hover:bg-slate-50 transition',
                exame.sigla_exame === 'CO' || exame.urgente ? 'bg-red-50/40' : '',
                exame.recebido_no_sap ? 'border-l-4 border-emerald-500' : ''
              ]"
            >
              <td class="p-3">
                <div class="flex items-center gap-1.5">
                  <span class="font-mono font-extrabold text-blue-900 text-base">
                    {{ exame.codigo_sap }}
                  </span>
                  <span
                    v-if="exame.sigla_exame === 'CO' || exame.urgente"
                    class="px-1.5 py-0.5 bg-red-600 text-white text-[10px] font-extrabold uppercase rounded animate-pulse"
                  >
                    🚨 URGENTE
                  </span>
                </div>
                <span class="text-xs text-slate-500 font-medium block">
                  Solicitação: <strong>#{{ exame.codigo_solicitacao }}</strong> ({{ exame.origem_peca || 'HC' }})
                </span>
                <span v-if="exame.exame_origem_codigo" class="text-[11px] text-indigo-700 font-semibold block">
                  🔗 Vinculado a: {{ exame.exame_origem_codigo }}
                </span>
              </td>

              <td class="p-3">
                <span class="font-bold text-slate-800">{{ exame.nome_paciente }}</span>
                <span class="block text-xs text-slate-500">Prontuário: {{ exame.prontuario_paciente || 'SUS Externo' }}</span>
              </td>

              <td class="p-3 max-w-xs">
                <div class="flex flex-wrap items-center gap-1 mb-1">
                  <span class="px-2 py-0.5 bg-blue-100 text-blue-900 text-xs font-bold rounded">
                    {{ exame.tipo_exame }} ({{ exame.sigla_exame }})
                  </span>
                  <span v-if="exame.suspeita_neoplasia" class="px-2 py-0.5 bg-rose-100 text-rose-800 text-xs font-bold rounded">
                    Onco
                  </span>
                  <span v-if="exame.requer_siscan" class="px-2 py-0.5 bg-pink-100 text-pink-800 text-[10px] font-bold rounded">
                    SISCAN {{ exame.siscan_lancado ? '✓' : 'Pend.' }}
                  </span>
                  <span class="px-2 py-0.5 bg-slate-200 text-slate-700 text-xs font-semibold rounded">
                    {{ exame.quantidade_amostras }} frasco(s)
                  </span>
                </div>
                <span class="block text-xs text-slate-600 truncate" :title="exame.descricao_material">
                  <strong>Material:</strong> {{ exame.descricao_material }}
                </span>
                <span v-if="exame.recebido_no_sap" class="block text-[11px] text-emerald-700 font-semibold mt-0.5">
                  🧬 {{ exame.quantidade_cassetes || 0 }} cassete(s) • {{ exame.quantidade_blocos || 0 }} bloco(s) • {{ exame.quantidade_laminas || 0 }} lâmina(s)
                </span>
              </td>

              <td class="p-3 text-xs text-slate-600">
                <span class="font-semibold text-slate-700 block">{{ exame.origem }}</span>
                <span class="text-[11px] text-slate-500">Última ação: <strong>{{ exame.ultimo_operador || 'AGHU' }}</strong></span>
              </td>

              <td class="p-3">
                <span
                  class="px-2.5 py-1 text-xs font-semibold rounded-full inline-block"
                  :class="
                    exame.etapa_atual.includes('Concluído')
                      ? 'bg-emerald-100 text-emerald-800'
                      : exame.recebido_no_sap
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-amber-100 text-amber-800'
                  "
                >
                  {{ exame.etapa_atual }}
                </span>
                <span class="block text-[11px] text-slate-500 mt-1">
                  <strong>Pré-laudo:</strong> {{ exame.status_pre_laudo || exame.laudo_final_aghu }}
                </span>
              </td>

              <td class="p-3 text-xs">
                <div class="font-bold" :class="exame.dias_decorridos >= 15 ? 'text-rose-600' : 'text-slate-800'">
                  ⏱️ {{ exame.dias_decorridos }}º dia corrido <span class="font-normal text-slate-500">(Meta: {{ exame.meta_dias_limite }}d)</span>
                </div>
                <div v-if="exame.suspeita_neoplasia" class="text-purple-700 font-semibold mt-0.5">
                  🎗️ Onco: {{ exame.dias_decorridos }}º dia <span class="font-normal text-slate-500">(Lei: {{ exame.lei_onco_limite }}d)</span>
                </div>
                <div v-if="exame.alerta_retencao_etapa" class="text-amber-700 font-bold text-[11px] mt-0.5">
                  ⚠️ Retido além do prazo da etapa
                </div>
              </td>

              <td class="p-3">
                <div class="flex flex-col gap-1">
                  <button
                    @click="abrirDetalhes(exame)"
                    class="text-xs bg-blue-50 hover:bg-blue-100 text-blue-900 border border-blue-200 font-semibold px-3 py-1.5 rounded transition"
                  >
                    🌳 Árvore & Histórico
                  </button>
                  <router-link
                    v-if="!exame.recebido_no_sap"
                    :to="`/recepcao?solicitacao=${exame.codigo_solicitacao}`"
                    class="text-center text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 font-semibold px-3 py-1 rounded transition"
                  >
                    Iniciar Recebimento →
                  </router-link>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-4 flex flex-col md:flex-row items-center justify-between gap-2 text-xs text-slate-500">
        <span>Exibindo {{ exames.length }} de {{ totalFiltrado }} exame(s)</span>
        <button
          v-if="exames.length < totalFiltrado"
          @click="carregarDados(true)"
          :disabled="carregando"
          class="bg-slate-200 hover:bg-slate-300 text-slate-800 font-medium px-4 py-2 rounded-lg transition disabled:opacity-50"
        >
          {{ carregando ? 'Carregando...' : 'Carregar mais' }}
        </button>
      </div>
    </div>

    <!-- MODAL: VISÃO UNIFICADA, ÁRVORE HIERÁRQUICA DE SUBPRODUTOS E AUDITORIA (RF040 a RF042) -->
    <div v-if="exameSelecionado" class="fixed inset-0 bg-black/60 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-4xl w-full p-6 shadow-2xl max-h-[92vh] overflow-y-auto">
        <div class="flex justify-between items-start border-b border-slate-200 pb-4 mb-4">
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-xl font-extrabold text-blue-900">
                Exame {{ exameSelecionado.codigo_sap }} (Solicitação #{{ exameSelecionado.codigo_solicitacao }})
              </h3>
              <span v-if="exameSelecionado.urgente" class="px-2 py-0.5 bg-red-600 text-white text-xs font-bold rounded">
                URGENTE
              </span>
            </div>
            <p class="text-sm text-slate-600 mt-1">
              Paciente: <strong>{{ exameSelecionado.nome_paciente }}</strong> • Prontuário: <strong>{{ exameSelecionado.prontuario_paciente || 'SUS' }}</strong> • Etapa: <strong>{{ exameSelecionado.etapa_atual }}</strong>
            </p>
          </div>
          <button @click="exameSelecionado = null" class="text-slate-400 hover:text-slate-700 text-xl font-bold">✕</button>
        </div>

        <div class="space-y-5">
          <!-- Dados Clínicos e Status do Pré-Laudo -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
            <div class="space-y-1.5">
              <p><strong>Tipo de Exame:</strong> {{ exameSelecionado.tipo_exame }} ({{ exameSelecionado.sigla_exame }})</p>
              <p><strong>Tipo de Peça:</strong> {{ exameSelecionado.tipo_peca || 'Geral' }}</p>
              <p><strong>Material Analisado:</strong> {{ exameSelecionado.descricao_material }}</p>
              <p><strong>QR Code Mestre:</strong> <code class="bg-slate-200 px-1.5 py-0.5 rounded font-mono">{{ exameSelecionado.qr_code }}</code></p>
              <p v-if="exameSelecionado.exame_origem_codigo"><strong>Vínculo de Origem:</strong> {{ exameSelecionado.exame_origem_codigo }}</p>
            </div>
            <div class="space-y-1.5">
              <p><strong>Macroscopia:</strong> {{ exameSelecionado.laudo_macroscopico_formal }}</p>
              <p><strong>Status do Pré-Laudo (Consulta Recepção):</strong> <span class="font-bold text-blue-900">{{ exameSelecionado.status_pre_laudo || exameSelecionado.laudo_final_aghu }}</span></p>
              <p v-if="exameSelecionado.diagnostico_associado"><strong>Diagnóstico Associado:</strong> {{ exameSelecionado.diagnostico_associado }}</p>
              <p v-if="exameSelecionado.requer_siscan">
                <strong>Controle SISCAN (Ministério da Saúde):</strong>
                <span :class="exameSelecionado.siscan_lancado ? 'text-emerald-700 font-bold' : 'text-rose-700 font-bold'">
                  {{ exameSelecionado.siscan_lancado ? 'Lançado no SISCAN ✓' : 'Pendente de lançamento após liberação' }}
                </span>
              </p>
            </div>
          </div>

          <!-- Árvore Hierárquica de Subprodutos (Frasco -> Cassete -> Bloco -> Lâmina) -->
          <div v-if="exameSelecionado.arvore_subprodutos && exameSelecionado.arvore_subprodutos.length">
            <h4 class="font-bold text-slate-800 text-sm mb-2">
              🌳 Árvore Hierárquica de Subprodutos (Frasco → Cassete → Bloco → Lâmina)
            </h4>
            <div class="space-y-3">
              <div
                v-for="frasco in exameSelecionado.arvore_subprodutos"
                :key="frasco.qr_code"
                class="p-3.5 bg-slate-50 border border-slate-200 rounded-xl text-xs"
              >
                <div class="flex flex-wrap justify-between items-center gap-2 font-bold text-slate-900">
                  <span>🧪 Frasco #{{ frasco.numero_amostra }} — {{ frasco.descricao_material }} ({{ frasco.qr_code }})</span>
                  <span class="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-[11px]">{{ frasco.status_frasco }}</span>
                </div>

                <!-- Cassetes do Frasco -->
                <div v-if="frasco.cassetes && frasco.cassetes.length" class="mt-2 pl-4 border-l-2 border-blue-300 space-y-2">
                  <div v-for="cas in frasco.cassetes" :key="cas.qr_code" class="bg-white p-2.5 rounded-lg border border-slate-200">
                    <div class="flex justify-between items-center font-semibold text-indigo-900">
                      <span>🗂️ Cassete {{ cas.sigla_cassete }}: {{ cas.codigo_cassete }}</span>
                      <span class="text-[11px] text-slate-500">{{ cas.status_cassete }}</span>
                    </div>

                    <!-- Blocos do Cassete -->
                    <div v-if="cas.blocos && cas.blocos.length" class="mt-1.5 pl-4 border-l-2 border-indigo-300 space-y-1.5">
                      <div v-for="blk in cas.blocos" :key="blk.qr_code" class="bg-slate-50 p-2 rounded border border-slate-200">
                        <div class="flex justify-between items-center font-semibold text-amber-900">
                          <span>🧊 Bloco: {{ blk.codigo_bloco }}</span>
                          <span class="text-[11px]">
                            {{ blk.arquivado ? `Arquivado (${blk.local_arquivo})` : blk.realizou_corte ? 'Corte Realizado' : 'Aguardando Corte' }}
                          </span>
                        </div>

                        <!-- Lâminas do Bloco -->
                        <div v-if="blk.laminas && blk.laminas.length" class="mt-1 pl-4 border-l-2 border-emerald-400 space-y-1">
                          <div
                            v-for="lam in blk.laminas"
                            :key="lam.qr_code"
                            class="flex flex-wrap justify-between items-center bg-white px-2.5 py-1 rounded border border-slate-200 text-emerald-950"
                          >
                            <span>🔬 Lâmina: <strong>{{ lam.codigo_lamina }}</strong> ({{ lam.tipo_coloracao }} {{ lam.marcador_ihq || '' }})</span>
                            <span class="text-[11px] font-semibold text-emerald-700">{{ lam.status_lamina }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Histórico de Rejeições / Devoluções (Preservado mesmo após superado) -->
          <div v-if="exameSelecionado.rejeicoes_historico && exameSelecionado.rejeicoes_historico.length">
            <h4 class="font-bold text-rose-800 text-sm mb-2">
              ⚠️ Histórico de Não Conformidades / Rejeições (Justificativa de SLA)
            </h4>
            <div class="space-y-2">
              <div
                v-for="rej in exameSelecionado.rejeicoes_historico"
                :key="rej.id"
                class="p-3 bg-rose-50 border-l-4 border-rose-600 rounded text-xs"
              >
                <div class="flex justify-between font-bold text-rose-900">
                  <span>{{ rej.tipo_inconformidade }} — {{ rej.motivo_padrao }}</span>
                  <span>{{ rej.data_rejeicao }} ({{ rej.superada ? 'Superada em ' + rej.data_superacao : 'Ativa / Aguardando Retorno' }})</span>
                </div>
                <p v-if="rej.detalhe_outros" class="text-rose-800 mt-1">Detalhe: {{ rej.detalhe_outros }}</p>
              </div>
            </div>
          </div>

          <!-- Trilha de Auditoria e Movimentações -->
          <div>
            <h4 class="font-bold text-slate-700 text-sm mb-2">📜 Trilha de Auditoria e Histórico de Movimentação (RF040)</h4>
            <div class="space-y-2">
              <div v-for="(log, idx) in exameSelecionado.historico" :key="idx" class="p-3 bg-blue-50 border-l-4 border-blue-600 rounded text-xs">
                <div class="flex justify-between font-semibold text-blue-900 mb-1">
                  <span>{{ log.etapa }} — Perfil: {{ log.perfil }}</span>
                  <span class="text-slate-500">{{ log.timestamp }}</span>
                </div>
                <p class="text-slate-700">{{ log.acao }}</p>
                <span class="text-slate-400 text-[10px] mt-1 block">Operador autenticado: {{ log.operador }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-6 flex justify-end gap-2">
          <button @click="exameSelecionado = null" class="bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-800">
            Fechar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../services/api'

const kpis = ref<any>({})
const exames = ref<any[]>([])
const exameSelecionado = ref<any>(null)
const busca = ref('')
const filtroEtapa = ref('')
const filtroTipo = ref('')
const somenteAtivos = ref(true)
const totalFiltrado = ref(0)
const carregando = ref(false)
const erroCarga = ref('')
const LIMITE = 100

const carregarDados = async (acumular = false) => {
  carregando.value = true
  erroCarga.value = ''
  try {
    const res = await api.get('/api/sap/exames', {
      params: {
        limite: LIMITE,
        offset: acumular ? exames.value.length : 0,
        busca: busca.value || undefined,
        etapa: filtroEtapa.value || undefined,
        tipo_exame: filtroTipo.value || undefined,
        somente_ativos: somenteAtivos.value,
      }
    })
    kpis.value = res.data.kpis
    exames.value = acumular ? [...exames.value, ...res.data.exames] : res.data.exames
    totalFiltrado.value = res.data.total_filtrado
  } catch (err: any) {
    console.error('Erro ao carregar dados do SAP:', err)
    erroCarga.value =
      err.response?.data?.detail ||
      'Não foi possível conectar ao backend (http://127.0.0.1:8000). Verifique se o servidor FastAPI está rodando.'
  } finally {
    carregando.value = false
  }
}

const abrirDetalhes = async (exame: any) => {
  try {
    const codigo = exame.recebido_no_sap ? exame.codigo_sap : exame.codigo_solicitacao
    const res = await api.get(`/api/sap/rastreabilidade/${encodeURIComponent(codigo)}`)
    exameSelecionado.value = res.data.exame
  } catch {
    exameSelecionado.value = exame
  }
}

onMounted(() => {
  carregarDados()
})
</script>
