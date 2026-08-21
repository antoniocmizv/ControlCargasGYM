<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  points: { type: Array, required: true },
  label: { type: String, default: 'Peso máximo' }
})

// Azul validado contra la superficie oscura de las tarjetas (#0f172a).
const SERIE = '#3987e5'

const W = 320
const H = 160
const PAD = { top: 16, right: 14, bottom: 26, left: 34 }

const hover = ref(null)

const escala = computed(() => {
  const valores = props.points.map((p) => p.best_load_kg)
  const min = Math.min(...valores)
  const max = Math.max(...valores)
  // Un margen para que la línea no se pegue a los bordes; si no varía, se centra.
  const margen = max === min ? Math.max(max * 0.1, 2.5) : (max - min) * 0.2
  return { min: Math.max(0, min - margen), max: max + margen }
})

const coords = computed(() => {
  const { min, max } = escala.value
  const ancho = W - PAD.left - PAD.right
  const alto = H - PAD.top - PAD.bottom
  const n = props.points.length
  return props.points.map((punto, i) => ({
    ...punto,
    x: PAD.left + (n === 1 ? ancho / 2 : (ancho * i) / (n - 1)),
    y: PAD.top + alto - ((punto.best_load_kg - min) / (max - min || 1)) * alto
  }))
})

const linea = computed(() => coords.value.map((p) => `${p.x},${p.y}`).join(' '))

const marcasY = computed(() => {
  const { min, max } = escala.value
  return [max, (max + min) / 2, min].map((valor) => ({
    valor: Math.round(valor * 10) / 10,
    y: PAD.top + (H - PAD.top - PAD.bottom) * ((max - valor) / (max - min || 1))
  }))
})

const dia = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })

/** Solo se etiquetan los extremos: un número por punto satura el gráfico. */
const destacados = computed(() => {
  const n = coords.value.length
  if (n <= 1) return coords.value
  return [coords.value[0], coords.value[n - 1]]
})
</script>

<template>
  <figure class="m-0">
    <figcaption class="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
      {{ label }} por sesión (kg)
    </figcaption>

    <svg
      :viewBox="`0 0 ${W} ${H}`"
      class="w-full"
      role="img"
      :aria-label="`Evolución de ${label.toLowerCase()}: de ${points[0]?.best_load_kg} a ${points[points.length - 1]?.best_load_kg} kilos`"
      @mouseleave="hover = null"
    >
      <!-- Rejilla discreta -->
      <g>
        <line
          v-for="marca in marcasY"
          :key="marca.valor"
          :x1="PAD.left"
          :x2="W - PAD.right"
          :y1="marca.y"
          :y2="marca.y"
          stroke="#1e293b"
          stroke-width="1"
        />
        <text
          v-for="marca in marcasY"
          :key="`t-${marca.valor}`"
          :x="PAD.left - 6"
          :y="marca.y + 3"
          text-anchor="end"
          fill="#64748b"
          font-size="8"
        >
          {{ marca.valor }}
        </text>
      </g>

      <polyline
        :points="linea"
        fill="none"
        :stroke="SERIE"
        stroke-width="2"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <g v-for="punto in coords" :key="punto.session_date">
        <!-- Anillo del color de la superficie: separa el punto de la línea -->
        <circle :cx="punto.x" :cy="punto.y" r="4.5" fill="#0f172a" />
        <circle :cx="punto.x" :cy="punto.y" r="3.2" :fill="SERIE" />
        <!-- Zona de toque generosa para el dedo -->
        <circle
          :cx="punto.x"
          :cy="punto.y"
          r="16"
          fill="transparent"
          @mouseenter="hover = punto"
          @touchstart.passive="hover = punto"
        />
      </g>

      <text
        v-for="punto in destacados"
        :key="`l-${punto.session_date}`"
        :x="punto.x"
        :y="punto.y - 10"
        text-anchor="middle"
        fill="#e2e8f0"
        font-size="9"
        font-weight="700"
      >
        {{ punto.best_load_kg }}
      </text>

      <text
        v-if="coords.length"
        :x="coords[0].x"
        :y="H - 8"
        text-anchor="start"
        fill="#64748b"
        font-size="8"
      >
        {{ dia(coords[0].session_date) }}
      </text>
      <text
        v-if="coords.length > 1"
        :x="coords[coords.length - 1].x"
        :y="H - 8"
        text-anchor="end"
        fill="#64748b"
        font-size="8"
      >
        {{ dia(coords[coords.length - 1].session_date) }}
      </text>
    </svg>

    <p
      class="mt-1 min-h-[2.5rem] rounded-lg bg-slate-800/60 px-3 py-2 text-xs"
      :class="hover ? 'text-slate-300' : 'text-slate-600'"
    >
      <template v-if="hover">
        <strong class="text-slate-100">{{ hover.best_load_kg }} kg</strong>
        · {{ dia(hover.session_date) }} · {{ hover.sets }} series
        <template v-if="hover.total_volume"> · volumen {{ Math.round(hover.total_volume) }} kg</template>
      </template>
      <template v-else>Toca un punto para ver el detalle de esa sesión.</template>
    </p>
  </figure>
</template>
