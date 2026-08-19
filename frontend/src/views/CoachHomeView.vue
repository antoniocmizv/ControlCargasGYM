<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import StateBlock from '@/components/StateBlock.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const routines = ref([])
const loading = ref(true)
const error = ref('')
const progress = ref(null)
const busy = ref(false)

const todayIso = new Date().toISOString().slice(0, 10)

const upcoming = computed(() => routines.value.filter((r) => r.session_date >= todayIso))
const past = computed(() => routines.value.filter((r) => r.session_date < todayIso))

const formatDate = (iso) =>
  new Date(iso).toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })

async function load() {
  loading.value = true
  try {
    routines.value = await api.get('/coach/routines')
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function showProgress(routine) {
  progress.value = { routine, rows: null }
  try {
    progress.value = await api.get(`/coach/routines/${routine.id}/progress`)
  } catch (err) {
    error.value = err.message
    progress.value = null
  }
}

async function duplicateTo(routine) {
  const date = window.prompt('Copiar esta batería al día (AAAA-MM-DD):', todayIso)
  if (!date) return
  busy.value = true
  try {
    await api.post(`/coach/routines/${routine.id}/duplicate`, undefined, { session_date: date })
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function remove(routine) {
  if (!window.confirm(`¿Eliminar «${routine.name}» y todas sus cargas registradas?`)) return
  busy.value = true
  try {
    await api.delete(`/coach/routines/${routine.id}`)
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

function logout() {
  auth.logout()
  router.push('/entrar')
}
</script>

<template>
  <AppShell title="Panel del entrenador" :subtitle="auth.user?.name">
    <template #actions>
      <button type="button" class="btn-ghost h-11 w-11 !px-0" aria-label="Salir" @click="logout">
        ⏻
      </button>
    </template>

    <nav class="mb-5 grid grid-cols-3 gap-2">
      <RouterLink to="/panel/jugadores" class="card flex flex-col items-center gap-1 !p-3 text-center">
        <span class="text-2xl">👥</span>
        <span class="text-xs font-semibold">Jugadores</span>
      </RouterLink>
      <RouterLink to="/panel/ejercicios" class="card flex flex-col items-center gap-1 !p-3 text-center">
        <span class="text-2xl">🏋️</span>
        <span class="text-xs font-semibold">Ejercicios</span>
      </RouterLink>
      <RouterLink to="/panel/exportar" class="card flex flex-col items-center gap-1 !p-3 text-center">
        <span class="text-2xl">📊</span>
        <span class="text-xs font-semibold">Exportar</span>
      </RouterLink>
    </nav>

    <RouterLink to="/panel/batería/nueva" class="btn-primary mb-5 w-full">
      + Dar de alta una sesión
    </RouterLink>

    <p v-if="error" class="mb-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{{ error }}</p>
    <p v-if="loading" class="py-10 text-center text-slate-400">Cargando baterías…</p>

    <StateBlock
      v-else-if="!routines.length"
      icon="📋"
      title="Aún no hay ninguna batería"
      message="Crea la primera sesión y asígnala al equipo, a un grupo o a jugadores concretos."
    />

    <template v-else>
      <section v-if="upcoming.length" class="mb-6">
        <h2 class="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Hoy y próximas
        </h2>
        <div class="space-y-2">
          <article v-for="routine in upcoming" :key="routine.id" class="card !p-3">
            <div class="flex items-start gap-3">
              <div class="min-w-0 flex-1">
                <p class="truncate font-bold">{{ routine.name }}</p>
                <p class="text-sm first-letter:uppercase text-brand-300">{{ formatDate(routine.session_date) }}</p>
                <p class="mt-0.5 text-xs text-slate-500">
                  {{ routine.exercise_count }} ejercicios · {{ routine.assigned_players }} jugadores
                </p>
              </div>
            </div>
            <div class="mt-3 flex gap-2">
              <RouterLink :to="`/panel/batería/${routine.id}`" class="btn-ghost flex-1 !text-sm">
                Editar
              </RouterLink>
              <button type="button" class="btn-ghost flex-1 !text-sm" @click="showProgress(routine)">
                Progreso
              </button>
              <button
                type="button"
                class="btn-ghost !px-3"
                aria-label="Copiar a otro día"
                :disabled="busy"
                @click="duplicateTo(routine)"
              >
                ⧉
              </button>
              <button
                type="button"
                class="btn-danger !px-3"
                aria-label="Eliminar batería"
                :disabled="busy"
                @click="remove(routine)"
              >
                🗑
              </button>
            </div>
          </article>
        </div>
      </section>

      <section v-if="past.length">
        <h2 class="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Anteriores</h2>
        <div class="space-y-2">
          <article v-for="routine in past" :key="routine.id" class="card !p-3">
            <p class="truncate font-semibold">{{ routine.name }}</p>
            <p class="text-xs text-slate-500 first-letter:uppercase">
              {{ formatDate(routine.session_date) }} · {{ routine.exercise_count }} ejercicios
            </p>
            <div class="mt-2 flex gap-2">
              <button type="button" class="btn-ghost flex-1 !text-sm" @click="showProgress(routine)">
                Progreso
              </button>
              <button
                type="button"
                class="btn-ghost !px-3"
                aria-label="Copiar a otro día"
                :disabled="busy"
                @click="duplicateTo(routine)"
              >
                ⧉
              </button>
            </div>
          </article>
        </div>
      </section>
    </template>

    <!-- Progreso de una batería -->
    <div
      v-if="progress"
      class="fixed inset-0 z-40 flex items-end bg-black/70 p-0 sm:items-center sm:p-4"
      @click.self="progress = null"
    >
      <div class="max-h-[80vh] w-full overflow-y-auto rounded-t-2xl bg-slate-900 p-5 sm:mx-auto sm:max-w-md sm:rounded-2xl">
        <div class="mb-4 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="truncate text-lg font-bold">{{ progress.routine.name }}</h3>
            <p class="text-sm first-letter:uppercase text-slate-400">
              {{ formatDate(progress.routine.session_date) }}
            </p>
          </div>
          <button type="button" class="btn-ghost !px-3" @click="progress = null">✕</button>
        </div>

        <p v-if="!progress.rows" class="py-6 text-center text-slate-400">Cargando…</p>
        <p v-else-if="!progress.rows.length" class="py-6 text-center text-sm text-slate-400">
          No hay jugadores asignados a esta batería.
        </p>
        <ul v-else class="space-y-2">
          <li
            v-for="row in progress.rows"
            :key="row.player_id"
            class="flex items-center gap-3 rounded-xl bg-slate-800/60 px-3 py-2.5"
          >
            <span class="min-w-0 flex-1 truncate text-sm font-semibold">{{ row.player_name }}</span>
            <span class="h-1.5 w-20 overflow-hidden rounded-full bg-slate-700">
              <span
                class="block h-full rounded-full"
                :class="row.logged_sets >= row.total_sets ? 'bg-emerald-500' : 'bg-brand-500'"
                :style="{ width: `${row.total_sets ? (row.logged_sets / row.total_sets) * 100 : 0}%` }"
              />
            </span>
            <span class="w-12 shrink-0 text-right text-xs tabular-nums text-slate-400">
              {{ row.logged_sets }}/{{ row.total_sets }}
            </span>
          </li>
        </ul>
      </div>
    </div>
  </AppShell>
</template>
