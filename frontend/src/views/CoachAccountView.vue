<script setup>
import { ref } from 'vue'

import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const actual = ref('')
const nueva = ref('')
const repetida = ref('')
const guardando = ref(false)
const error = ref('')
const hecho = ref(false)

async function cambiar() {
  error.value = ''
  hecho.value = false

  if (nueva.value.length < 8) return (error.value = 'La nueva contraseña necesita 8 caracteres')
  if (nueva.value !== repetida.value) return (error.value = 'Las dos contraseñas no coinciden')

  guardando.value = true
  try {
    await api.post('/coach/password', {
      current_password: actual.value,
      new_password: nueva.value
    })
    actual.value = nueva.value = repetida.value = ''
    hecho.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <AppShell title="Mi cuenta" :subtitle="auth.user?.name" back="/panel">
    <section class="card mb-4">
      <h2 class="mb-1 font-bold">{{ auth.user?.name }}</h2>
      <p class="text-sm text-slate-400">
        {{ auth.isAdmin ? 'Entrenador principal' : 'Entrenador' }}
      </p>
    </section>

    <form class="card space-y-4" @submit.prevent="cambiar">
      <h2 class="font-bold">Cambiar mi contraseña</h2>

      <div>
        <label class="label" for="actual">Contraseña actual</label>
        <input
          id="actual"
          v-model="actual"
          type="password"
          class="field"
          autocomplete="current-password"
          required
        />
      </div>

      <div>
        <label class="label" for="nueva">Nueva contraseña</label>
        <input
          id="nueva"
          v-model="nueva"
          type="password"
          class="field"
          autocomplete="new-password"
          minlength="8"
          required
        />
        <p class="mt-1 text-xs text-slate-500">Mínimo 8 caracteres.</p>
      </div>

      <div>
        <label class="label" for="repetida">Repite la nueva</label>
        <input
          id="repetida"
          v-model="repetida"
          type="password"
          class="field"
          autocomplete="new-password"
          required
        />
      </div>

      <button type="submit" class="btn-primary w-full" :disabled="guardando">
        {{ guardando ? 'Guardando…' : 'Cambiar contraseña' }}
      </button>

      <p v-if="hecho" class="rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
        Contraseña cambiada. La próxima vez entra con la nueva.
      </p>
      <p v-if="error" class="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{{ error }}</p>
    </form>
  </AppShell>
</template>
