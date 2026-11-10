import { createRouter, createWebHistory } from 'vue-router'
import DefaultLayout from '../layouts/DefaultLayout.vue'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: Login,
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: DefaultLayout,
      children: [
        {
          path: '',
          name: 'Início',
          component: Home,
          meta: { requiresAuth: false }
        },
        {
          path: 'sap',
          name: 'Painel SAP',
          component: () => import('../views/SAPDashboardView.vue'),
          meta: { requiresAuth: false }
        },
        {
          path: 'recepcao',
          name: 'Recepção / Triagem (AGHU)',
          component: () => import('../views/SAPRecepcaoView.vue'),
          meta: { requiresAuth: false }
        },
        {
          path: 'componentes',
          name: 'Componentes',
          component: () => import('../views/Exemplos.vue'),
          meta: { requiresAuth: false }
        },
        {
          path: 'exemplo',
          name: 'Exemplo',
          component: () => import('../views/Pacientes.vue'),
          meta: { requiresAuth: false }
        },
        {
          path: 'configuracoes',
          name: 'Configuracoes',
          component: () => import('../views/Configuracoes.vue'),
          meta: { requiresAuth: false }
        }
      ]
    }
  ]
})

export default router