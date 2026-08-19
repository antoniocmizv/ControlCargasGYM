<script setup>
import { computed, onMounted, ref } from 'vue'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'

const exercises = ref([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const editing = ref(null)
const form = ref({ name: '', category: '', description: '' })

const CATEGORIES = ['Pierna', 'Pecho', 'Espalda', 'Hombro', 'Brazo', 'Glúteo', 'Core', 'Otros']

const grouped = computed(() =>
  exercises.value.reduce((acc, exercise) => {
    const key = exercise.category || 'Otros'
    ;(acc[key] ||= []).push(exercise)
    return acc
  }, {})
)

async function load() {
  try {
    exercises.value = await api.get('/coach/exercises')
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openNew() {
  editing.value = 'new'
  form.value = { name: '', category: '', description: '' }
}

function openEdit(exercise) {
  editing.value = exercise.id
  form.value = {
    name: exercise.name,
    category: exercise.category || '',
    description: exercise.description || ''
  }
}

async function submit() {
  error.value = ''
  busy.value = true
  try {
    const payload = {
      name: form.value.name.trim(),
      category: form.value.category || null,
      description: form.value.description.trim() || null
    }
    if (editing.value === 'new') await api.post('/coach/exercises', payload)
    else await api.patch(`/coach/exercises/${editing.value}`, payload)
    editing.value = null
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function remove(exercise) {
  if (!window.confirm(`¿Quitar «${exercise.name}» del catalogo?`)) return
  busy.value = true
  try {
    await api.delete(`/coach/exercises/${exercise.id}`)
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AppShell title="Ejercicios" :subtitle="`${exercises.length} en el catalogo`" back="/panel">
    <p v-if="error" class="mb-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{{ error }}</p>

    <button type="button" class="btn-primary mb-5 w-full" @click="openNew">+ Nuevo ejercicio</button>

    <p v-if="loading" class="py-10 text-center text-slate-400">Cargando…</p>

    <div v-else class="space-y-5">
      <section v-for="(list, category) in grouped" :key="category">
        <h2 class="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">{{ category }}</h2>
        <div class="space-y-2">
          <article
            v-for="exercise in list"
            :key="exercise.id"
            class="card flex items-center gap-3 !p-3"
          >
            <div class="min-w-0 flex-1">
              <p class="truncate font-semibold">{{ exercise.name }}</p>
              <p v-if="exercise.description" class="truncate text-xs text-slate-500">
                {{ exercise.description }}
              </p>
            </div>
            <button type="button" class="btn-ghost !min-h-0 !px-3 !py-1.5 !text-sm" @click="openEdit(exercise)">
              Editar
            </button>
            <button type="button" class="btn-danger !min-h-0 !px-3 !py-1.5" :disabled="busy" @click="remove(exercise)">
              🗑
            </button>
          </article>
        </div>
      </section>
    </div>

    <div
      v-if="editing"
      class="fixed inset-0 z-40 flex items-end bg-black/70 sm:items-center sm:p-4"
      @click.self="editing = null"
    >
      <form
        class="w-full space-y-4 rounded-t-2xl bg-slate-900 p-5 sm:mx-auto sm:max-w-md sm:rounded-2xl"
        @submit.prevent="submit"
      >
        <h2 class="text-lg font-bold">
          {{ editing === 'new' ? 'Nuevo ejercicio' : 'Editar ejercicio' }}
        </h2>

        <div>
          <label class="label" for="ename">Nombre</label>
          <input id="ename" v-model="form.name" class="field" placeholder="Ej. Sentadilla trasera" required />
        </div>

        <div>
          <label class="label" for="ecat">Categoría</label>
          <select id="ecat" v-model="form.category" class="field">
            <option value="">Sin categoría</option>
            <option v-for="category in CATEGORIES" :key="category" :value="category">
              {{ category }}
            </option>
          </select>
        </div>

        <div>
          <label class="label" for="edesc">Descripción (opcional)</label>
          <textarea id="edesc" v-model="form.description" rows="2" class="field" />
        </div>

        <div class="flex gap-2 pt-1">
          <button type="button" class="btn-ghost flex-1" @click="editing = null">Cancelar</button>
          <button type="submit" class="btn-primary flex-1" :disabled="busy">Guardar</button>
        </div>
      </form>
    </div>
  </AppShell>
</template>
