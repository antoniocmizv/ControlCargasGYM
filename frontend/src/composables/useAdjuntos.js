import { ref } from 'vue'

import { api } from '@/api/client'

/**
 * La sesión viaja en la cabecera Authorization, así que un enlace normal al PDF
 * daría 401: hay que traerlo como blob y abrirlo con un object URL.
 */
export function useAdjuntos(routineId) {
  const adjuntos = ref([])
  const cargando = ref(false)
  const error = ref('')

  async function cargar() {
    if (!routineId) return
    cargando.value = true
    try {
      adjuntos.value = await api.get(`/routines/${routineId}/adjuntos`)
      error.value = ''
    } catch (err) {
      error.value = err.message
    } finally {
      cargando.value = false
    }
  }

  async function abrir(adjunto) {
    error.value = ''
    try {
      const respuesta = await api.download(`/routines/${routineId}/adjuntos/${adjunto.id}`)
      const url = URL.createObjectURL(await respuesta.blob())
      const ventana = window.open(url, '_blank')
      if (!ventana) {
        // Con el bloqueador de ventanas activo, al menos que se descargue.
        const enlace = document.createElement('a')
        enlace.href = url
        enlace.download = adjunto.filename
        enlace.click()
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (err) {
      error.value = err.message
    }
  }

  return { adjuntos, cargando, error, cargar, abrir }
}

export function pesoLegible(bytes) {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`
  return `${bytes} B`
}
