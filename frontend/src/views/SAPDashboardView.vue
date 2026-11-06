<template>
  <div class="min-h-screen bg-slate-50 p-6">
    <!-- Cabeçalho Institucional -->
    <header class="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-center">
      <div>
        <h1 class="text-3xl font-extrabold text-blue-900 tracking-tight">
          HC-UFPE / EBSERH - Serviço de Anatomia Patológica (SAP)
        </h1>
        <p class="text-sm text-slate-600 mt-1">
          Sistema de Gestão Integrada de Amostras, Laudos, Rastreabilidade e SLAs
        </p>
      </div>
      <div class="flex gap-3">
        <button 
          @click="carregarDados" 
          class="bg-blue-700 hover:bg-blue-800 text-white font-medium px-4 py-2 rounded-lg shadow transition flex items-center gap-2">
          🔄 Atualizar Painel
        </button>
      </div>
    </header>

    <!-- Indicadores / KPIs (SLA 20 dias e Lei 60 dias) -->
    <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-blue-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Total no Sistema</span>
        <p class="text-2xl font-bold text-slate-800 mt-1">{{ kpis.total_exames || 0 }}</p>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-amber-500">
        <span class="text-xs font-semibold uppercase text-slate-400">Em Processamento</span>
        <p class="text-2xl font-bold text-amber-600 mt-1">{{ kpis.em_andamento || 0 }}</p>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-rose-600 animate-pulse">
        <span class="text-xs font-semibold uppercase text-slate-400">Alerta Meta 20 Dias</span>
        <p class="text-2xl font-bold text-rose-600 mt-1">{{ kpis.alerta_meta_20_dias || 0 }}</p>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-purple-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Lei 60 Dias (Oncologia)</span>
        <p class="text-2xl font-bold text-purple-700 mt-1">{{ kpis.monitorados_lei_60_dias || 0 }}</p>
      </div>
      <div class="bg-white p-4 rounded-xl shadow border-l-4 border-emerald-600">
        <span class="text-xs font-semibold uppercase text-slate-400">Concluídos e Arquivados</span>
        <p class="text-2xl font-bold text-emerald-600 mt-1">{{ kpis.concluidos || 0 }}</p>
      </div>
    </div>

    <!-- Lista de Exames em Tempo Real -->
    <div class="bg-white rounded-xl shadow p-6">
      <h2 class="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
        <span>📋</span> Fila de Exames por Etapa do Processo
      </h2>

      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-100 text-slate-700 text-xs uppercase tracking-wider">
              <th class="p-3">Protocolo / QR Code</th>
              <th class="p-3">Paciente / Prontuário</th>
              <th class="p-3">Tipo</th>
              <th class="p-3">Origem</th>
              <th class="p-3">Etapa Atual</th>
              <th class="p-3">SLAs (Dias)</th>
              <th class="p-3">Ações</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200 text-sm">
            <tr v-for="exame in exames" :key="exame.codigo_anual" class="hover:bg-slate-50 transition">
              <td class="p-3 font-mono font-bold text-blue-800">
                {{ exame.codigo_anual }}
                <span class="block text-xs text-slate-400 font-normal">{{ exame.requisicao_aghu_id }}</span>
              </td>
              <td class="p-3">
                <span class="font-medium text-slate-800">{{ exame.nome_paciente }}</span>
                <span class="block text-xs text-slate-500">Prontuário: {{ exame.prontuario_paciente || 'Pendente (Prefeitura)' }}</span>
              </td>
              <td class="p-3">
                <span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-bold rounded">
                  {{ exame.tipo_exame }}
                </span>
                <span v-if="exame.suspeita_neoplasia" class="ml-1 px-2 py-1 bg-rose-100 text-rose-800 text-xs font-bold rounded">
                  Onco
                </span>
              </td>
              <td class="p-3 text-xs text-slate-600">
                {{ exame.origem }}
              </td>
              <td class="p-3">
                <span class="px-2.5 py-1 text-xs font-semibold rounded-full" 
                      :class="exame.etapa_atual.includes('ARQUIVADO') || exame.etapa_atual.includes('Concluído') ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'">
                  {{ exame.etapa_atual }}
                </span>
              </td>
              <td class="p-3 text-xs">
                <span class="text-rose-600 font-bold">Meta 20d: {{ exame.meta_20_dias_restantes }}d rest.</span><br/>
                <span class="text-purple-600">Lei 60d: {{ exame.lei_60_dias_restantes }}d rest.</span>
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

    <!-- Modal de Detalhes / Auditoria -->
    <div v-if="exameSelecionado" class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-start mb-4">
          <div>
            <h3 class="text-xl font-bold text-blue-900">Detalhes do Exame: {{ exameSelecionado.codigo_anual }}</h3>
            <p class="text-sm text-slate-600">Paciente: {{ exameSelecionado.nome_paciente }}</p>
          </div>
          <button @click="exameSelecionado = null" class="text-slate-400 hover:text-slate-700 text-xl font-bold">✕</button>
        </div>

        <div class="space-y-4">
          <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-1">
            <p><strong>QR Code Técnico:</strong> <code class="bg-slate-200 px-1 py-0.5 rounded">{{ exameSelecionado.qr_code }}</code></p>
            <p><strong>Laudo Macroscópico:</strong> {{ exameSelecionado.laudo_macroscopico_formal || 'Aguardando clivagem na Macro.' }}</p>
            <p><strong>Laudo AGHU Definitivo:</strong> {{ exameSelecionado.laudo_final_aghu || 'Em andamento nas bancadas.' }}</p>
          </div>

          <h4 class="font-bold text-slate-700 text-sm">Trilha de Auditoria e Histórico do Exame</h4>
          <div class="space-y-2">
            <div v-for="(log, idx) in exameSelecionado.historico" :key="idx" class="p-3 bg-blue-50 border-l-2 border-blue-600 rounded text-xs">
              <div class="flex justify-between font-semibold text-blue-900 mb-1">
                <span>{{ log.etapa }} ({{ log.perfil }})</span>
                <span class="text-slate-500">{{ log.timestamp }}</span>
              </div>
              <p class="text-slate-700">{{ log.acao }}</p>
              <span class="text-slate-400 text-[10px] mt-1 block">Operador: {{ log.operador }}</span>
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
    console.error("Erro ao carregar dados do SAP:", err)
  }
}

const abrirDetalhes = (exame: any) => {
  exameSelecionado.value = exame
}

onMounted(() => {
  carregarDados()
})
</script>