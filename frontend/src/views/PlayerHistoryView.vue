<script setup>
import { onMounted, ref } from 'vue'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import StateBlock from '@/components/StateBlock.vue'

const sessions = ref([])
const loading = ref(true)
const error = ref('')
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
        :to="`/sesion/${session.session_date}`"
        class="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 transition active:scale-[0.98]"
      >
        <span class="w-24 shrink-0 text-sm font-semibold first-letter:uppercase text-brand-300">
          {{ formatDate(session.session_date) }}
        </span>
        <span class="min-w-0 flex-1">
          <span class="block truncate font-semibold">{{ session.name }}</span>
          <span class="text-xs" :class="session.pending ? 'text-amber-400' : 'text-slate-500'">
            <template v-if="session.pending">⏳ sin rellenar</template>
            <template v-else>
              {{ session.exercise_count }}
              {{ session.exercise_count === 1 ? 'ejercicio' : 'ejercicios' }}
            </template>
          </span>
        </span>
        <span class="shrink-0 text-slate-600">›</span>
      </RouterLink>
    </div>
  </AppShell>
</template>
