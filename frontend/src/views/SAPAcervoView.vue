<template>
  <div class="min-h-screen bg-slate-50 p-6 space-y-6">
    <!-- Cabeçalho -->
    <header class="flex flex-col justify-between gap-4 lg:flex-row lg:items-center bg-white p-5 rounded-xl shadow-sm border border-slate-200">
      <div>
        <h1 class="text-2xl md:text-3xl font-extrabold text-blue-900 tracking-tight">
          Rastreabilidade QR Code, Acervo Científico e Impressoras Térmicas
        </h1>
        <p class="text-sm text-slate-600 mt-1">
          Visão Unificada em tempo real (RF040–RF043), Pesquisa Científica com Exportação CSV (RF044–RF050) e Estações Zebra/Argox (RF054–RF055)
        </p>
      </div>
    </header>

    <!-- Abas -->
    <div class="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
      <button
        @click="aba = 'ACERVO'"
        :class="aba === 'ACERVO' ? 'bg-blue-800 text-white shadow' : 'bg-white text-slate-700 border border-slate-300'"
        class="px-4 py-2.5 rounded-xl font-bold text-xs transition">
        🔎 1.7 Busca e Pesquisa no Acervo Científico (RF044–RF050)
      </button>
      <button
        @click="aba = 'RASTREIO'"
        :class="aba === 'RASTREIO' ? 'bg-indigo-800 text-white shadow' : 'bg-white text-slate-700 border border-slate-300'"
        class="px-4 py-2.5 rounded-xl font-bold text-xs transition">
        📡 1.6 Visão Unificada por Leitura de QR Code (RF040–RF043)
      </button>
      <button
        @click="aba = 'IMPRESSORAS'; carregarImpressoras()"
        :class="aba === 'IMPRESSORAS' ? 'bg-slate-800 text-white shadow' : 'bg-white text-slate-700 border border-slate-300'"
        class="px-4 py-2.5 rounded-xl font-bold text-xs transition">
        🖨️ 1.9 Configuração de Impressoras Térmicas Zebra/Argox (RF054–RF055)
      </button>
    </div>

    <!-- ======================================================================= -->
    <!-- ABA 1: BUSCA E PESQUISA NO ACERVO CIENTÍFICO (RF044 a RF050)            -->
    <!-- ======================================================================= -->
    <div v-if="aba === 'ACERVO'" class="space-y-6">
      <form @submit.prevent="executarBuscaAcervo" class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-4 text-xs">
        <div class="flex flex-wrap justify-between items-center border-b pb-3 gap-2">
          <h2 class="text-base font-bold text-slate-800">Filtros Combinados de Pesquisa no Acervo Patológico</h2>
          <div class="flex gap-2">
            <button
              type="button"
              @click="limparFiltros"
              class="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold">
              Limpar Filtros
            </button>
            <button
              type="button"
              @click="exportarCSV"
              class="px-4 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-bold shadow">
              📥 Exportar Resultados CSV para Pesquisa Científica (RF050)
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label class="font-bold text-slate-700 block mb-1">Nº Solicitação / Código SAP (RF044):</label>
            <input v-model="filtros.numero_solicitacao" type="text" placeholder="Ex: 1479367 ou HP-2026-001" class="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Paciente: Nome, CPF, CNS ou Prontuário (RF045):</label>
            <input v-model="filtros.paciente" type="text" placeholder="Ex: 17450396 ou L.C.B.S." class="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Tipo de Peça Patológica (RF047):</label>
            <input v-model="filtros.tipo_peca" type="text" placeholder="Ex: Mama, Próstata, Colo Uterino, Parótida..." class="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Modalidade de Exame:</label>
            <select v-model="filtros.sigla_exame" class="w-full border rounded-lg px-3 py-2 bg-white">
              <option value="">Todas (HP, CO, IHQ, CG, CCV)</option>
              <option value="HP">HP — Histopatológico</option>
              <option value="CO">CO — Congelação</option>
              <option value="IHQ">IHQ — Imuno-histoquímica</option>
              <option value="CG">CG — Citopatologia Geral</option>
              <option value="CCV">CCV — Citologia Cérvico-Vaginal</option>
            </select>
          </div>

          <div>
            <label class="font-bold text-slate-700 block mb-1">Diagnóstico Associado / Clínica (RF048):</label>
            <input v-model="filtros.diagnostico" type="text" placeholder="Ex: Neoplasia, Carcinoma, Adenocarcinoma..." class="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Marcador IHQ / Complemento (RF049):</label>
            <input v-model="filtros.marcador_complemento" type="text" placeholder="Ex: IHQ, Ki-67, HER2, RE, RP, CD20..." class="w-full border rounded-lg px-3 py-2" />
          </div>
          <div>
            <label class="font-bold text-slate-700 block mb-1">Tipo de Período (RF046):</label>
            <select v-model="filtros.tipo_data" class="w-full border rounded-lg px-3 py-2 bg-white">
              <option value="solicitacao">Data da Solicitação</option>
              <option value="recebimento">Data de Recebimento</option>
              <option value="macroscopia">Data da Macroscopia</option>
              <option value="liberacao">Data de Liberação</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="font-bold text-slate-700 block mb-1">De:</label>
              <input v-model="filtros.data_inicio" type="date" class="w-full border rounded-lg px-2 py-2" />
            </div>
            <div>
              <label class="font-bold text-slate-700 block mb-1">Até:</label>
              <input v-model="filtros.data_fim" type="date" class="w-full border rounded-lg px-2 py-2" />
            </div>
          </div>
        </div>

        <div class="flex justify-end">
          <button type="submit" class="bg-blue-700 hover:bg-blue-800 text-white font-bold px-6 py-2.5 rounded-xl shadow">
            🔍 Pesquisar no Acervo ({{ totalAcervo }} registro[s] encontrado[s])
          </button>
        </div>
      </form>

      <!-- Tabela de Resultados do Acervo -->
      <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="bg-slate-100 text-slate-700 uppercase">
                <th class="p-3">Código SAP / Solicitação</th>
                <th class="p-3">Paciente / Prontuário</th>
                <th class="p-3">Tipo de Peça & Material</th>
                <th class="p-3">Diagnóstico / Clínica</th>
                <th class="p-3">Etapa / Datas</th>
                <th class="p-3">Ação</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200">
              <tr v-for="item in resultadosAcervo" :key="`${item.codigo_sap}-${item.codigo_solicitacao}`" class="hover:bg-slate-50">
                <td class="p-3">
                  <span class="font-mono font-extrabold text-blue-900 block">{{ item.codigo_sap }}</span>
                  <span class="text-slate-500">Solicitação #{{ item.codigo_solicitacao }}</span>
                </td>
                <td class="p-3">
                  <span class="font-bold text-slate-800 block">{{ item.nome_paciente }}</span>
                  <span class="text-slate-500">Pront: {{ item.prontuario_paciente || 'SUS' }}</span>
                </td>
                <td class="p-3 max-w-xs">
                  <span class="font-semibold text-indigo-900 block">{{ item.tipo_peca }} ({{ item.sigla_exame }})</span>
                  <span class="text-slate-600 truncate block">{{ item.descricao_material }}</span>
                </td>
                <td class="p-3 max-w-xs">
                  <span class="text-slate-700 line-clamp-2">{{ item.diagnostico_associado || 'Em investigação / Ver dados clínicos' }}</span>
                </td>
                <td class="p-3">
                  <span class="font-bold text-emerald-800 block">{{ item.etapa_atual }}</span>
                  <span class="text-slate-500">Sol: {{ item.data_solicitacao }}</span>
                </td>
                <td class="p-3">
                  <button
                    @click="abrirRastreioDireto(item.recebido_no_sap ? item.codigo_sap : item.codigo_solicitacao)"
                    class="bg-blue-50 hover:bg-blue-100 text-blue-900 border border-blue-200 font-bold px-3 py-1 rounded">
                    Ver Visão Unificada
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- ABA 2: VISÃO UNIFICADA POR LEITURA DE QR CODE (RF040 a RF043)           -->
    <!-- ======================================================================= -->
    <div v-if="aba === 'RASTREIO'" class="space-y-6">
      <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-3">
        <label class="block text-xs font-bold uppercase text-slate-700">
          Escaneie o QR Code de qualquer Subproduto (Frasco, Cassete, Bloco, Lâmina) ou digite Nº Solicitação / CPF / CNS:
        </label>
        <div class="flex gap-3">
          <input
            v-model="termoRastreio"
            @keyup.enter="consultarRastreio"
            type="text"
            placeholder="Ex: 1479367, HP-2026-001, CAS-..., BLK-..., LAM-..."
            class="flex-1 border border-slate-300 rounded-lg px-4 py-2.5 text-sm"
          />
          <button
            @click="consultarRastreio"
            class="bg-indigo-700 hover:bg-indigo-800 text-white font-bold px-6 py-2.5 rounded-lg text-sm shadow">
            📡 Consultar Status e Árvore Completa
          </button>
        </div>
      </div>

      <div v-if="exameRastreado" class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-5 text-xs">
        <div class="flex flex-wrap justify-between items-center border-b pb-4 gap-3">
          <div>
            <span class="text-xs font-bold uppercase text-indigo-700">Visão Unificada Tempo Real (AGHU + SISPATO)</span>
            <h2 class="text-xl font-extrabold text-blue-900 mt-0.5">
              {{ exameRastreado.codigo_sap }} — Paciente: {{ exameRastreado.nome_paciente }} (Pront: {{ exameRastreado.prontuario_paciente }})
            </h2>
          </div>
          <span class="px-4 py-1.5 rounded-full bg-emerald-100 text-emerald-900 font-extrabold text-sm">
            Etapa Atual: {{ exameRastreado.etapa_atual }}
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 p-4 rounded-xl border">
          <div>
            <strong class="text-slate-500 block">Solicitação AGHU / Origem:</strong>
            <p class="font-bold text-slate-800">#{{ exameRastreado.codigo_solicitacao }} — {{ exameRastreado.origem }}</p>
          </div>
          <div>
            <strong class="text-slate-500 block">Status de Pré-Laudo (Orientação ao Paciente):</strong>
            <p class="font-bold text-blue-900">{{ exameRastreado.status_pre_laudo }}</p>
          </div>
          <div>
            <strong class="text-slate-500 block">Subprodutos Gerados:</strong>
            <p class="font-bold text-slate-800">
              {{ exameRastreado.quantidade_amostras }} Frasco(s) • {{ exameRastreado.quantidade_cassetes }} Cassete(s) • {{ exameRastreado.quantidade_blocos }} Bloco(s) • {{ exameRastreado.quantidade_laminas }} Lâmina(s)
            </p>
          </div>
        </div>

        <div>
          <h3 class="font-bold text-slate-800 text-sm mb-2">🌳 Árvore Hierárquica de Rastreabilidade</h3>
          <div class="space-y-2">
            <div v-for="f in exameRastreado.arvore_subprodutos" :key="f.qr_code" class="p-3 bg-slate-50 rounded-xl border">
              <p class="font-bold text-slate-900">🧪 Frasco #{{ f.numero_amostra }} ({{ f.qr_code }}): {{ f.descricao_material }} — [{{ f.status_frasco }}]</p>
              <div v-for="c in f.cassetes" :key="c.qr_code" class="mt-1.5 pl-4 border-l-2 border-blue-400">
                <p class="font-semibold text-indigo-900">🗂️ Cassete {{ c.codigo_cassete }} — {{ c.status_cassete }}</p>
                <div v-for="b in c.blocos" :key="b.qr_code" class="pl-4 border-l-2 border-amber-400">
                  <p class="font-semibold text-amber-900">🧊 Bloco {{ b.codigo_bloco }} {{ b.arquivado ? `(Arquivado: ${b.local_arquivo})` : '' }}</p>
                  <div v-for="l in b.laminas" :key="l.qr_code" class="pl-4 border-l-2 border-emerald-500 text-emerald-900">
                    🔬 Lâmina {{ l.codigo_lamina }} ({{ l.tipo_coloracao }}) — {{ l.status_lamina }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div>
          <h3 class="font-bold text-slate-800 text-sm mb-2">📜 Histórico Completo de Movimentação (RF040)</h3>
          <div class="space-y-2">
            <div v-for="(h, i) in exameRastreado.historico" :key="i" class="p-3 bg-blue-50 border-l-4 border-blue-600 rounded">
              <div class="flex justify-between font-bold text-blue-900">
                <span>{{ h.etapa }} ({{ h.perfil }})</span>
                <span>{{ h.timestamp }}</span>
              </div>
              <p class="text-slate-700 mt-0.5">{{ h.acao }} — <strong>Operador: {{ h.operador }}</strong></p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ======================================================================= -->
    <!-- ABA 3: CONFIGURAÇÃO DE IMPRESSORAS TÉRMICAS POR ESTAÇÃO (RF054, RF055)  -->
    <!-- ======================================================================= -->
    <div v-if="aba === 'IMPRESSORAS'" class="space-y-4">
      <div v-if="msgImpressora" class="p-3 bg-emerald-100 border-l-4 border-emerald-600 text-emerald-900 text-xs font-bold rounded">
        ✅ {{ msgImpressora }}
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div
          v-for="imp in impressoras"
          :key="imp.id"
          class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-3 text-xs"
        >
          <div class="flex justify-between items-center border-b pb-2">
            <h3 class="text-base font-extrabold text-blue-900">🖨️ Estação: {{ imp.estacao }}</h3>
            <span class="px-2.5 py-0.5 bg-emerald-100 text-emerald-800 rounded font-bold">{{ imp.linguagem }} ({{ imp.dpi }} DPI)</span>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="font-bold text-slate-700 block mb-1">Nome na Rede / Fila CUPS:</label>
              <input v-model="imp.nome_impressora" type="text" class="w-full border rounded px-2.5 py-1.5" />
            </div>
            <div>
              <label class="font-bold text-slate-700 block mb-1">Fabricante / Modelo Térmico:</label>
              <input v-model="imp.fabricante_modelo" type="text" class="w-full border rounded px-2.5 py-1.5" />
            </div>
            <div>
              <label class="font-bold text-slate-700 block mb-1">Endereço IP / Porta RAW (Zebra/Argox):</label>
              <input v-model="imp.endereco_conexao" type="text" class="w-full border rounded px-2.5 py-1.5 font-mono" />
            </div>
            <div>
              <label class="font-bold text-slate-700 block mb-1">Insumo / Etiqueta Resistente:</label>
              <input v-model="imp.tamanho_etiqueta" type="text" class="w-full border rounded px-2.5 py-1.5" />
            </div>
          </div>

          <div class="flex justify-between items-center pt-2">
            <label class="flex items-center gap-2 font-semibold text-slate-700 cursor-pointer">
              <input type="checkbox" v-model="imp.impressao_automatica" class="rounded text-blue-600" />
              Disparar impressão automática ao gerar código na bancada
            </label>
            <button
              @click="salvarImpressora(imp)"
              class="bg-blue-700 hover:bg-blue-800 text-white font-bold px-4 py-1.5 rounded-lg">
              Salvar Estação
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../services/api'

const aba = ref<'ACERVO' | 'RASTREIO' | 'IMPRESSORAS'>('ACERVO')
const resultadosAcervo = ref<any[]>([])
const totalAcervo = ref(0)
const termoRastreio = ref('1479367')
const exameRastreado = ref<any>(null)
const impressoras = ref<any[]>([])
const msgImpressora = ref('')

const filtros = ref({
  numero_solicitacao: '',
  paciente: '',
  tipo_peca: '',
  sigla_exame: '',
  diagnostico: '',
  marcador_complemento: '',
  tipo_data: 'solicitacao',
  data_inicio: '',
  data_fim: ''
})

const executarBuscaAcervo = async () => {
  const res = await api.get('/api/sap/acervo', {
    params: {
      numero_solicitacao: filtros.value.numero_solicitacao || undefined,
      paciente: filtros.value.paciente || undefined,
      tipo_peca: filtros.value.tipo_peca || undefined,
      sigla_exame: filtros.value.sigla_exame || undefined,
      diagnostico: filtros.value.diagnostico || undefined,
      marcador_complemento: filtros.value.marcador_complemento || undefined,
      tipo_data: filtros.value.tipo_data,
      data_inicio: filtros.value.data_inicio || undefined,
      data_fim: filtros.value.data_fim || undefined,
      limite: 100
    }
  })
  resultadosAcervo.value = res.data.resultados
  totalAcervo.value = res.data.total_encontrado
}

const limparFiltros = () => {
  filtros.value = {
    numero_solicitacao: '',
    paciente: '',
    tipo_peca: '',
    sigla_exame: '',
    diagnostico: '',
    marcador_complemento: '',
    tipo_data: 'solicitacao',
    data_inicio: '',
    data_fim: ''
  }
  executarBuscaAcervo()
}

const exportarCSV = () => {
  const params = new URLSearchParams()
  Object.entries(filtros.value).forEach(([k, v]) => {
    if (v) params.append(k, String(v))
  })
  const base = api.defaults.baseURL || ''
  window.open(`${base}/api/sap/acervo/exportar-csv?${params.toString()}`, '_blank')
}

const consultarRastreio = async () => {
  if (!termoRastreio.value.trim()) return
  const res = await api.get(`/api/sap/rastreabilidade/${encodeURIComponent(termoRastreio.value.trim())}`)
  exameRastreado.value = res.data.exame
}

const abrirRastreioDireto = async (codigo: string) => {
  termoRastreio.value = codigo
  aba.value = 'RASTREIO'
  await consultarRastreio()
}

const carregarImpressoras = async () => {
  const res = await api.get('/api/sap/impressoras')
  impressoras.value = res.data.impressoras
}

const salvarImpressora = async (imp: any) => {
  msgImpressora.value = ''
  const res = await api.put(`/api/sap/impressoras/${imp.id}`, imp)
  msgImpressora.value = res.data.mensagem
}

onMounted(() => {
  executarBuscaAcervo()
  carregarImpressoras()
})
</script>
