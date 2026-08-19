<script setup>
import { onMounted, ref } from 'vue'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'

const players = ref([])
const groups = ref([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)

const editing = ref(null)
const form = ref({ name: '', pin: '', group_ids: [] })
const newGroup = ref('')

async function load() {
  try {
    const [playerList, groupList] = await Promise.all([
      api.get('/coach/players', { include_inactive: true }),
      api.get('/coach/groups')
    ])
    players.value = playerList
    groups.value = groupList
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
  form.value = { name: '', pin: '', group_ids: [] }
}

function openEdit(player) {
  editing.value = player.id
  form.value = { name: player.name, pin: '', group_ids: player.groups.map((g) => g.id) }
}

function toggleGroup(id) {
  const list = form.value.group_ids
  form.value.group_ids = list.includes(id) ? list.filter((entry) => entry !== id) : [...list, id]
}

async function submit() {
  error.value = ''
  if (!form.value.name.trim()) return (error.value = 'El nombre es obligatorio')

  busy.value = true
  try {
    if (editing.value === 'new') {
      if (!/^\d{4}$/.test(form.value.pin)) throw new Error('El PIN debe tener 4 dígitos')
      await api.post('/coach/players', {
        name: form.value.name.trim(),
        pin: form.value.pin,
        group_ids: form.value.group_ids
      })
    } else {
      const payload = { name: form.value.name.trim(), group_ids: form.value.group_ids }
      if (form.value.pin) {
        if (!/^\d{4}$/.test(form.value.pin)) throw new Error('El PIN debe tener 4 dígitos')
        payload.pin = form.value.pin
      }
      await api.patch(`/coach/players/${editing.value}`, payload)
    }
    editing.value = null
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function toggleActive(player) {
  busy.value = true
  try {
    await api.patch(`/coach/players/${player.id}`, { is_active: !player.is_active })
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function remove(player) {
  if (!window.confirm(`¿Eliminar a ${player.name} y todo su historial de cargas?`)) return
  busy.value = true
  try {
    await api.delete(`/coach/players/${player.id}`)
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function createGroup() {
  if (!newGroup.value.trim()) return
  busy.value = true
  try {
    await api.post('/coach/groups', { name: newGroup.value.trim() })
    newGroup.value = ''
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function removeGroup(group) {
  if (!window.confirm(`¿Eliminar el grupo «${group.name}»?`)) return
  busy.value = true
  try {
    await api.delete(`/coach/groups/${group.id}`)
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AppShell title="Jugadores" :subtitle="`${players.length} en plantilla`" back="/panel">
    <p v-if="error" class="mb-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{{ error }}</p>

    <button type="button" class="btn-primary mb-5 w-full" @click="openNew">+ Nuevo jugador</button>

    <p v-if="loading" class="py-10 text-center text-slate-400">Cargando…</p>

    <template v-else>
      <div class="mb-6 space-y-2">
        <article
          v-for="player in players"
          :key="player.id"
          class="card !p-3"
          :class="!player.is_active && 'opacity-50'"
        >
          <div class="flex items-center gap-3">
            <span
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-600/20 text-sm font-bold text-brand-300"
            >
              {{ player.name.slice(0, 2).toUpperCase() }}
            </span>
            <div class="min-w-0 flex-1">
              <p class="truncate font-semibold">{{ player.name }}</p>
              <p class="truncate text-xs text-slate-500">
                {{ player.groups.map((g) => g.name).join(', ') || 'Sin grupo' }}
                <span v-if="!player.is_active"> · inactivo</span>
              </p>
            </div>
            <button type="button" class="btn-ghost !min-h-0 !px-2 !py-1.5 !text-sm" @click="openEdit(player)">
              Editar
            </button>
          </div>
          <div class="mt-2 flex gap-2">
            <button type="button" class="btn-ghost flex-1 !min-h-0 !py-1.5 !text-xs" :disabled="busy" @click="toggleActive(player)">
              {{ player.is_active ? 'Desactivar' : 'Reactivar' }}
            </button>
            <button type="button" class="btn-danger !min-h-0 !px-3 !py-1.5 !text-xs" :disabled="busy" @click="remove(player)">
              Eliminar
            </button>
          </div>
        </article>
      </div>

      <section class="card">
        <h2 class="mb-3 font-bold">Grupos</h2>
        <div class="mb-3 flex flex-wrap gap-2">
          <span
            v-for="group in groups"
            :key="group.id"
            class="chip flex items-center gap-2 bg-slate-800 text-slate-300"
          >
            {{ group.name }}
            <button type="button" class="text-slate-500 hover:text-red-400" @click="removeGroup(group)">
              ✕
            </button>
          </span>
          <p v-if="!groups.length" class="text-sm text-slate-500">Sin grupos todavía.</p>
        </div>
        <form class="flex gap-2" @submit.prevent="createGroup">
          <input v-model="newGroup" class="field" placeholder="Ej. Porteros, Lesionados" />
          <button type="submit" class="btn-ghost" :disabled="busy">Añadir</button>
        </form>
      </section>
    </template>

    <!-- Alta / edición -->
    <div
      v-if="editing"
      class="fixed inset-0 z-40 flex items-end bg-black/70 sm:items-center sm:p-4"
      @click.self="editing = null"
    >
      <form
        class="w-full space-y-4 rounded-t-2xl bg-slate-900 p-5 sm:mx-auto sm:max-w-md sm:rounded-2xl"
        @submit.prevent="submit"
      >
        <h2 class="text-lg font-bold">{{ editing === 'new' ? 'Nuevo jugador' : 'Editar jugador' }}</h2>

        <div>
          <label class="label" for="jname">Nombre</label>
          <input id="jname" v-model="form.name" class="field" required />
        </div>

        <div>
          <label class="label" for="jpin">
            PIN de 4 dígitos
            <span v-if="editing !== 'new'" class="font-normal">(vacio = no cambiar)</span>
          </label>
          <input
            id="jpin"
            v-model="form.pin"
            inputmode="numeric"
            maxlength="4"
            pattern="\d{4}"
            class="field tracking-[0.4em]"
            placeholder="0000"
          />
        </div>

        <div v-if="groups.length">
          <span class="label">Grupos</span>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="group in groups"
              :key="group.id"
              type="button"
              class="chip border"
              :class="
                form.group_ids.includes(group.id)
                  ? 'border-brand-500 bg-brand-600/20 text-brand-200'
                  : 'border-slate-700 text-slate-400'
              "
              @click="toggleGroup(group.id)"
            >
              {{ group.name }}
            </button>
          </div>
        </div>

        <div class="flex gap-2 pt-1">
          <button type="button" class="btn-ghost flex-1" @click="editing = null">Cancelar</button>
          <button type="submit" class="btn-primary flex-1" :disabled="busy">Guardar</button>
        </div>
      </form>
    </div>
  </AppShell>
</template>
