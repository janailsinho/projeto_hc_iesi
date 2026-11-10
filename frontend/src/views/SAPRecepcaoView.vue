<template>
  <div class="min-h-screen bg-slate-50 p-6">
    <!-- Cabeçalho da Tela de Recepção (Sem a faixa verde superior) -->
    <header class="mb-6 flex flex-col justify-between gap-4 lg:flex-row lg:items-center bg-white p-5 rounded-xl shadow-sm border border-slate-200">
      <div>
        <h1 class="text-2xl md:text-3xl font-extrabold text-blue-900 tracking-tight">
          Recepção e Triagem de Amostras
        </h1>
        <p class="text-sm text-slate-600 mt-1">
          Consulta por número de solicitação do AGHU, conferência física de frascos e geração do código SAP
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <!-- Simulador de Perfil de Acesso (RBAC) -->
        <div class="bg-slate-100 px-3 py-2 rounded-lg border border-slate-300 flex items-center gap-2">
          <span class="text-xs font-bold uppercase text-slate-500">Perfil Ativo:</span>
          <select v-model="perfilAtivo" class="bg-transparent text-xs font-bold text-blue-900 focus:outline-none cursor-pointer">
            <option value="Recepção SAP">Recepção SAP (Triagem)</option>
            <option value="Técnico de Laboratório">Técnico de Laboratório</option>
            <option value="Médico Residente / Patologista">Médico Residente / Patologista</option>
            <option value="Chefia SAP / Admin">Chefia SAP / Admin</option>
          </select>
        </div>

        <router-link 
          to="/sap" 
          class="bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold px-4 py-2 rounded-lg transition text-sm">
          ← Voltar ao Painel SAP
        </router-link>
      </div>
    </header>

    <!-- Alerta de Restrição de Perfil (RBAC) -->
    <div v-if="perfilAtivo !== 'Recepção SAP' && perfilAtivo !== 'Chefia SAP / Admin'" class="mb-6 p-4 bg-rose-50 border-l-4 border-rose-600 text-rose-900 rounded-lg text-sm shadow-sm">
      ⚠️ <strong>Controle de Acesso por Perfil (RBAC):</strong> O perfil selecionado (<strong>{{ perfilAtivo }}</strong>) possui acesso apenas para visualização. Para validar frascos e gerar o código de entrada no SAP, altere o perfil no topo para <strong>Recepção SAP</strong> ou <strong>Chefia SAP / Admin</strong>.
    </div>

    <!-- Bloco 1: Busca da Solicitação no AGHU (CSV) -->
    <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-6">
      <label class="block text-xs font-bold uppercase text-slate-700 mb-2">
        1. Consultar Número da Solicitação AGHU:
      </label>
      <div class="flex flex-col sm:flex-row gap-3">
        <input 
          v-model="inputCodigoSolicitacao" 
          @keyup.enter="consultarSolicitacaoCSV"
          type="text" 
          placeholder="Digite o nº da solicitação (Ex: 1479377, 1479445, 1479341, 1479326)..." 
          class="flex-1 border border-slate-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600"
        />
        <button 
          @click="consultarSolicitacaoCSV" 
          class="bg-blue-700 hover:bg-blue-800 text-white font-semibold px-6 py-2.5 rounded-lg text-sm shadow transition">
          🔍 Buscar Solicitação no AGHU
        </button>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        <span>💡 <strong>Códigos reais da planilha CSV para teste rápido:</strong></span>
        <button @click="testarCodigo('1479445')" class="px-2.5 py-1 bg-slate-100 hover:bg-blue-50 text-blue-800 rounded border border-slate-300 font-mono font-semibold">1479445 (1 amostra - HP)</button>
        <button @click="testarCodigo('1479341')" class="px-2.5 py-1 bg-slate-100 hover:bg-blue-50 text-blue-800 rounded border border-slate-300 font-mono font-semibold">1479341 (2 amostras - HP)</button>
        <button @click="testarCodigo('1479326')" class="px-2.5 py-1 bg-slate-100 hover:bg-blue-50 text-blue-800 rounded border border-slate-300 font-mono font-semibold">1479326 (Colonoscopia)</button>
        <button @click="testarCodigo('1479297')" class="px-2.5 py-1 bg-slate-100 hover:bg-blue-50 text-blue-800 rounded border border-slate-300 font-mono font-semibold">1479297 (IHQ)</button>
      </div>
    </div>

    <!-- Alertas de Erro ou Confirmação -->
    <div v-if="erroRecebimento" class="mb-6 p-4 bg-rose-100 border-l-4 border-rose-600 text-rose-800 text-sm rounded-lg">
      {{ erroRecebimento }}
    </div>

    <div v-if="exameRecemGerado" class="mb-6 p-5 bg-emerald-50 border-2 border-emerald-500 text-emerald-950 rounded-xl shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <span class="text-xs font-extrabold uppercase bg-emerald-200 text-emerald-900 px-2 py-0.5 rounded">Recebimento Concluído</span>
        <h3 class="text-lg font-extrabold mt-1">
          Código SAP Gerado: <span class="font-mono text-blue-900">{{ exameRecemGerado.codigo_sap }}</span>
        </h3>
        <p class="text-xs text-slate-700 mt-0.5">
          QR Code de Rastreabilidade: <code class="bg-white px-2 py-0.5 rounded border font-mono">{{ exameRecemGerado.qr_code }}</code> • Solicitação AGHU #{{ exameRecemGerado.codigo_solicitacao }}
        </p>
      </div>
      <router-link 
        to="/sap" 
        class="bg-emerald-700 hover:bg-emerald-800 text-white font-bold px-4 py-2 rounded-lg text-xs shadow transition">
        Ver na Fila do Painel SAP →
      </router-link>
    </div>

    <!-- Bloco 2: Resultado da Consulta e Checklist de Validação Física -->
    <div v-if="solicitacaoEncontrada" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Coluna Esquerda: Dados do Paciente e da Solicitação AGHU -->
      <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4">
        <div class="flex justify-between items-center border-b border-slate-100 pb-3">
          <h2 class="text-base font-bold text-slate-800">2. Dados da Solicitação AGHU</h2>
          <span class="font-mono font-bold text-blue-800 bg-blue-50 px-2.5 py-1 rounded text-xs">
            #{{ solicitacaoEncontrada.codigo_solicitacao }}
          </span>
        </div>

        <div class="space-y-3 text-xs">
          <div>
            <span class="text-slate-400 uppercase font-semibold block">Paciente / Prontuário</span>
            <p class="text-sm font-bold text-slate-800 mt-0.5">{{ solicitacaoEncontrada.nome_paciente }}</p>
            <p class="text-slate-600">Prontuário: <strong>{{ solicitacaoEncontrada.prontuario }}</strong> • Nasc: {{ solicitacaoEncontrada.data_nascimento }}</p>
          </div>

          <div>
            <span class="text-slate-400 uppercase font-semibold block">Data da Solicitação</span>
            <p class="font-semibold text-slate-700 mt-0.5">{{ solicitacaoEncontrada.data_solicitacao }}</p>
          </div>

          <div>
            <span class="text-slate-400 uppercase font-semibold block">Origem / Unidade / Especialidade</span>
            <p class="font-semibold text-slate-700 mt-0.5">
              {{ solicitacaoEncontrada.origem }} — {{ solicitacaoEncontrada.unidade }} ({{ solicitacaoEncontrada.especialidade }})
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
              <span class="text-[11px] uppercase font-bold text-blue-800 block">Total de Amostras na Solicitação</span>
              <span class="text-xs text-slate-600">Prefixo SAP: <strong>{{ solicitacaoEncontrada.prefixo_sugerido }}</strong></span>
            </div>
            <span class="text-3xl font-extrabold text-blue-900">{{ solicitacaoEncontrada.total_amostras }}</span>
          </div>
        </div>
      </div>

      <!-- Coluna Direita (2/3): Checklist de Frascos e Validação de Entrada -->
      <div class="lg:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between space-y-6">
        <div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-3 mb-4 gap-2">
            <div>
              <h2 class="text-base font-bold text-slate-800">
                3. Validação Física de Amostras ({{ amostrasMarcadas.length }} de {{ solicitacaoEncontrada.total_amostras }} conferidas)
              </h2>
              <p class="text-xs text-slate-500">Confira cada frasco físico recebido antes de gerar o protocolo do SAP</p>
            </div>
            <button 
              @click="marcarTodasAmostras" 
              type="button"
              class="text-xs bg-blue-50 hover:bg-blue-100 text-blue-800 font-bold px-3 py-1.5 rounded-lg border border-blue-200 transition">
              ☑️ Marcar Todas as Amostras
            </button>
          </div>

          <!-- Lista de Amostras / Frascos do CSV -->
          <div class="space-y-2.5 max-h-80 overflow-y-auto pr-1">
            <label 
              v-for="item in solicitacaoEncontrada.amostras" 
              :key="item.numero_amostra"
              class="flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition text-xs"
              :class="amostrasMarcadas.includes(item.numero_amostra) ? 'bg-emerald-50/80 border-emerald-500 shadow-sm' : 'bg-slate-50 border-slate-200 hover:bg-slate-100'">
              <input 
                type="checkbox" 
                :value="item.numero_amostra" 
                v-model="amostrasMarcadas"
                class="mt-0.5 h-4 w-4 text-emerald-600 rounded"
              />
              <div class="flex-1">
                <div class="flex flex-wrap justify-between gap-2">
                  <span class="font-bold text-slate-900 text-sm">
                    Frasco / Amostra #{{ item.numero_amostra }} — {{ item.nome_exame }} ({{ item.sigla_exame }})
                  </span>
                  <span class="px-2 py-0.5 bg-slate-200 text-slate-700 rounded text-[10px] font-bold uppercase">
                    Status AGHU: {{ item.status_item_exame }}
                  </span>
                </div>
                <p class="text-slate-700 mt-1">
                  <strong>Material Anatômico:</strong> {{ item.descricao_material }}
                </p>
              </div>
            </label>
          </div>
        </div>

        <!-- Parâmetros de Triagem e Botão de Confirmação -->
        <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-4 text-xs">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block font-bold text-slate-700 mb-1">Condição / Estágio Físico na Entrada:</label>
              <select v-model="estagioEntrada" class="w-full border border-slate-300 rounded-lg px-3 py-2 bg-white">
                <option value="Peça a Fresco / Formol (Para Macroscopia)">Peça a Fresco / Formol (Segue para Macroscopia)</option>
                <option value="Bloco de Parafina Externo (Para Recorte/IHQ)">Bloco de Parafina (Segue para Processamento Técnico)</option>
                <option value="Lâmina Pronta (Para Revisão/Microscopia)">Lâmina Pronta (Segue para Microscopia)</option>
              </select>
            </div>
            <div>
              <label class="block font-bold text-slate-700 mb-1">Observações da Triagem (Opcional):</label>
              <input 
                v-model="observacaoRecepcao" 
                type="text" 
                placeholder="Ex: Frascos íntegros e identificados..."
                class="w-full border border-slate-300 rounded-lg px-3 py-2 bg-white"
              />
            </div>
          </div>

          <div class="flex items-center gap-2 pt-1">
            <input type="checkbox" id="checkOncoPage" v-model="flagNeoplasia" class="h-4 w-4 text-rose-600 rounded" />
            <label for="checkOncoPage" class="font-bold text-rose-800 cursor-pointer">
              Sinalizar Prioridade Oncológica (Ativar monitoramento da Lei Federal dos 60 Dias)
            </label>
          </div>

          <div class="flex justify-end pt-2 border-t border-slate-200">
            <button 
              @click="confirmarRecebimento"
              :disabled="(perfilAtivo !== 'Recepção SAP' && perfilAtivo !== 'Chefia SAP / Admin') || solicitacaoEncontrada.ja_recebida"
              class="w-full sm:w-auto px-6 py-3 rounded-xl text-white text-sm font-bold shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed bg-emerald-600 hover:bg-emerald-700">
              ✅ Confirmar Recebimento ({{ amostrasMarcadas.length }}/{{ solicitacaoEncontrada.total_amostras }}) e Gerar Código {{ solicitacaoEncontrada.prefixo_sugerido }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'

const perfilAtivo = ref<string>('Recepção SAP')
const inputCodigoSolicitacao = ref<string>('')
const solicitacaoEncontrada = ref<any>(null)
const amostrasMarcadas = ref<number[]>([])
const estagioEntrada = ref<string>('Peça a Fresco / Formol (Para Macroscopia)')
const observacaoRecepcao = ref<string>('')
const flagNeoplasia = ref<boolean>(false)
const erroRecebimento = ref<string>('')
const exameRecemGerado = ref<any>(null)

const testarCodigo = (codigo: string) => {
  inputCodigoSolicitacao.value = codigo
  consultarSolicitacaoCSV()
}

const consultarSolicitacaoCSV = async () => {
  erroRecebimento.value = ''
  exameRecemGerado.value = null
  solicitacaoEncontrada.value = null
  amostrasMarcadas.value = []

  if (!inputCodigoSolicitacao.value.trim()) {
    erroRecebimento.value = 'Digite um número de solicitação válido.'
    return
  }

  try {
    const res = await axios.get(`http://localhost:8000/api/sap/solicitacao/${inputCodigoSolicitacao.value.trim()}`)
    solicitacaoEncontrada.value = res.data
    flagNeoplasia.value = res.data.suspeita_neoplasia_sugerida
  } catch (err: any) {
    erroRecebimento.value = err.response?.data?.detail || 'Erro ao consultar solicitação no CSV do AGHU.'
  }
}

const marcarTodasAmostras = () => {
  if (solicitacaoEncontrada.value) {
    amostrasMarcadas.value = solicitacaoEncontrada.value.amostras.map((a: any) => a.numero_amostra)
  }
}

const confirmarRecebimento = async () => {
  erroRecebimento.value = ''
  exameRecemGerado.value = null

  if (!solicitacaoEncontrada.value) return

  try {
    const payload = {
      codigo_solicitacao: solicitacaoEncontrada.value.codigo_solicitacao,
      amostras_conferidas: amostrasMarcadas.value,
      estagio_entrada: estagioEntrada.value,
      suspeita_neoplasia: flagNeoplasia.value,
      observacao_recepcao: observacaoRecepcao.value,
      perfil_usuario: perfilAtivo.value,
      operador: 'admin (HC-UFPE)'
    }
    const res = await axios.post('http://localhost:8000/api/sap/receber', payload)
    exameRecemGerado.value = res.data.exame
    solicitacaoEncontrada.value.ja_recebida = true
  } catch (err: any) {
    erroRecebimento.value = err.response?.data?.detail || 'Falha ao registrar o recebimento da amostra.'
  }
}
</script>