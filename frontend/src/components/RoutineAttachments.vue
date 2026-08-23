<script setup>
import { onMounted } from 'vue'

import { pesoLegible, useAdjuntos } from '@/composables/useAdjuntos'

const props = defineProps({
  routineId: { type: Number, required: true }
})

const { adjuntos, error, cargar, abrir } = useAdjuntos(props.routineId)

onMounted(cargar)
</script>

<template>
  <div v-if="adjuntos.length" class="space-y-2">
    <button
      v-for="adjunto in adjuntos"
      :key="adjunto.id"
      type="button"
      class="flex w-full items-center gap-3 rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-left transition active:scale-[0.98] hover:border-brand-600"
      @click="abrir(adjunto)"
    >
      <span class="text-xl">📄</span>
      <span class="min-w-0 flex-1">
        <span class="block truncate font-semibold">{{ adjunto.filename }}</span>
        <span class="text-xs text-slate-500">PDF · {{ pesoLegible(adjunto.size_bytes) }}</span>
      </span>
      <span class="shrink-0 text-xs font-semibold text-brand-400">Abrir</span>
    </button>

    <p v-if="error" class="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-300">{{ error }}</p>
  </div>
</template>
