<template>
  <div class="p-6">
    <!-- Cabeçalho do Painel SAP (Limpo, sem botões redundantes) -->
    <header class="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-center bg-white p-5 rounded-xl shadow-sm border border-slate-200">
      <div>
        <h1 class="text-2xl md:text-3xl font-extrabold text-blue-900 tracking-tight">
          HC-UFPE / EBSERH - Serviço de Anatomia Patológica (SAP)
        </h1>
        <p class="text-sm text-slate-600 mt-1">
          SISPATO — Monitoramento em Tempo Real de Amostras, Laudos, Rastreabilidade e Prazos
        </p>
      </div>

      <div>
        <button 
          @click="carregarDados" 
          class="bg-blue-700 hover:bg-blue-800 text-white font-medium px-4 py-2 rounded-lg shadow transition flex items-center gap-2 text-sm">
          🔄 Atualizar Painel
        </button>
      </div>
    </header>

    <!-- Indicadores / KPIs -->
    <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-blue-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Total no Sistema</span>
        <p class="text-2xl font-bold text-slate-800 mt-1">{{ kpis.total_exames || 0 }}</p>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-amber-500">
        <span class="text-xs font-semibold uppercase text-slate-400">Em Processamento</span>
        <p class="text-2xl font-bold text-amber-600 mt-1">{{ kpis.em_andamento || 0 }}</p>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-rose-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Alerta Prazo (≥15 Dias)</span>
        <p class="text-2xl font-bold text-rose-600 mt-1">{{ kpis.alerta_meta_20_dias || 0 }}</p>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-purple-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Casos Oncológicos (Lei 60d)</span>
        <p class="text-2xl font-bold text-purple-700 mt-1">{{ kpis.monitorados_lei_60_dias || 0 }}</p>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-emerald-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Concluídos e Arquivados</span>
        <p class="text-2xl font-bold text-emerald-600 mt-1">{{ kpis.concluidos || 0 }}</p>
      </div>
    </div>

    <!-- Lista de Exames em Tempo Real -->
    <div class="bg-white rounded-xl shadow p-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-2">
        <h2 class="text-xl font-bold text-slate-800 flex items-center gap-2">
          <span>📋</span> Fila de Exames por Etapa do Processo
        </h2>
        <span class="text-xs text-slate-500">
          Códigos SAP: <strong>HP</strong> (Histopatológico) • <strong>IHQ</strong> (Imuno-histoquímica) • <strong>CO</strong> (Congelação) • <strong>CG / CCV</strong> (Citologia)
        </span>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-100 text-slate-700 text-xs uppercase tracking-wider">
              <th class="p-3">Código SAP / Solicitação AGHU</th>
              <th class="p-3">Paciente / Prontuário</th>
              <th class="p-3">Tipo de Exame / Material</th>
              <th class="p-3">Origem / Unidade</th>
              <th class="p-3">Etapa Atual</th>
              <th class="p-3">Tempo Decorrido (SLA)</th>
              <th class="p-3">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-sm">
            <tr v-for="exame in exames" :key="exame.codigo_sap" class="hover:bg-slate-50 transition">
              <td class="p-3">
                <span class="font-mono font-extrabold text-blue-900 text-base block">
                  {{ exame.codigo_sap }}
                </span>
                <span class="text-xs text-slate-500 font-medium">
                  Solicitação AGHU: <strong>{{ exame.codigo_solicitacao }}</strong>
                </span>
              </td>

              <td class="p-3">
                <span class="font-bold text-slate-800">{{ exame.nome_paciente }}</span>
                <span class="block text-xs text-slate-500">Prontuário: {{ exame.prontuario_paciente || 'Externo' }}</span>
              </td>

              <td class="p-3 max-w-xs">
                <div class="flex flex-wrap items-center gap-1 mb-1">
                  <span class="px-2 py-0.5 bg-blue-100 text-blue-900 text-xs font-bold rounded">
                    {{ exame.tipo_exame }} ({{ exame.sigla_exame }})
                  </span>
                  <span v-if="exame.suspeita_neoplasia" class="px-2 py-0.5 bg-rose-100 text-rose-800 text-xs font-bold rounded">
                    Onco
                  </span>
                  <span class="px-2 py-0.5 bg-slate-200 text-slate-700 text-xs font-semibold rounded">
                    {{ exame.quantidade_amostras }} amostra(s)
                  </span>
                </div>
                <span class="block text-xs text-slate-600 truncate" :title="exame.descricao_material">
                  <strong>Material:</strong> {{ exame.descricao_material }}
                </span>
              </td>

              <td class="p-3 text-xs text-slate-600">
                {{ exame.origem }}
              </td>

              <td class="p-3">
                <span class="px-2.5 py-1 text-xs font-semibold rounded-full" 
                      :class="exame.etapa_atual.includes('Concluído') ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'">
                  {{ exame.etapa_atual }}
                </span>
              </td>

              <td class="p-3 text-xs">
                <div class="font-bold" :class="exame.dias_decorridos >= 15 ? 'text-rose-600' : 'text-slate-800'">
                  ⏱️ {{ exame.dias_decorridos }}º dia corrido <span class="font-normal text-slate-500">(Meta: {{ exame.meta_dias_limite }}d)</span>
                </div>
                <div v-if="exame.suspeita_neoplasia" class="text-purple-700 font-semibold mt-0.5">
                  🎗️ Onco: {{ exame.dias_decorridos }}º dia <span class="font-normal text-slate-500">(Lei: {{ exame.lei_onco_limite }}d)</span>
                </div>
              </td>

              <td class="p-3">
                <button 
                  @click="abrirDetalhes(exame)" 
                  class="text-xs bg-slate-200 hover:bg-slate-300 text-slate-800 font-medium px-3 py-1.5 rounded transition">
                  Visualizar Histórico
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- MODAL: DETALHES E AUDITORIA DO EXAME -->
    <div v-if="exameSelecionado" class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-start mb-4">
          <div>
            <h3 class="text-xl font-bold text-blue-900">
              Exame {{ exameSelecionado.codigo_sap }} (Solicitação AGHU #{{ exameSelecionado.codigo_solicitacao }})
            </h3>
            <p class="text-sm text-slate-600">
              Paciente: <strong>{{ exameSelecionado.nome_paciente }}</strong> | Quantidade de Amostras: <strong>{{ exameSelecionado.quantidade_amostras }}</strong>
            </p>
          </div>
          <button @click="exameSelecionado = null" class="text-slate-400 hover:text-slate-700 text-xl font-bold">✕</button>
        </div>

        <div class="space-y-4">
          <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-1.5">
            <p><strong>Tipo de Exame:</strong> {{ exameSelecionado.tipo_exame }} ({{ exameSelecionado.sigla_exame }})</p>
            <p><strong>Material Analisado:</strong> {{ exameSelecionado.descricao_material }}</p>
            <p><strong>QR Code de Rastreabilidade:</strong> <code class="bg-slate-200 px-1.5 py-0.5 rounded font-mono">{{ exameSelecionado.qr_code }}</code></p>
            <p><strong>Laudo Macroscópico:</strong> {{ exameSelecionado.laudo_macroscopico_formal }}</p>
            <p><strong>Status AGHU:</strong> {{ exameSelecionado.laudo_final_aghu }}</p>
          </div>

          <h4 class="font-bold text-slate-700 text-sm">Trilha de Auditoria e Histórico do Exame</h4>
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

        <div class="mt-6 flex justify-end">
          <button @click="exameSelecionado = null" class="bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-800">
            Fechar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const kpis = ref<any>({})
const exames = ref<any[]>([])
const exameSelecionado = ref<any>(null)

const carregarDados = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/sap/exames')
    kpis.value = res.data.kpis
    exames.value = res.data.exames
  } catch (err) {
    console.error('Erro ao carregar dados do SAP:', err)
  }
}

const abrirDetalhes = (exame: any) => {
  exameSelecionado.value = exame
}

onMounted(() => {
  carregarDados()
})
</script>