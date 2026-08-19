<script setup>
import { computed, ref } from 'vue'

import NumberStepper from '@/components/NumberStepper.vue'

const props = defineProps({
  item: { type: Object, required: true },
  isSaving: { type: Function, required: true },
  isPending: { type: Function, required: true },
  startOpen: { type: Boolean, default: false }
})

const emit = defineEmits(['save'])

const open = ref(props.startOpen)
const draft = ref({})

/** Una fila por serie, ya rellena con lo que el jugador tenga guardado. */
const rows = computed(() =>
  Array.from({ length: props.item.sets }, (_, index) => {
    const number = index + 1
    const log = props.item.logs.find((entry) => entry.set_number === number)
    return {
      number,
      loadKg: log ? Number(log.load_kg) : null,
      reps: log ? log.reps : null,
      done: Boolean(log)
    }
  })
)

const doneCount = computed(() => rows.value.filter((row) => row.done).length)
const complete = computed(() => doneCount.value === props.item.sets)

function valueFor(row, field) {
  const key = `${row.number}:${field}`
  return key in draft.value ? draft.value[key] : row[field]
}

function setDraft(row, field, value) {
  draft.value = { ...draft.value, [`${row.number}:${field}`]: value }
}

function commit(row) {
  const loadKg = valueFor(row, 'loadKg')
  if (loadKg === null || loadKg === undefined) return
  const reps = valueFor(row, 'reps') ?? props.item.target_reps ?? null
  setDraft(row, 'reps', reps)
  emit('save', { itemId: props.item.id, setNumber: row.number, loadKg, reps })
}

function previousLoad(row) {
  const previous = rows.value.find((entry) => entry.number === row.number - 1)
  return previous ? valueFor(previous, 'loadKg') : null
}

/** Copia la carga de la serie anterior: lo habitual es repetir peso. */
function repeatPrevious(row) {
  const previous = rows.value.find((entry) => entry.number === row.number - 1)
  const load = previousLoad(row)
  if (load === null || load === undefined) return
  setDraft(row, 'loadKg', load)
  setDraft(row, 'reps', valueFor(previous, 'reps') ?? props.item.target_reps ?? null)
  commit(row)
}
</script>

<template>
  <article class="card overflow-hidden !p-0">
    <button type="button" class="flex w-full items-center gap-3 p-4 text-left" @click="open = !open">
      <span
        class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold"
        :class="complete ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'"
      >
        {{ complete ? '✓' : item.position + 1 }}
      </span>
      <div class="min-w-0 flex-1">
        <h3 class="truncate font-bold leading-tight">{{ item.exercise.name }}</h3>
        <p class="mt-0.5 truncate text-sm text-slate-400">
          {{ item.sets }} series
          <template v-if="item.target_reps"> × {{ item.target_reps }} reps</template>
          <template v-if="item.rest_seconds"> · {{ item.rest_seconds }}s</template>
        </p>
      </div>
      <span
        class="chip shrink-0"
        :class="complete ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-800 text-slate-400'"
      >
        {{ doneCount }}/{{ item.sets }}
      </span>
      <span class="shrink-0 text-slate-600 transition" :class="open && 'rotate-90'">›</span>
    </button>

    <div v-if="open" class="border-t border-slate-800 p-4">
      <p
        v-if="item.last_performance"
        class="mb-3 rounded-lg bg-slate-800/60 px-3 py-2 text-xs text-slate-400"
      >
        📈 Última vez ({{ new Date(item.last_performance.session_date).toLocaleDateString('es-ES') }}):
        <strong class="text-slate-200">{{ item.last_performance.best_load_kg }} kg</strong>
        <template v-if="item.last_performance.reps"> × {{ item.last_performance.reps }} reps</template>
      </p>

      <p v-if="item.notes" class="mb-3 text-sm italic text-slate-400">{{ item.notes }}</p>

      <div class="space-y-3">
        <div
          v-for="row in rows"
          :key="row.number"
          class="rounded-xl p-3 transition"
          :class="
            !row.done
              ? 'bg-slate-800/40'
              : isPending(item.id, row.number)
                ? 'bg-amber-500/5 ring-1 ring-amber-500/25'
                : 'bg-emerald-500/5 ring-1 ring-emerald-500/20'
          "
        >
          <div class="mb-2 flex items-center justify-between gap-2">
            <span class="text-sm font-bold text-slate-300">Serie {{ row.number }}</span>
            <span v-if="isSaving(item.id, row.number)" class="text-xs text-slate-500">guardando…</span>
            <span
              v-else-if="row.done && isPending(item.id, row.number)"
              class="text-xs font-semibold text-amber-400"
            >
              ⏳ sin enviar
            </span>
            <span v-else-if="row.done" class="text-xs font-semibold text-emerald-400">✓ guardado</span>
            <button
              v-else-if="previousLoad(row) !== null && previousLoad(row) !== undefined"
              type="button"
              class="text-xs font-semibold text-brand-400"
              @click="repeatPrevious(row)"
            >
              = a la anterior
            </button>
          </div>

          <NumberStepper
            :model-value="valueFor(row, 'loadKg')"
            :step="2.5"
            :max="500"
            suffix="kg"
            @update:model-value="setDraft(row, 'loadKg', $event)"
            @commit="commit(row)"
          />

          <div class="mt-2 flex items-center gap-3">
            <span class="text-xs font-medium uppercase tracking-wide text-slate-500">Reps</span>
            <div class="ml-auto w-40">
              <NumberStepper
                :model-value="valueFor(row, 'reps')"
                :step="1"
                :max="200"
                compact
                :placeholder="String(item.target_reps ?? 0)"
                @update:model-value="setDraft(row, 'reps', $event)"
                @commit="commit(row)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </article>
</template>
