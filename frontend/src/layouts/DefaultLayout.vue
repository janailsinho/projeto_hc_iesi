<template>
  <div class="flex h-screen bg-slate-100 font-sans overflow-hidden">
    <!-- Menu Lateral Esquerdo Único -->
    <aside
      :class="[
        'bg-neutral-900 text-white transition-all duration-300 flex flex-col justify-between z-20 shadow-xl',
        isSidebarOpen ? 'w-64' : 'w-20'
      ]"
    >
      <div>
        <div class="flex items-center gap-3 p-4 border-b border-neutral-800">
          <button
            @click="toggleSidebar"
            class="text-gray-300 hover:text-white focus:outline-none p-1 rounded-lg hover:bg-neutral-800 transition"
            title="Alternar Menu"
          >
            <CubeTransparentIcon class="w-6 h-6" />
          </button>
          <span v-if="isSidebarOpen" class="font-extrabold text-base tracking-wide leading-tight text-emerald-400">
            {{ SYSTEM_TITLE }}
          </span>
        </div>

        <!-- Navegação Principal do SISPATO (Sem o bloco Início) -->
        <nav class="mt-4 px-3 space-y-1.5">
          <router-link
            to="/sap"
            active-class="bg-neutral-800 text-emerald-300 font-semibold"
            class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-emerald-400 hover:bg-neutral-800 hover:text-emerald-300 transition-colors"
          >
            <BeakerIcon class="w-5 h-5 shrink-0" />
            <span v-if="isSidebarOpen" class="text-sm">Painel SAP</span>
          </router-link>

          <router-link
            to="/recepcao"
            active-class="bg-neutral-800 text-emerald-300 font-semibold"
            class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-emerald-400 hover:bg-neutral-800 hover:text-emerald-300 transition-colors"
          >
            <ClipboardDocumentCheckIcon class="w-5 h-5 shrink-0" />
            <span v-if="isSidebarOpen" class="text-sm">Recepção / Triagem</span>
          </router-link>

          <router-link
            to="/componentes"
            active-class="bg-neutral-800 text-white font-semibold"
            class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-300 hover:bg-neutral-800 hover:text-white transition-colors"
          >
            <CubeIcon class="w-5 h-5 shrink-0" />
            <span v-if="isSidebarOpen" class="text-sm">Componentes</span>
          </router-link>

          <router-link
            to="/exemplo"
            active-class="bg-neutral-800 text-white font-semibold"
            class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-300 hover:bg-neutral-800 hover:text-white transition-colors"
          >
            <DocumentTextIcon class="w-5 h-5 shrink-0" />
            <span v-if="isSidebarOpen" class="text-sm">Exemplo</span>
          </router-link>

          <router-link
            to="/configuracoes"
            active-class="bg-neutral-800 text-white font-semibold"
            class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-300 hover:bg-neutral-800 hover:text-white transition-colors"
          >
            <Cog6ToothIcon class="w-5 h-5 shrink-0" />
            <span v-if="isSidebarOpen" class="text-sm">Configurações</span>
          </router-link>
        </nav>
      </div>

      <div v-if="isSidebarOpen" class="p-4 border-t border-neutral-800 text-[11px] text-gray-400">
        <p class="font-semibold text-gray-300">Framework SETISD</p>
        <p>SISPATO v{{ APP_VERSION }} | HC-UFPE</p>
      </div>
    </aside>

    <!-- Conteúdo Principal -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden bg-slate-100">
      <header class="bg-white shadow-sm border-b border-slate-200 h-16 flex items-center justify-between px-6 z-10 shrink-0">
        <h2 class="text-lg font-bold text-slate-800 tracking-tight">
          {{ route.name || 'SISPATO' }}
        </h2>

        <div class="relative">
          <button
            @click="showUserMenu = !showUserMenu"
            class="flex items-center gap-2 text-slate-600 hover:text-slate-900 focus:outline-none"
          >
            <UserCircleIcon class="w-8 h-8 text-slate-600" />
          </button>

          <div
            v-if="showUserMenu"
            class="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl border border-slate-200 py-3 px-4 z-50"
          >
            <div class="flex items-center gap-3 border-b border-slate-100 pb-3 mb-3">
              <UserCircleIcon class="w-10 h-10 text-slate-400" />
              <div>
                <p class="font-bold text-slate-800 text-sm">admin</p>
                <p class="text-xs text-slate-500">Gestor / Preceptor SAP</p>
              </div>
            </div>
            <div class="space-y-1.5 text-xs text-slate-600 mb-3">
              <p><strong class="text-slate-400 uppercase text-[10px] block">Setor</strong> Unidade de Anatomia Patológica</p>
              <p><strong class="text-slate-400 uppercase text-[10px] block">Hospital</strong> HC-UFPE / EBSERH</p>
            </div>
            <button
              @click="logout"
              class="w-full text-left text-xs font-semibold text-rose-600 hover:bg-rose-50 p-2 rounded-lg transition"
            >
              Sair da Conta
            </button>
          </div>
        </div>
      </header>

      <!-- View principal -->
      <main class="flex-1 overflow-y-auto p-6 bg-slate-100">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { SYSTEM_TITLE, APP_VERSION } from '../config/version'
import {
  BeakerIcon,
  ClipboardDocumentCheckIcon,
  CubeIcon,
  DocumentTextIcon,
  Cog6ToothIcon,
  UserCircleIcon,
  CubeTransparentIcon
} from '@heroicons/vue/24/outline'

const route = useRoute()
const router = useRouter()
const isSidebarOpen = ref(true)
const showUserMenu = ref(false)

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}

const logout = () => {
  showUserMenu.value = false
  router.push('/login')
}
</script>