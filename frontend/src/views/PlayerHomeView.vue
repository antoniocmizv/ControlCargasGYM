<script setup>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/AppShell.vue'
import ExerciseCard from '@/components/ExerciseCard.vue'
import StateBlock from '@/components/StateBlock.vue'
import { useAuthStore } from '@/stores/auth'
import { useWorkoutStore } from '@/stores/workout'

const auth = useAuthStore()
const workout = useWorkoutStore()
const router = useRouter()
const route = useRoute()

const hoyIso = () => new Date().toLocaleDateString('sv-SE') // AAAA-MM-DD en local

/** El día que se está rellenando: el de la URL o, si no lo hay, hoy. */
const dia = computed(() => route.params.date || hoyIso())
const esHoy = computed(() => dia.value === hoyIso())

const fechaLarga = computed(() =>
  new Date(`${dia.value}T00:00:00`).toLocaleDateString('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long'
  })
)

/** Con una sola batería se muestra su nombre; con varias, el resumen del día. */
const headline = computed(() =>
  workout.routines.length === 1
    ? workout.routines[0].name
    : `${workout.routines.length} baterías ${esHoy.value ? 'hoy' : 'ese día'}`
)

const progress = computed(() =>
  workout.totalSets ? Math.round((workout.loggedSets / workout.totalSets) * 100) : 0
)

/** Se despliega solo el ejercicio en curso; el resto queda plegado. */
const firstPendingId = computed(
  () => workout.allItems.find((item) => item.logs.length < item.sets)?.id ?? null
)

onMounted(() => {
  workout.loadDay(dia.value)
  window.addEventListener('online', workout.flushQueue)
})

// Cambiar de día desde el historial recarga sin desmontar la vista.
watch(dia, (valor) => workout.loadDay(valor))

onUnmounted(() => {
  window.removeEventListener('online', workout.flushQueue)
})

function onSave({ itemId, setNumber, loadKg, reps }) {
  workout.saveSet(itemId, setNumber, loadKg, reps)
}

function logout() {
  workout.reset()
  auth.logout()
  router.push('/entrar')
}
</script>

<template>
  <AppShell
    :title="auth.user?.name || 'Mi sesión'"
    :subtitle="fechaLarga"
    :back="esHoy ? null : '/mis-sesiones'"
  >
    <template #actions>
      <RouterLink to="/progresion" class="btn-ghost h-11 w-11 !px-0" aria-label="Mi progresión">
        📈
      </RouterLink>
      <RouterLink to="/mis-sesiones" class="btn-ghost h-11 w-11 !px-0" aria-label="Mis sesiones">
        🗓
      </RouterLink>
      <button
        v-if="esHoy"
        type="button"
        class="btn-ghost h-11 w-11 !px-0"
        aria-label="Salir"
        @click="logout"
      >
        ⏻
      </button>
    </template>

    <p
      v-if="!esHoy"
      class="mb-3 rounded-xl bg-brand-600/15 px-4 py-3 text-sm text-brand-200"
    >
      📅 Estás rellenando una sesión de otro día. Se guarda igual que la de hoy.
    </p>

    <p
      v-if="workout.pendingCount"
      class="mb-3 rounded-xl bg-amber-500/10 px-4 py-3 text-sm text-amber-300"
    >
      ⚠️ {{ workout.pendingCount }} serie(s) sin enviar. Se guardarán solas al recuperar la conexión.
    </p>

    <p v-if="workout.loading" class="py-12 text-center text-slate-400">Cargando tu sesión…</p>

    <StateBlock
      v-else-if="workout.error"
      icon="⚠️"
      title="No hemos podido cargar la sesión"
      :message="workout.error"
    >
      <button type="button" class="btn-primary mt-2" @click="workout.loadDay(dia)">Reintentar</button>
    </StateBlock>

    <StateBlock
      v-else-if="!workout.routines.length"
      icon="😴"
      :title="esHoy ? 'Hoy no tienes batería asignada' : 'Ese día no tenías batería asignada'"
      message="Cuando el entrenador dé de alta la sesión aparecerá aquí."
    >
      <RouterLink to="/mis-sesiones" class="btn-ghost mt-2">Ver sesiones anteriores</RouterLink>
    </StateBlock>

    <template v-else>
      <section class="card mb-4">
        <div class="mb-3 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h2 class="truncate text-lg font-bold">{{ headline }}</h2>
            <p class="text-sm text-slate-400">
              {{ workout.allItems.length }}
              {{ workout.allItems.length === 1 ? 'ejercicio' : 'ejercicios' }}
              · {{ workout.totalSets }} {{ workout.totalSets === 1 ? 'serie' : 'series' }}
            </p>
          </div>
          <span
            class="chip shrink-0"
            :class="
              workout.isComplete ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-800 text-slate-300'
            "
          >
            {{ workout.loggedSets }}/{{ workout.totalSets }}
          </span>
        </div>

        <div class="h-2 overflow-hidden rounded-full bg-slate-800">
          <div
            class="h-full rounded-full transition-all duration-300"
            :class="workout.isComplete ? 'bg-emerald-500' : 'bg-brand-500'"
            :style="{ width: `${progress}%` }"
          />
        </div>

        <p v-if="workout.isComplete" class="mt-3 text-sm font-semibold text-emerald-400">
          ✅ Sesión completada. ¡Buen trabajo!
        </p>
      </section>

      <!-- Normalmente hay una sola batería; si el entrenador asigna un extra, van seguidas. -->
      <section v-for="routine in workout.routines" :key="routine.id" class="mb-4 last:mb-0">
        <div v-if="workout.routines.length > 1" class="mb-2 px-1">
          <h3 class="font-bold">{{ routine.name }}</h3>
        </div>
        <p v-if="routine.notes" class="mb-3 px-1 text-sm italic text-slate-400">
          {{ routine.notes }}
        </p>

        <div class="space-y-3">
          <ExerciseCard
            v-for="item in routine.items"
            :key="item.id"
            :item="item"
            :is-saving="workout.isSaving"
            :is-pending="workout.isPending"
            :start-open="item.id === firstPendingId"
            @save="onSave"
          />
        </div>
      </section>
    </template>
  </AppShell>
</template>
