<script setup>
import { onMounted, ref } from 'vue'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'

const players = ref([])
const playerId = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const busy = ref(false)
const error = ref('')
const done = ref(false)

onMounted(async () => {
  try {
    players.value = await api.get('/coach/players')
  } catch (err) {
    error.value = err.message
  }
})

/** Atajos: la mayoria de descargas son "la semana" o "el mes". */
function setRange(days) {
  const to = new Date()
  const from = new Date()
  from.setDate(to.getDate() - days)
  dateFrom.value = from.toISOString().slice(0, 10)
  dateTo.value = to.toISOString().slice(0, 10)
}

async function download() {
  busy.value = true
  error.value = ''
  done.value = false
  try {
    const response = await api.download('/export/excel', {
      date_from: dateFrom.value,
      date_to: dateTo.value,
      player_id: playerId.value
    })
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `cargas_${new Date().toISOString().slice(0, 10)}.xlsx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    done.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AppShell title="Exportar a Excel" subtitle="Descarga las cargas registradas" back="/panel">
    <section class="card space-y-4">
      <div>
        <span class="label">Período rápido</span>
        <div class="grid grid-cols-3 gap-2">
          <button type="button" class="btn-ghost !text-sm" @click="setRange(7)">7 días</button>
          <button type="button" class="btn-ghost !text-sm" @click="setRange(30)">30 días</button>
          <button type="button" class="btn-ghost !text-sm" @click="setRange(90)">90 días</button>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <label class="block">
          <span class="label">Desde</span>
          <input v-model="dateFrom" type="date" class="field" />
        </label>
        <label class="block">
          <span class="label">Hasta</span>
          <input v-model="dateTo" type="date" class="field" />
        </label>
      </div>

      <label class="block">
        <span class="label">Jugador</span>
        <select v-model="playerId" class="field">
          <option value="">Todo el equipo</option>
          <option v-for="player in players" :key="player.id" :value="player.id">
            {{ player.name }}
          </option>
        </select>
      </label>

      <button type="button" class="btn-primary w-full" :disabled="busy" @click="download">
        {{ busy ? 'Generando…' : '⬇ Descargar .xlsx' }}
      </button>

      <p v-if="done" class="rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
        Archivo generado. Revisa tus descargas.
      </p>
      <p v-if="error" class="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{{ error }}</p>
    </section>

    <p class="mt-4 px-1 text-sm text-slate-500">
      El archivo trae dos hojas: <strong>Cargas</strong> con el detalle serie a serie y
      <strong>Resumen</strong> con kg máximo, medio y volumen por jugador y ejercicio. Deja las fechas
      vacias para exportar todo el histórico.
    </p>
  </AppShell>
</template>
