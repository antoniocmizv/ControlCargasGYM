import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api } from '@/api/client'

const TOKEN_KEY = 'cargas_token'
const USER_KEY = 'cargas_user'

function loadStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY)) || null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY))
  const user = ref(loadStoredUser())

  const isLogged = computed(() => Boolean(token.value && user.value))
  const isCoach = computed(() => user.value?.role === 'coach')
  const isPlayer = computed(() => user.value?.role === 'player')

  function persist(data) {
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
  }

  async function loginPlayer(userId, pin) {
    persist(await api.post('/auth/login/player', { user_id: userId, pin }))
  }

  async function loginCoach(username, password) {
    persist(await api.post('/auth/login/coach', { username, password }))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, isLogged, isCoach, isPlayer, loginPlayer, loginCoach, logout }
})
