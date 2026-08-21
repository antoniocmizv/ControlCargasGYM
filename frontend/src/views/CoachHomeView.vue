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

    <RouterLink to="/panel/bateria/nueva" class="btn-primary mb-5 w-full">
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
              <RouterLink :to="`/panel/bateria/${routine.id}`" class="btn-ghost flex-1 !text-sm">
                Editar
              </RouterLink>
              <RouterLink
                :to="`/panel/bateria/${routine.id}/seguimiento`"
                class="btn-ghost flex-1 !text-sm"
              >
                Seguimiento
              </RouterLink>
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
              <RouterLink
                :to="`/panel/bateria/${routine.id}/seguimiento`"
                class="btn-ghost flex-1 !text-sm"
              >
                Seguimiento
              </RouterLink>
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

  </AppShell>
</template>
