<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import StateBlock from '@/components/StateBlock.vue'

const route = useRoute()
const datos = ref(null)
const error = ref('')
const cargando = ref(true)
const actualizado = ref(null)
const abierto = ref(null)
let temporizador = null

const completados = computed(
  () => (datos.value?.players || []).filter((p) => p.logged_sets >= p.total_sets && p.total_sets).length
)

async function cargar({ silencioso = false } = {}) {
  if (!silencioso) cargando.value = true
  try {
    datos.value = await api.get(`/coach/routines/${route.params.id}/live`)
    actualizado.value = new Date()
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    cargando.value = false
  }
}

onMounted(() => {
  cargar()
  // Refresco periódico: el entrenador deja la pantalla abierta durante la sesión.
  temporizador = setInterval(() => cargar({ silencioso: true }), 20000)
})

onUnmounted(() => clearInterval(temporizador))

const hora = (fecha) =>
  fecha ? fecha.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }) : ''
</script>

<template>
  <AppShell
    :title="datos?.routine.name || 'Seguimiento'"
    :subtitle="
      datos
        ? `${completados}/${datos.players.length} jugadores han terminado`
        : 'Cargando…'
    "
    back="/panel"
  >
    <template #actions>
      <button
        type="button"
        class="btn-ghost h-11 w-11 !px-0"
        aria-label="Actualizar"
        @click="cargar()"
      >
        ↻
      </button>
    </template>

    <p v-if="cargando" class="py-12 text-center text-slate-400">Cargando…</p>
    <StateBlock v-else-if="error" icon="⚠️" title="No hemos podido cargar el seguimiento" :message="error">
      <button type="button" class="btn-primary mt-2" @click="cargar()">Reintentar</button>
    </StateBlock>

    <StateBlock
      v-else-if="!datos.players.length"
      icon="👥"
      title="Sin jugadores asignados"
      message="Esta batería no está asignada a ningún jugador activo."
    />

    <template v-else>
      <p class="mb-3 px-1 text-xs text-slate-500">
        Se actualiza solo cada 20 s · última {{ hora(actualizado) }}
      </p>

      <div class="space-y-2">
        <article v-for="jugador in datos.players" :key="jugador.player_id" class="card !p-0">
          <button
            type="button"
            class="flex w-full items-center gap-3 p-3 text-left"
            @click="abierto = abierto === jugador.player_id ? null : jugador.player_id"
          >
            <span
              class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-bold"
              :class="
                jugador.logged_sets >= jugador.total_sets && jugador.total_sets
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : jugador.logged_sets
                    ? 'bg-brand-600/20 text-brand-300'
                    : 'bg-slate-800 text-slate-500'
              "
            >
              {{ jugador.player_name.slice(0, 2).toUpperCase() }}
            </span>
            <span class="min-w-0 flex-1">
              <span class="block truncate font-semibold">{{ jugador.player_name }}</span>
              <span class="block h-1.5 w-full max-w-[10rem] overflow-hidden rounded-full bg-slate-800">
                <span
                  class="block h-full rounded-full transition-all"
                  :class="
                    jugador.logged_sets >= jugador.total_sets ? 'bg-emerald-500' : 'bg-brand-500'
                  "
                  :style="{
                    width: `${jugador.total_sets ? (jugador.logged_sets / jugador.total_sets) * 100 : 0}%`
                  }"
                />
              </span>
            </span>
            <span class="shrink-0 text-xs tabular-nums text-slate-400">
              {{ jugador.logged_sets }}/{{ jugador.total_sets }}
            </span>
            <span class="shrink-0 text-slate-600" :class="abierto === jugador.player_id && 'rotate-90'">
              ›
            </span>
          </button>

          <div v-if="abierto === jugador.player_id" class="border-t border-slate-800 p-3">
            <div v-for="ej in jugador.exercises" :key="ej.routine_exercise_id" class="mb-3 last:mb-0">
              <div class="mb-1 flex items-baseline justify-between gap-2">
                <span class="min-w-0 truncate text-sm font-semibold">{{ ej.exercise_name }}</span>
                <span v-if="ej.best_load_kg !== null" class="shrink-0 text-xs text-slate-400">
                  máx. <strong class="text-slate-200">{{ ej.best_load_kg }} kg</strong>
                </span>
              </div>

              <div v-if="ej.logs.length" class="flex flex-wrap gap-1.5">
                <span
                  v-for="log in ej.logs"
                  :key="log.set_number"
                  class="chip bg-slate-800 text-slate-200 tabular-nums"
                >
                  {{ log.load_kg }} kg
                  <span v-if="log.reps" class="ml-1 text-slate-500">×{{ log.reps }}</span>
                </span>
                <span
                  v-if="ej.logs.length < ej.sets"
                  class="chip border border-dashed border-slate-700 text-slate-600"
                >
                  faltan {{ ej.sets - ej.logs.length }}
                </span>
              </div>
              <p v-else class="text-xs text-slate-600">Sin registrar · {{ ej.sets }} series</p>
            </div>
          </div>
        </article>
      </div>
    </template>
  </AppShell>
</template>
