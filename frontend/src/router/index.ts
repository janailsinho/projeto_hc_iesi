import { createRouter, createWebHistory, NavigationGuardNext } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import Home from '../views/Home.vue';
import Login from '../views/Login.vue';
import Configuracoes from '../views/Configuracoes.vue';

import Exemplos from '../views/Exemplos.vue';
import Pacientes from '../views/Pacientes.vue';

import SAPDashboardView from '../views/SAPDashboardView.vue'

const routes = [
  {
    path: '/',
    name: 'Início',
    component: Home,
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { layout: 'LoginLayout' },
  },
  {
    path: '/componentes',
    name: 'Componentes',
    component: Exemplos,
  },
  {
    path: '/exemplo',
    name: 'Exemplo',
    component: Pacientes,
    meta: { requiresAuth: true },
  },
  {
    path: '/configuracoes',
    name: 'Configuracoes',
    component: Configuracoes,
    meta: { requiresAuth: true },
  },
  {
    path: '/sap',
    name: 'SAPDashboard',
    component: SAPDashboardView
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  linkActiveClass: 'bg-paper-active-link',
  linkExactActiveClass: 'bg-paper-active-link',
});

router.beforeEach((to, _from, next: NavigationGuardNext) => {
  const authStore = useAuthStore();

  // Força o bypass de autenticação para a apresentação do SAP, home e login
  if (to.path.startsWith('/sap') || to.path === '/' || to.path === '/login') {
    return next();
  }

  // Simula liberação automática para rotas protegidas durante a demonstração
  if (to.meta.requiresAuth) {
    return next();
  }

  next();
});

export default router;