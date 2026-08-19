<script setup>
import { onMounted, ref } from 'vue'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import StateBlock from '@/components/StateBlock.vue'
import { useWorkoutStore } from '@/stores/workout'

const workout = useWorkoutStore()
const sessions = ref([])
const loading = ref(true)
const error = ref('')
const openDay = ref(null)

onMounted(async () => {
  try {
    sessions.value = await api.get('/routines/mine')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

const formatDate = (iso) =>
  new Date(iso).toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' })

async function openSession(session) {
  openDay.value = session.session_date
  await workout.loadToday(session.session_date)
}
</script>

<template>
  <AppShell title="Mis sesiones" subtitle="Últimas baterías asignadas" back="/hoy">
    <p v-if="loading" class="py-12 text-center text-slate-400">Cargando…</p>
    <StateBlock v-else-if="error" icon="⚠️" title="No hemos podido cargar el historial" :message="error" />
    <StateBlock
      v-else-if="!sessions.length"
      icon="🗓"
      title="Todavía no tienes sesiones"
      message="Aquí aparecerán las baterías que te asigne el entrenador."
    />

    <div v-else class="space-y-2">
      <RouterLink
        v-for="session in sessions"
        :key="session.id"
        to="/hoy"
        class="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 transition active:scale-[0.98]"
        @click="openSession(session)"
      >
        <span class="w-24 shrink-0 text-sm font-semibold first-letter:uppercase text-brand-300">
          {{ formatDate(session.session_date) }}
        </span>
        <span class="min-w-0 flex-1">
          <span class="block truncate font-semibold">{{ session.name }}</span>
          <span class="text-xs text-slate-500">{{ session.exercise_count }} ejercicios</span>
        </span>
        <span class="shrink-0 text-slate-600">›</span>
      </RouterLink>
    </div>
  </AppShell>
</template>
