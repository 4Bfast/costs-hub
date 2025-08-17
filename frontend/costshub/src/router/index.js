// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Importa todos os nossos componentes de forma explícita
import MainLayout from '../layouts/MainLayout.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import EmailVerificationView from '../views/EmailVerificationView.vue'
import DashboardView from '../views/DashboardView.vue'
import SettingsView from '../views/SettingsView.vue'
import AnalysisView from '../views/AnalysisView.vue'
import AlarmsView from '../views/AlarmsView.vue'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
  },
  {
    path: '/register',
    name: 'register',
    component: RegisterView,
  },
  {
    path: '/verify-email',
    name: 'verify-email',
    component: EmailVerificationView,
  },
  {
    // Rota "Pai" que contém o nosso layout com a barra lateral
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    // Todas as rotas abaixo serão renderizadas DENTRO do MainLayout
    children: [
      {
        path: '', // Se o usuário acessar a raiz, redireciona para o dashboard
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: DashboardView,
      },
      {
        path: 'settings',
        name: 'settings',
        component: SettingsView,
      },
      {
        path: 'analysis',
        name: 'analysis',
        component: AnalysisView,
      },
      {
        path: 'alarms',
        name: 'alarms',
        component: AlarmsView,
      },
    ]
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const isAuthenticated = authStore.isAuthenticated

  if (to.matched.some(record => record.meta.requiresAuth) && !isAuthenticated) {
    next({ name: 'login' })
  } else if (to.name === 'login' && isAuthenticated) {
    next({ name: 'dashboard' })
  } else {
    next()
  }
})

export default router