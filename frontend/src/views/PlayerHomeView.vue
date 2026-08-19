<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/AppShell.vue'
import ExerciseCard from '@/components/ExerciseCard.vue'
import StateBlock from '@/components/StateBlock.vue'
import { useAuthStore } from '@/stores/auth'
import { useWorkoutStore } from '@/stores/workout'

const auth = useAuthStore()
const workout = useWorkoutStore()
const router = useRouter()

const today = computed(() =>
  new Date().toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' })
)

const progress = computed(() =>
  workout.totalSets ? Math.round((workout.loggedSets / workout.totalSets) * 100) : 0
)

/** Se despliega solo el ejercicio en curso; el resto queda plegado. */
const firstPendingId = computed(
  () => (workout.routine?.items || []).find((item) => item.logs.length < item.sets)?.id ?? null
)

onMounted(() => {
  workout.loadToday()
  window.addEventListener('online', workout.flushQueue)
})

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
  <AppShell :title="auth.user?.name || 'Mi sesión'" :subtitle="today">
    <template #actions>
      <RouterLink to="/mis-sesiones" class="btn-ghost h-11 w-11 !px-0" aria-label="Mis sesiones">
        🗓
      </RouterLink>
      <button type="button" class="btn-ghost h-11 w-11 !px-0" aria-label="Salir" @click="logout">
        ⏻
      </button>
    </template>

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
      <button type="button" class="btn-primary mt-2" @click="workout.loadToday()">Reintentar</button>
    </StateBlock>

    <StateBlock
      v-else-if="!workout.routine"
      icon="😴"
      title="Hoy no tienes batería asignada"
      message="Cuando el entrenador dé de alta la sesión aparecerá aquí."
    >
      <RouterLink to="/mis-sesiones" class="btn-ghost mt-2">Ver sesiones anteriores</RouterLink>
    </StateBlock>

    <template v-else>
      <section class="card mb-4">
        <div class="mb-3 flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h2 class="truncate text-lg font-bold">{{ workout.routine.name }}</h2>
            <p class="text-sm text-slate-400">
              {{ workout.routine.items.length }} ejercicios · {{ workout.totalSets }} series
            </p>
          </div>
          <span
            class="chip shrink-0"
            :class="workout.isComplete ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-800 text-slate-300'"
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

        <p v-if="workout.routine.notes" class="mt-3 text-sm italic text-slate-400">
          {{ workout.routine.notes }}
        </p>
        <p v-if="workout.isComplete" class="mt-3 text-sm font-semibold text-emerald-400">
          ✅ Sesión completada. ¡Buen trabajo!
        </p>
      </section>

      <div class="space-y-3">
        <ExerciseCard
          v-for="item in workout.routine.items"
          :key="item.id"
          :item="item"
          :is-saving="workout.isSaving"
          :is-pending="workout.isPending"
          :start-open="item.id === firstPendingId"
          @save="onSave"
        />
      </div>
    </template>
  </AppShell>
</template>
