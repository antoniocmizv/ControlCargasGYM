<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import NumberStepper from '@/components/NumberStepper.vue'
import StateBlock from '@/components/StateBlock.vue'
import { fechaLarga } from '@/utils/fechas'

const route = useRoute()

const rutina = ref(null)
const jugadores = ref([])
const elegido = ref(null)
const borrador = ref({})
const cargando = ref(true)
const guardando = ref(false)
const guardado = ref(false)
const error = ref('')

const clave = (itemId) => `${elegido.value?.player_id}:${itemId}`

/** Jugadores que ya tienen algo marcado, para verlo de un vistazo en la lista. */
const conAnotaciones = ref(new Set())

onMounted(async () => {
  try {
    const [vivo, anotaciones] = await Promise.all([
      api.get(`/coach/routines/${route.params.id}/live`),
      api.get(`/coach/routines/${route.params.id}/anotaciones`)
    ])
    rutina.value = vivo.routine
    jugadores.value = vivo.players

    for (const anotacion of anotaciones) {
      borrador.value[`${anotacion.user_id}:${anotacion.routine_exercise_id}`] = {
        target_load_kg: anotacion.target_load_kg,
        note: anotacion.note || ''
      }
      conAnotaciones.value.add(anotacion.user_id)
    }
  } catch (err) {
    error.value = err.message
  } finally {
    cargando.value = false
  }
})

function valor(itemId, campo) {
  return borrador.value[clave(itemId)]?.[campo] ?? (campo === 'note' ? '' : null)
}

function fijar(itemId, campo, valorNuevo) {
  const actual = borrador.value[clave(itemId)] || { target_load_kg: null, note: '' }
  borrador.value = {
    ...borrador.value,
    [clave(itemId)]: { ...actual, [campo]: valorNuevo }
  }
  guardado.value = false
}

const ejercicios = computed(() => elegido.value?.exercises || [])

async function guardar() {
  guardando.value = true
  error.value = ''
  try {
    const entradas = ejercicios.value.map((ejercicio) => ({
      routine_exercise_id: ejercicio.routine_exercise_id,
      user_id: elegido.value.player_id,
      target_load_kg: valor(ejercicio.routine_exercise_id, 'target_load_kg'),
      note: valor(ejercicio.routine_exercise_id, 'note') || null
    }))
    await api.put(`/coach/routines/${route.params.id}/anotaciones`, entradas)

    const algo = entradas.some((e) => e.target_load_kg !== null || e.note)
    if (algo) conAnotaciones.value.add(elegido.value.player_id)
    else conAnotaciones.value.delete(elegido.value.player_id)
    conAnotaciones.value = new Set(conAnotaciones.value)

    guardado.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    guardando.value = false
  }
}

function abrir(jugador) {
  elegido.value = jugador
  guardado.value = false
}
</script>

<template>
  <AppShell
    :title="elegido ? elegido.player_name : 'Anotaciones'"
    :subtitle="rutina ? `${rutina.name} · ${fechaLarga(rutina.session_date)}` : 'Cargando…'"
    :back="elegido ? null : '/panel'"
  >
    <template v-if="elegido" #actions>
      <button type="button" class="btn-ghost !px-3 !text-sm" @click="elegido = null">
        ‹ Jugadores
      </button>
    </template>

    <p v-if="cargando" class="py-12 text-center text-slate-400">Cargando…</p>
    <StateBlock v-else-if="error && !rutina" icon="⚠️" title="No hemos podido cargar" :message="error" />

    <StateBlock
      v-else-if="!jugadores.length"
      icon="👥"
      title="Sin jugadores asignados"
      message="Asigna la batería a alguien para poder anotarle pesos."
    />

    <!-- Elegir jugador -->
    <template v-else-if="!elegido">
      <p class="mb-3 px-1 text-sm text-slate-400">
        Marca a cada jugador el peso que debe hacer en cada ejercicio. Lo verá en su sesión.
      </p>
      <div class="space-y-2">
        <button
          v-for="jugador in jugadores"
          :key="jugador.player_id"
          type="button"
          class="flex w-full items-center gap-3 rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-left transition active:scale-[0.98] hover:border-brand-600"
          @click="abrir(jugador)"
        >
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-600/20 text-sm font-bold text-brand-300"
          >
            {{ jugador.player_name.slice(0, 2).toUpperCase() }}
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate font-semibold">{{ jugador.player_name }}</span>
            <span
              class="text-xs"
              :class="conAnotaciones.has(jugador.player_id) ? 'text-brand-400' : 'text-slate-500'"
            >
              {{ conAnotaciones.has(jugador.player_id) ? '🎯 con anotaciones' : 'sin anotar' }}
            </span>
          </span>
          <span class="shrink-0 text-slate-600">›</span>
        </button>
      </div>
    </template>

    <!-- Anotar ejercicio a ejercicio -->
    <template v-else>
      <div class="space-y-3">
        <article
          v-for="ejercicio in ejercicios"
          :key="ejercicio.routine_exercise_id"
          class="card"
        >
          <div class="mb-3 flex items-baseline justify-between gap-2">
            <h3 class="min-w-0 truncate font-bold">{{ ejercicio.exercise_name }}</h3>
            <span class="shrink-0 text-xs text-slate-500">
              {{ ejercicio.sets }} series
              <template v-if="ejercicio.target_reps"> × {{ ejercicio.target_reps }}</template>
            </span>
          </div>

          <label class="mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-500">
            Peso a hacer
          </label>
          <NumberStepper
            :model-value="valor(ejercicio.routine_exercise_id, 'target_load_kg')"
            :step="2.5"
            :max="500"
            suffix="kg"
            @update:model-value="fijar(ejercicio.routine_exercise_id, 'target_load_kg', $event)"
          />

          <label class="mt-3 mb-1.5 block text-xs font-medium uppercase tracking-wide text-slate-500">
            Nota (opcional)
          </label>
          <input
            :value="valor(ejercicio.routine_exercise_id, 'note')"
            class="field !py-2 text-sm"
            maxlength="500"
            placeholder="Ej. baja el ritmo, cuida la técnica"
            @input="fijar(ejercicio.routine_exercise_id, 'note', $event.target.value)"
          />

          <p v-if="ejercicio.best_load_kg !== null" class="mt-2 text-xs text-slate-500">
            Ya ha registrado hasta {{ ejercicio.best_load_kg }} kg en esta sesión.
          </p>
        </article>
      </div>

      <p v-if="error" class="mt-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">
        {{ error }}
      </p>
      <p v-if="guardado" class="mt-4 rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
        Guardado. {{ elegido.player_name }} lo verá en su sesión.
      </p>

      <button type="button" class="btn-primary mt-4 w-full" :disabled="guardando" @click="guardar">
        {{ guardando ? 'Guardando…' : 'Guardar anotaciones' }}
      </button>
      <p class="mt-2 px-1 text-xs text-slate-500">
        Deja el peso y la nota en blanco para quitar una anotación.
      </p>
    </template>
  </AppShell>
</template>
