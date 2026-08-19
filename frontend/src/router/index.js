import { createRouter, createWebHistory } from 'vue-router'

import { setUnauthorizedHandler } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/', redirect: () => (localStorage.getItem('cargas_token') ? '/hoy' : '/entrar') },
  { path: '/entrar', name: 'login', component: () => import('@/views/LoginView.vue') },
  {
    path: '/hoy',
    name: 'player-home',
    component: () => import('@/views/PlayerHomeView.vue'),
    meta: { requiresAuth: true, role: 'player' }
  },
  {
    path: '/mis-sesiones',
    name: 'player-history',
    component: () => import('@/views/PlayerHistoryView.vue'),
    meta: { requiresAuth: true, role: 'player' }
  },
  {
    path: '/panel',
    name: 'coach-home',
    component: () => import('@/views/CoachHomeView.vue'),
    meta: { requiresAuth: true, role: 'coach' }
  },
  {
    path: '/panel/batería/nueva',
    name: 'coach-routine-new',
    component: () => import('@/views/CoachRoutineEditor.vue'),
    meta: { requiresAuth: true, role: 'coach' }
  },
  {
    path: '/panel/batería/:id',
    name: 'coach-routine-edit',
    component: () => import('@/views/CoachRoutineEditor.vue'),
    meta: { requiresAuth: true, role: 'coach' }
  },
  {
    path: '/panel/jugadores',
    name: 'coach-players',
    component: () => import('@/views/CoachPlayersView.vue'),
    meta: { requiresAuth: true, role: 'coach' }
  },
  {
    path: '/panel/ejercicios',
    name: 'coach-exercises',
    component: () => import('@/views/CoachExercisesView.vue'),
    meta: { requiresAuth: true, role: 'coach' }
  },
  {
    path: '/panel/exportar',
    name: 'coach-export',
    component: () => import('@/views/CoachExportView.vue'),
    meta: { requiresAuth: true, role: 'coach' }
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

const homeFor = (auth) => (auth.isCoach ? '/panel' : '/hoy')

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isLogged) return { path: '/entrar' }
  if (to.meta.role && auth.isLogged && auth.user.role !== to.meta.role) return { path: homeFor(auth) }
  if (to.name === 'login' && auth.isLogged) return { path: homeFor(auth) }
  return true
})

setUnauthorizedHandler(() => {
  useAuthStore().logout()
  router.push('/entrar')
})

export default router
