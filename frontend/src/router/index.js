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
    meta: { requiresAuth: true, player: true }
  },
  {
    // Sesión de un día concreto: en la URL para que sobreviva a una recarga.
    path: '/sesion/:date(\\d{4}-\\d{2}-\\d{2})',
    name: 'player-session',
    component: () => import('@/views/PlayerHomeView.vue'),
    meta: { requiresAuth: true, player: true }
  },
  {
    path: '/progresion',
    name: 'player-progress',
    component: () => import('@/views/PlayerProgressView.vue'),
    meta: { requiresAuth: true, player: true }
  },
  {
    path: '/mis-sesiones',
    name: 'player-history',
    component: () => import('@/views/PlayerHistoryView.vue'),
    meta: { requiresAuth: true, player: true }
  },
  {
    path: '/panel',
    name: 'coach-home',
    component: () => import('@/views/CoachHomeView.vue'),
    meta: { requiresAuth: true, staff: true }
  },
  {
    path: '/panel/bateria/nueva',
    name: 'coach-routine-new',
    component: () => import('@/views/CoachRoutineEditor.vue'),
    meta: { requiresAuth: true, staff: true }
  },
  {
    path: '/panel/bateria/:id',
    name: 'coach-routine-edit',
    component: () => import('@/views/CoachRoutineEditor.vue'),
    meta: { requiresAuth: true, staff: true }
  },
  {
    path: '/panel/bateria/:id/seguimiento',
    name: 'coach-live',
    component: () => import('@/views/CoachLiveView.vue'),
    meta: { requiresAuth: true, staff: true }
  },
  {
    path: '/panel/jugadores',
    name: 'coach-players',
    component: () => import('@/views/CoachPlayersView.vue'),
    meta: { requiresAuth: true, staff: true }
  },
  {
    path: '/panel/ejercicios',
    name: 'coach-exercises',
    component: () => import('@/views/CoachExercisesView.vue'),
    meta: { requiresAuth: true, staff: true }
  },
  {
    path: '/panel/entrenadores',
    name: 'coach-staff',
    component: () => import('@/views/CoachStaffView.vue'),
    meta: { requiresAuth: true, staff: true, admin: true }
  },
  {
    path: '/panel/cuenta',
    name: 'coach-account',
    component: () => import('@/views/CoachAccountView.vue'),
    meta: { requiresAuth: true, staff: true }
  },
  {
    path: '/panel/exportar',
    name: 'coach-export',
    component: () => import('@/views/CoachExportView.vue'),
    meta: { requiresAuth: true, staff: true }
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
  if (to.meta.staff && auth.isLogged && !auth.isCoach) return { path: homeFor(auth) }
  if (to.meta.player && auth.isLogged && !auth.isPlayer) return { path: homeFor(auth) }
  if (to.meta.admin && auth.isLogged && !auth.isAdmin) return { path: '/panel' }
  if (to.name === 'login' && auth.isLogged) return { path: homeFor(auth) }
  return true
})

setUnauthorizedHandler(() => {
  useAuthStore().logout()
  router.push('/entrar')
})

export default router
