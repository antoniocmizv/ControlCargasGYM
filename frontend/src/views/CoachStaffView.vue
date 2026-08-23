<script setup>
import { onMounted, ref } from 'vue'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const entrenadores = ref([])
const cargando = ref(true)
const ocupado = ref(false)
const error = ref('')
const creando = ref(false)
const form = ref({ name: '', username: '', password: '' })
const reseteando = ref(null)
const nuevaClave = ref('')

async function cargar() {
  try {
    entrenadores.value = await api.get('/coach/staff')
    error.value = ''
  } catch (err) {
    error.value = err.message
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)

async function crear() {
  error.value = ''
  if (form.value.password.length < 8) return (error.value = 'La contraseña necesita 8 caracteres')

  ocupado.value = true
  try {
    await api.post('/coach/staff', {
      name: form.value.name.trim(),
      username: form.value.username.trim().toLowerCase(),
      password: form.value.password
    })
    form.value = { name: '', username: '', password: '' }
    creando.value = false
    await cargar()
  } catch (err) {
    error.value = err.message
  } finally {
    ocupado.value = false
  }
}

async function alternarActivo(entrenador) {
  ocupado.value = true
  try {
    await api.patch(`/coach/staff/${entrenador.id}`, { is_active: !entrenador.is_active })
    await cargar()
  } catch (err) {
    error.value = err.message
  } finally {
    ocupado.value = false
  }
}

async function resetear() {
  error.value = ''
  if (nuevaClave.value.length < 8) return (error.value = 'La contraseña necesita 8 caracteres')

  ocupado.value = true
  try {
    await api.patch(`/coach/staff/${reseteando.value.id}`, { password: nuevaClave.value })
    reseteando.value = null
    nuevaClave.value = ''
    await cargar()
  } catch (err) {
    error.value = err.message
  } finally {
    ocupado.value = false
  }
}
</script>

<template>
  <AppShell title="Entrenadores" subtitle="Quién puede crear sesiones" back="/panel">
    <p v-if="error" class="mb-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{{ error }}</p>

    <button type="button" class="btn-primary mb-5 w-full" @click="creando = true">
      + Nuevo entrenador
    </button>

    <p v-if="cargando" class="py-10 text-center text-slate-400">Cargando…</p>

    <div v-else class="space-y-2">
      <article
        v-for="entrenador in entrenadores"
        :key="entrenador.id"
        class="card !p-3"
        :class="!entrenador.is_active && 'opacity-50'"
      >
        <div class="flex items-center gap-3">
          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold"
            :class="
              entrenador.role === 'admin'
                ? 'bg-amber-500/20 text-amber-300'
                : 'bg-brand-600/20 text-brand-300'
            "
          >
            {{ entrenador.name.slice(0, 2).toUpperCase() }}
          </span>
          <div class="min-w-0 flex-1">
            <p class="truncate font-semibold">
              {{ entrenador.name }}
              <span v-if="entrenador.id === auth.user?.id" class="text-xs text-slate-500">(tú)</span>
            </p>
            <p class="truncate text-xs text-slate-500">
              {{ entrenador.username }}
              <span v-if="entrenador.role === 'admin'"> · principal</span>
              <span v-if="!entrenador.is_active"> · desactivado</span>
            </p>
          </div>
        </div>

        <div v-if="entrenador.role !== 'admin'" class="mt-2 flex gap-2">
          <button
            type="button"
            class="btn-ghost flex-1 !min-h-0 !py-1.5 !text-xs"
            :disabled="ocupado"
            @click="reseteando = entrenador"
          >
            Cambiar contraseña
          </button>
          <button
            type="button"
            class="btn-ghost !min-h-0 !px-3 !py-1.5 !text-xs"
            :disabled="ocupado"
            @click="alternarActivo(entrenador)"
          >
            {{ entrenador.is_active ? 'Desactivar' : 'Reactivar' }}
          </button>
        </div>
      </article>
    </div>

    <p class="mt-4 px-1 text-sm text-slate-500">
      Los entrenadores pueden crear sesiones, gestionar jugadores y ejercicios, ver los pesos y
      exportar. Solo el principal da de alta a otros entrenadores.
    </p>

    <!-- Alta -->
    <div
      v-if="creando"
      class="fixed inset-0 z-40 flex items-end bg-black/70 sm:items-center sm:p-4"
      @click.self="creando = false"
    >
      <form
        class="w-full space-y-4 rounded-t-2xl bg-slate-900 p-5 sm:mx-auto sm:max-w-md sm:rounded-2xl"
        @submit.prevent="crear"
      >
        <h2 class="text-lg font-bold">Nuevo entrenador</h2>

        <div>
          <label class="label" for="nombre">Nombre</label>
          <input id="nombre" v-model="form.name" class="field" required />
        </div>
        <div>
          <label class="label" for="usuario">Usuario</label>
          <input
            id="usuario"
            v-model="form.username"
            class="field"
            autocapitalize="none"
            pattern="[a-zA-Z0-9._\-]+"
            required
          />
          <p class="mt-1 text-xs text-slate-500">Letras, números, punto, guion y guion bajo.</p>
        </div>
        <div>
          <label class="label" for="clave">Contraseña inicial</label>
          <input id="clave" v-model="form.password" type="text" class="field" minlength="8" required />
          <p class="mt-1 text-xs text-slate-500">
            Mínimo 8 caracteres. Podrá cambiarla desde «Mi cuenta».
          </p>
        </div>

        <div class="flex gap-2 pt-1">
          <button type="button" class="btn-ghost flex-1" @click="creando = false">Cancelar</button>
          <button type="submit" class="btn-primary flex-1" :disabled="ocupado">Crear</button>
        </div>
      </form>
    </div>

    <!-- Reseteo de contraseña -->
    <div
      v-if="reseteando"
      class="fixed inset-0 z-40 flex items-end bg-black/70 sm:items-center sm:p-4"
      @click.self="reseteando = null"
    >
      <form
        class="w-full space-y-4 rounded-t-2xl bg-slate-900 p-5 sm:mx-auto sm:max-w-md sm:rounded-2xl"
        @submit.prevent="resetear"
      >
        <h2 class="text-lg font-bold">Contraseña de {{ reseteando.name }}</h2>
        <div>
          <label class="label" for="reset">Nueva contraseña</label>
          <input id="reset" v-model="nuevaClave" type="text" class="field" minlength="8" required />
        </div>
        <div class="flex gap-2 pt-1">
          <button type="button" class="btn-ghost flex-1" @click="reseteando = null">Cancelar</button>
          <button type="submit" class="btn-primary flex-1" :disabled="ocupado">Guardar</button>
        </div>
      </form>
    </div>
  </AppShell>
</template>
