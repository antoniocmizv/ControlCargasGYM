<script setup>
import { onMounted, ref } from 'vue'

const offline = ref(!navigator.onLine)

onMounted(() => {
  window.addEventListener('online', () => (offline.value = false))
  window.addEventListener('offline', () => (offline.value = true))
})
</script>

<template>
  <RouterView />
  <!-- Abajo para no tapar la cabecera, que es sticky. -->
  <div
    v-if="offline"
    class="fixed inset-x-0 bottom-0 z-50 bg-amber-500 px-4 py-2 text-center text-xs font-semibold text-amber-950"
    style="padding-bottom: calc(0.5rem + env(safe-area-inset-bottom))"
  >
    Sin conexión · tus cargas se guardarán al volver la red
  </div>
</template>
