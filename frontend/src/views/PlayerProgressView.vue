<script setup>
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import ProgressChart from '@/components/ProgressChart.vue'
import StateBlock from '@/components/StateBlock.vue'

const ejercicios = ref([])
const seleccionado = ref(null)
const detalle = ref(null)
const cargando = ref(true)
const cargandoDetalle = ref(false)
const error = ref('')

const diferencia = computed(() => {
  if (!seleccionado.value) return 0
  return Math.round((seleccionado.value.latest_load_kg - seleccionado.value.first_load_kg) * 10) / 10
})

onMounted(async () => {
  try {
    ejercicios.value = await api.get('/progress/exercises')
    if (ejercicios.value.length) await elegir(ejercicios.value[0])
  } catch (err) {
    error.value = err.message
  } finally {
    cargando.value = false
  }
})

async function elegir(resumen) {
  seleccionado.value = resumen
  cargandoDetalle.value = true
  try {
    detalle.value = await api.get(`/progress/exercises/${resumen.exercise.id}`)
  } catch (err) {
    error.value = err.message
    detalle.value = null
  } finally {
    cargandoDetalle.value = false
  }
}
</script>

<template>
  <AppShell title="Mi progresión" subtitle="Cómo evoluciona tu peso" back="/hoy">
    <p v-if="cargando" class="py-12 text-center text-slate-400">Cargando…</p>

    <StateBlock v-else-if="error" icon="⚠️" title="No hemos podido cargar la progresión" :message="error" />

    <StateBlock
      v-else-if="!ejercicios.length"
      icon="📈"
      title="Todavía no hay nada que mostrar"
      message="En cuanto registres cargas en una sesión verás aquí cómo evolucionas en cada ejercicio."
    />

    <template v-else>
      <!-- Selector de ejercicio -->
      <div class="-mx-4 mb-4 overflow-x-auto px-4">
        <div class="flex w-max gap-2">
          <button
            v-for="resumen in ejercicios"
            :key="resumen.exercise.id"
            type="button"
            class="btn !min-h-[38px] whitespace-nowrap !px-3 !text-sm"
            :class="
              seleccionado?.exercise.id === resumen.exercise.id
                ? 'bg-brand-600 text-white'
                : 'bg-slate-800 text-slate-300'
            "
            @click="elegir(resumen)"
          >
            {{ resumen.exercise.name }}
          </button>
        </div>
      </div>

      <section v-if="seleccionado" class="card mb-4">
        <h2 class="mb-1 text-lg font-bold">{{ seleccionado.exercise.name }}</h2>
        <p class="mb-4 text-sm text-slate-400">
          {{ seleccionado.sessions }} {{ seleccionado.sessions === 1 ? 'sesión' : 'sesiones' }}
          registradas
        </p>

        <!-- Cifras de cabecera -->
        <div class="mb-5 grid grid-cols-3 gap-2 text-center">
          <div class="rounded-xl bg-slate-800/60 px-2 py-3">
            <p class="text-xs text-slate-500">Actual</p>
            <p class="text-xl font-bold tabular-nums">{{ seleccionado.latest_load_kg }}</p>
            <p class="text-[10px] text-slate-500">kg</p>
          </div>
          <div class="rounded-xl bg-slate-800/60 px-2 py-3">
            <p class="text-xs text-slate-500">Récord</p>
            <p class="text-xl font-bold tabular-nums text-emerald-300">
              {{ seleccionado.best_load_kg }}
            </p>
            <p class="text-[10px] text-slate-500">kg</p>
          </div>
          <div class="rounded-xl bg-slate-800/60 px-2 py-3">
            <p class="text-xs text-slate-500">Desde el inicio</p>
            <p
              class="text-xl font-bold tabular-nums"
              :class="diferencia > 0 ? 'text-emerald-300' : diferencia < 0 ? 'text-amber-300' : ''"
            >
              {{ diferencia > 0 ? '+' : '' }}{{ diferencia }}
            </p>
            <p class="text-[10px] text-slate-500">kg</p>
          </div>
        </div>

        <p v-if="cargandoDetalle" class="py-8 text-center text-sm text-slate-500">Cargando…</p>
        <ProgressChart v-else-if="detalle?.points.length" :points="detalle.points" />
      </section>

      <!-- Los mismos datos en tabla: el gráfico no puede ser la única vía -->
      <section v-if="detalle?.points.length" class="card">
        <h3 class="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Sesión a sesión
        </h3>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-800 text-left text-xs text-slate-500">
                <th class="pb-2 font-medium">Día</th>
                <th class="pb-2 font-medium">Sesión</th>
                <th class="pb-2 text-right font-medium">Máx.</th>
                <th class="pb-2 text-right font-medium">Series</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="punto in [...detalle.points].reverse()"
                :key="punto.session_date"
                class="border-b border-slate-800/60 last:border-0"
              >
                <td class="py-2 whitespace-nowrap text-slate-300">
                  {{ new Date(`${punto.session_date}T00:00:00`).toLocaleDateString('es-ES') }}
                </td>
                <td class="max-w-[8rem] truncate py-2 text-slate-400">{{ punto.routine_name }}</td>
                <td class="py-2 text-right font-semibold tabular-nums">{{ punto.best_load_kg }} kg</td>
                <td class="py-2 text-right tabular-nums text-slate-400">{{ punto.sets }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </AppShell>
</template>
