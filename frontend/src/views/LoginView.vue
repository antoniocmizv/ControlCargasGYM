<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const mode = ref('player')
const players = ref([])
const search = ref('')
const selected = ref(null)
const pin = ref('')
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const loadingPlayers = ref(true)

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return players.value
  return players.value.filter((player) => player.name.toLowerCase().includes(term))
})

onMounted(async () => {
  try {
    players.value = await api.get('/auth/players')
  } catch (err) {
    error.value = err.message
  } finally {
    loadingPlayers.value = false
  }
})

// Con el PIN completo entramos solos: una pulsación menos.
watch(pin, (value) => {
  if (value.length === 4) submitPlayer()
})

function pickPlayer(player) {
  selected.value = player
  pin.value = ''
  error.value = ''
}

function pressDigit(digit) {
  if (pin.value.length < 4) pin.value += digit
  navigator.vibrate?.(8)
}

function eraseDigit() {
  pin.value = pin.value.slice(0, -1)
}

async function submitPlayer() {
  if (loading.value || pin.value.length < 4) return
  loading.value = true
  error.value = ''
  try {
    await auth.loginPlayer(selected.value.id, pin.value)
    router.push('/hoy')
  } catch (err) {
    error.value = err.message
    pin.value = ''
    navigator.vibrate?.([40, 60, 40])
  } finally {
    loading.value = false
  }
}

async function submitCoach() {
  loading.value = true
  error.value = ''
  try {
    await auth.loginCoach(username.value.trim(), password.value)
    router.push('/panel')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function switchMode(next) {
  mode.value = next
  error.value = ''
  selected.value = null
  pin.value = ''
}
</script>

<template>
  <div class="flex min-h-screen flex-col px-5 py-8" style="padding-top: env(safe-area-inset-top)">
    <div class="mx-auto w-full max-w-md flex-1">
      <div class="mb-8 text-center">
        <div class="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600">
          <span class="text-3xl">🏋️</span>
        </div>
        <h1 class="text-2xl font-bold">Control de Cargas</h1>
        <p class="text-sm text-slate-400">Registra tus kg de cada sesión</p>
      </div>

      <!-- Paso 1: elegir jugador -->
      <template v-if="mode === 'player' && !selected">
        <p v-if="loadingPlayers" class="py-8 text-center text-slate-400">Cargando equipo…</p>

        <template v-else-if="players.length">
          <input
            v-model="search"
            type="search"
            placeholder="Busca tu nombre"
            class="field mb-3"
            autocomplete="off"
          />
          <div class="space-y-2">
            <button
              v-for="player in filtered"
              :key="player.id"
              type="button"
              class="flex w-full items-center gap-3 rounded-xl border border-slate-800 bg-slate-900 px-4 py-4 text-left transition active:scale-[0.98] hover:border-brand-600"
              @click="pickPlayer(player)"
            >
              <span
                class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-600/20 text-sm font-bold text-brand-300"
              >
                {{ player.name.slice(0, 2).toUpperCase() }}
              </span>
              <span class="flex-1 truncate font-semibold">{{ player.name }}</span>
              <span class="text-slate-600">›</span>
            </button>
            <p v-if="!filtered.length" class="py-6 text-center text-sm text-slate-500">
              Ningún jugador coincide con «{{ search }}»
            </p>
          </div>
        </template>

        <p v-else class="card text-center text-sm text-slate-400">
          Todavía no hay jugadores dados de alta. Entra como entrenador para crearlos.
        </p>
      </template>

      <!-- Paso 2: PIN -->
      <template v-else-if="mode === 'player' && selected">
        <button type="button" class="mb-6 text-sm text-brand-400" @click="selected = null">
          ‹ Cambiar de jugador
        </button>

        <p class="mb-1 text-center text-sm text-slate-400">Hola,</p>
        <p class="mb-6 text-center text-xl font-bold">{{ selected.name }}</p>

        <div class="mb-6 flex justify-center gap-3">
          <span
            v-for="index in 4"
            :key="index"
            class="h-4 w-4 rounded-full transition"
            :class="pin.length >= index ? 'bg-brand-500 scale-110' : 'bg-slate-700'"
          />
        </div>

        <div class="mx-auto grid max-w-xs grid-cols-3 gap-3">
          <button
            v-for="digit in ['1', '2', '3', '4', '5', '6', '7', '8', '9']"
            :key="digit"
            type="button"
            class="btn-ghost h-16 text-2xl font-bold"
            @click="pressDigit(digit)"
          >
            {{ digit }}
          </button>
          <span />
          <button type="button" class="btn-ghost h-16 text-2xl font-bold" @click="pressDigit('0')">
            0
          </button>
          <button
            type="button"
            class="btn-ghost h-16 text-xl"
            aria-label="Borrar"
            @click="eraseDigit"
          >
            ⌫
          </button>
        </div>
      </template>

      <!-- Entrenador -->
      <form v-else class="space-y-4" @submit.prevent="submitCoach">
        <div>
          <label class="label" for="usuario">Usuario</label>
          <input
            id="usuario"
            v-model="username"
            class="field"
            autocomplete="username"
            autocapitalize="none"
            required
          />
        </div>
        <div>
          <label class="label" for="clave">Contraseña</label>
          <input
            id="clave"
            v-model="password"
            type="password"
            class="field"
            autocomplete="current-password"
            required
          />
        </div>
        <button type="submit" class="btn-primary w-full" :disabled="loading">
          {{ loading ? 'Entrando…' : 'Entrar al panel' }}
        </button>
      </form>

      <p
        v-if="error"
        class="mt-5 rounded-xl bg-red-500/10 px-4 py-3 text-center text-sm text-red-300"
        role="alert"
      >
        {{ error }}
      </p>
    </div>

    <div class="mx-auto w-full max-w-md pt-8 text-center">
      <button
        type="button"
        class="text-sm text-slate-500 underline underline-offset-4"
        @click="switchMode(mode === 'player' ? 'coach' : 'player')"
      >
        {{ mode === 'player' ? 'Soy el entrenador' : 'Soy jugador' }}
      </button>
    </div>
  </div>
</template>
