import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { ApiError, api } from '@/api/client'

const QUEUE_KEY = 'cargas_pendientes'

function loadQueue() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY)) || []
  } catch {
    return []
  }
}

/** Clave de una serie concreta: identifica el registro dentro de la cola. */
const keyOf = (itemId, setNumber) => `${itemId}:${setNumber}`

export const useWorkoutStore = defineStore('workout', () => {
  const routine = ref(null)
  const loading = ref(false)
  const error = ref('')
  const saving = ref(new Set())
  const queue = ref(loadQueue())

  const pendingCount = computed(() => queue.value.length)
  const totalSets = computed(() =>
    (routine.value?.items || []).reduce((acc, item) => acc + item.sets, 0)
  )
  const loggedSets = computed(() =>
    (routine.value?.items || []).reduce((acc, item) => acc + item.logs.length, 0)
  )
  const isComplete = computed(() => totalSets.value > 0 && loggedSets.value >= totalSets.value)

  function persistQueue() {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue.value))
  }

  async function loadToday(day) {
    loading.value = true
    error.value = ''
    try {
      routine.value = await api.get('/routines/today', day ? { day } : undefined)
      await flushQueue()
    } catch (err) {
      error.value = err.message
      routine.value = null
    } finally {
      loading.value = false
    }
  }

  /** Escribe el valor en memoria para que la UI responda al instante. */
  function applyLocally({ routine_exercise_id: itemId, set_number: setNumber, load_kg, reps }) {
    const item = routine.value?.items.find((entry) => entry.id === itemId)
    if (!item) return
    const existing = item.logs.find((log) => log.set_number === setNumber)
    if (existing) {
      existing.load_kg = load_kg
      existing.reps = reps
    } else {
      item.logs.push({ id: null, routine_exercise_id: itemId, set_number: setNumber, load_kg, reps })
      item.logs.sort((a, b) => a.set_number - b.set_number)
    }
  }

  function enqueue(payload) {
    queue.value = [
      ...queue.value.filter(
        (entry) =>
          keyOf(entry.routine_exercise_id, entry.set_number) !==
          keyOf(payload.routine_exercise_id, payload.set_number)
      ),
      payload
    ]
    persistQueue()
  }

  function dequeue(payload) {
    queue.value = queue.value.filter(
      (entry) =>
        keyOf(entry.routine_exercise_id, entry.set_number) !==
        keyOf(payload.routine_exercise_id, payload.set_number)
    )
    persistQueue()
  }

  /**
   * Guarda una serie. Si no hay red, queda encolada en localStorage y se
   * reintenta al volver la conexión: en un gimnasio la cobertura falla.
   */
  async function saveSet(itemId, setNumber, loadKg, reps) {
    const payload = {
      routine_exercise_id: itemId,
      set_number: setNumber,
      load_kg: loadKg,
      reps: reps ?? null
    }
    applyLocally(payload)

    const key = keyOf(itemId, setNumber)
    saving.value = new Set(saving.value).add(key)
    try {
      const saved = await api.post('/logs', payload)
      dequeue(payload)
      const item = routine.value?.items.find((entry) => entry.id === itemId)
      const local = item?.logs.find((log) => log.set_number === setNumber)
      if (local) local.id = saved.id
      return true
    } catch (err) {
      // Un fallo de red se reintenta; un rechazo del servidor no.
      if (err instanceof ApiError && err.status === 0) enqueue(payload)
      else error.value = err.message
      return false
    } finally {
      const next = new Set(saving.value)
      next.delete(key)
      saving.value = next
    }
  }

  async function flushQueue() {
    if (!queue.value.length) return
    for (const payload of [...queue.value]) {
      try {
        await api.post('/logs', payload)
        dequeue(payload)
      } catch {
        break // sigue sin haber red: lo dejamos para el próximo intento
      }
    }
  }

  function isSaving(itemId, setNumber) {
    return saving.value.has(keyOf(itemId, setNumber))
  }

  /** La serie está escrita en pantalla pero todavía no ha llegado al servidor. */
  function isPending(itemId, setNumber) {
    return queue.value.some(
      (entry) => keyOf(entry.routine_exercise_id, entry.set_number) === keyOf(itemId, setNumber)
    )
  }

  function reset() {
    routine.value = null
    error.value = ''
  }

  return {
    routine,
    loading,
    error,
    queue,
    pendingCount,
    totalSets,
    loggedSets,
    isComplete,
    loadToday,
    saveSet,
    flushQueue,
    isSaving,
    isPending,
    reset
  }
})
