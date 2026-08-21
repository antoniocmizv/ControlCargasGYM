<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'

const route = useRoute()
const router = useRouter()

const routineId = computed(() => route.params.id || null)
const isEdit = computed(() => Boolean(routineId.value))

const name = ref('')
const sessionDate = ref(new Date().toISOString().slice(0, 10))
const notes = ref('')
const items = ref([])
const target = ref('all')
const selectedGroups = ref([])
const selectedPlayers = ref([])

const exercises = ref([])
const groups = ref([])
const players = ref([])
const picking = ref(false)
const pickerSearch = ref('')
const loading = ref(true)
const saving = ref(false)
const error = ref('')

const byCategory = computed(() => {
  const term = pickerSearch.value.trim().toLowerCase()
  const list = term
    ? exercises.value.filter((ex) => ex.name.toLowerCase().includes(term))
    : exercises.value
  return list.reduce((acc, exercise) => {
    const key = exercise.category || 'Otros'
    ;(acc[key] ||= []).push(exercise)
    return acc
  }, {})
})

const totalSets = computed(() => items.value.reduce((acc, item) => acc + Number(item.sets || 0), 0))

onMounted(async () => {
  try {
    const [exerciseList, groupList, playerList] = await Promise.all([
      api.get('/coach/exercises'),
      api.get('/coach/groups'),
      api.get('/coach/players')
    ])
    exercises.value = exerciseList
    groups.value = groupList
    players.value = playerList

    if (isEdit.value) await loadRoutine()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})

async function loadRoutine() {
  const routine = await api.get(`/coach/routines/${routineId.value}`)
  name.value = routine.name
  sessionDate.value = routine.session_date
  notes.value = routine.notes || ''
  items.value = routine.items.map((item) => ({
    id: item.id,
    exercise_id: item.exercise.id,
    exercise_name: item.exercise.name,
    sets: item.sets,
    target_reps: item.target_reps,
    rest_seconds: item.rest_seconds,
    notes: item.notes
  }))

  const assignments = routine.assignments
  if (assignments.some((a) => a.target_type === 'all')) {
    target.value = 'all'
  } else if (assignments.some((a) => a.target_type === 'group')) {
    target.value = 'group'
    selectedGroups.value = assignments.filter((a) => a.group_id).map((a) => a.group_id)
  } else {
    target.value = 'player'
    selectedPlayers.value = assignments.filter((a) => a.user_id).map((a) => a.user_id)
  }
}

function addExercise(exercise) {
  items.value.push({
    id: null,
    exercise_id: exercise.id,
    exercise_name: exercise.name,
    sets: 3,
    target_reps: 8,
    rest_seconds: 120,
    notes: ''
  })
  picking.value = false
  pickerSearch.value = ''
}

function removeItem(index) {
  items.value.splice(index, 1)
}

function move(index, delta) {
  const next = index + delta
  if (next < 0 || next >= items.value.length) return
  const copy = [...items.value]
  ;[copy[index], copy[next]] = [copy[next], copy[index]]
  items.value = copy
}

/**
 * La plantilla desenvuelve los refs, asi que el ref hay que tocarlo aqui:
 * pasarlo como argumento desde el `@click` entregaba el array pelado.
 */
function toggleSeleccion(seleccion, value) {
  seleccion.value = seleccion.value.includes(value)
    ? seleccion.value.filter((entry) => entry !== value)
    : [...seleccion.value, value]
}

const toggleGroup = (id) => toggleSeleccion(selectedGroups, id)
const togglePlayer = (id) => toggleSeleccion(selectedPlayers, id)

function buildAssignments() {
  if (target.value === 'all') return [{ target_type: 'all' }]
  if (target.value === 'group')
    return selectedGroups.value.map((id) => ({ target_type: 'group', group_id: id }))
  return selectedPlayers.value.map((id) => ({ target_type: 'player', user_id: id }))
}

async function save() {
  error.value = ''
  const assignments = buildAssignments()

  if (!name.value.trim()) return (error.value = 'Ponle un nombre a la batería')
  if (!items.value.length) return (error.value = 'Añade al menos un ejercicio')
  if (!assignments.length) return (error.value = 'Elige a quién va dirigida la batería')

  saving.value = true
  try {
    const payload = {
      name: name.value.trim(),
      session_date: sessionDate.value,
      notes: notes.value.trim() || null,
      items: items.value.map((item) => ({
        id: item.id ?? null,
        exercise_id: item.exercise_id,
        sets: Number(item.sets) || 1,
        target_reps: item.target_reps ? Number(item.target_reps) : null,
        rest_seconds: item.rest_seconds ? Number(item.rest_seconds) : null,
        notes: item.notes || null
      })),
      assignments
    }
    if (isEdit.value) await api.put(`/coach/routines/${routineId.value}`, payload)
    else await api.post('/coach/routines', payload)
    router.push('/panel')
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppShell
    :title="isEdit ? 'Editar batería' : 'Nueva batería'"
    :subtitle="items.length ? `${items.length} ejercicios · ${totalSets} series` : 'Da de alta la sesión'"
    back="/panel"
  >
    <p v-if="loading" class="py-10 text-center text-slate-400">Cargando…</p>

    <form v-else class="space-y-5" @submit.prevent="save">
      <section class="card space-y-4">
        <div>
          <label class="label" for="nombre">Nombre de la sesión</label>
          <input
            id="nombre"
            v-model="name"
            class="field"
            placeholder="Ej. Fuerza tren inferior"
            required
          />
        </div>
        <div>
          <label class="label" for="fecha">Día</label>
          <input id="fecha" v-model="sessionDate" type="date" class="field" required />
        </div>
        <div>
          <label class="label" for="notas">Notas (opcional)</label>
          <textarea
            id="notas"
            v-model="notes"
            rows="2"
            class="field"
            placeholder="Indicaciones para el equipo"
          />
        </div>
      </section>

      <!-- A quien va dirigida -->
      <section class="card">
        <h2 class="mb-3 font-bold">¿Para quién?</h2>
        <div class="mb-3 grid grid-cols-3 gap-2">
          <button
            v-for="option in [
              { value: 'all', label: 'Equipo' },
              { value: 'group', label: 'Grupos' },
              { value: 'player', label: 'Jugadores' }
            ]"
            :key="option.value"
            type="button"
            class="btn !text-sm"
            :class="target === option.value ? 'bg-brand-600 text-white' : 'bg-slate-800 text-slate-300'"
            @click="target = option.value"
          >
            {{ option.label }}
          </button>
        </div>

        <p v-if="target === 'all'" class="text-sm text-slate-400">
          La verán todos los jugadores activos del equipo.
        </p>

        <div v-else-if="target === 'group'" class="flex flex-wrap gap-2">
          <button
            v-for="group in groups"
            :key="group.id"
            type="button"
            class="chip border"
            :class="
              selectedGroups.includes(group.id)
                ? 'border-brand-500 bg-brand-600/20 text-brand-200'
                : 'border-slate-700 text-slate-400'
            "
            @click="toggleGroup(group.id)"
          >
            {{ group.name }}
          </button>
          <p v-if="!groups.length" class="text-sm text-slate-400">
            No hay grupos todavía.
            <RouterLink to="/panel/jugadores" class="text-brand-400 underline">Crear uno</RouterLink>
          </p>
        </div>

        <div v-else class="flex flex-wrap gap-2">
          <button
            v-for="player in players"
            :key="player.id"
            type="button"
            class="chip border"
            :class="
              selectedPlayers.includes(player.id)
                ? 'border-brand-500 bg-brand-600/20 text-brand-200'
                : 'border-slate-700 text-slate-400'
            "
            @click="togglePlayer(player.id)"
          >
            {{ player.name }}
          </button>
        </div>
      </section>

      <!-- Ejercicios -->
      <section>
        <div class="mb-2 flex items-center justify-between">
          <h2 class="font-bold">Ejercicios</h2>
          <button type="button" class="text-sm font-semibold text-brand-400" @click="picking = true">
            + Añadir
          </button>
        </div>

        <!-- Nota aparte de la cadena v-if/v-else: no debe sustituir a la lista. -->
        <p v-if="isEdit && items.length" class="mb-2 px-1 text-xs text-slate-500">
          Puedes cambiar nombre, fecha, series o descansos sin perder lo ya registrado. Quitar un
          ejercicio o recortar sus series sí borra esas cargas.
        </p>

        <p v-if="!items.length" class="card py-8 text-center text-sm text-slate-400">
          Añade el primer ejercicio de la batería.
        </p>

        <div v-else class="space-y-3">
          <article v-for="(item, index) in items" :key="index" class="card !p-3">
            <div class="mb-3 flex items-center gap-2">
              <span class="text-sm font-bold text-slate-500">{{ index + 1 }}</span>
              <p class="min-w-0 flex-1 truncate font-semibold">{{ item.exercise_name }}</p>
              <button type="button" class="btn-ghost !min-h-0 !px-2 !py-1" @click="move(index, -1)">↑</button>
              <button type="button" class="btn-ghost !min-h-0 !px-2 !py-1" @click="move(index, 1)">↓</button>
              <button type="button" class="btn-danger !min-h-0 !px-2 !py-1" @click="removeItem(index)">
                ✕
              </button>
            </div>

            <div class="grid grid-cols-3 gap-2">
              <label class="block">
                <span class="label !mb-1 !text-xs">Series</span>
                <input v-model.number="item.sets" type="number" min="1" max="20" class="field !py-2 text-center" />
              </label>
              <label class="block">
                <span class="label !mb-1 !text-xs">Reps</span>
                <input v-model.number="item.target_reps" type="number" min="1" max="200" class="field !py-2 text-center" />
              </label>
              <label class="block">
                <span class="label !mb-1 !text-xs">Descanso (s)</span>
                <input v-model.number="item.rest_seconds" type="number" min="0" max="600" step="15" class="field !py-2 text-center" />
              </label>
            </div>
          </article>
        </div>
      </section>

      <p v-if="error" class="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{{ error }}</p>

      <button type="submit" class="btn-primary w-full" :disabled="saving">
        {{ saving ? 'Guardando…' : isEdit ? 'Guardar cambios' : 'Dar de alta la sesión' }}
      </button>
    </form>

    <!-- Selector de ejercicios -->
    <div
      v-if="picking"
      class="fixed inset-0 z-40 flex items-end bg-black/70 sm:items-center sm:p-4"
      @click.self="picking = false"
    >
      <div class="flex max-h-[85vh] w-full flex-col rounded-t-2xl bg-slate-900 sm:mx-auto sm:max-w-md sm:rounded-2xl">
        <div class="flex items-center gap-2 border-b border-slate-800 p-4">
          <input v-model="pickerSearch" class="field" placeholder="Buscar ejercicio" autocomplete="off" />
          <button type="button" class="btn-ghost !px-3" @click="picking = false">✕</button>
        </div>
        <div class="overflow-y-auto p-4">
          <div v-for="(list, category) in byCategory" :key="category" class="mb-4">
            <h3 class="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {{ category }}
            </h3>
            <button
              v-for="exercise in list"
              :key="exercise.id"
              type="button"
              class="mb-1.5 w-full rounded-xl bg-slate-800 px-4 py-3 text-left font-medium transition active:scale-[0.98]"
              @click="addExercise(exercise)"
            >
              {{ exercise.name }}
            </button>
          </div>
          <p v-if="!Object.keys(byCategory).length" class="py-6 text-center text-sm text-slate-400">
            Sin resultados.
            <RouterLink to="/panel/ejercicios" class="text-brand-400 underline">Crear ejercicio</RouterLink>
          </p>
        </div>
      </div>
    </div>
  </AppShell>
</template>
