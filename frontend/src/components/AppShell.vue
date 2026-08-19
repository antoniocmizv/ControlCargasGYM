<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  back: { type: [String, Object], default: null }
})
</script>

<template>
  <div class="min-h-screen bg-slate-950">
    <header
      class="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur"
      style="padding-top: env(safe-area-inset-top)"
    >
      <div class="mx-auto flex max-w-2xl items-center gap-3 px-4 py-3">
        <RouterLink
          v-if="back"
          :to="back"
          class="btn-ghost -ml-2 h-11 w-11 !px-0 text-xl"
          aria-label="Volver"
        >
          ‹
        </RouterLink>
        <div class="min-w-0 flex-1">
          <h1 class="truncate text-lg font-bold leading-tight">{{ title }}</h1>
          <p v-if="subtitle" class="truncate text-sm text-slate-400">{{ subtitle }}</p>
        </div>
        <slot name="actions" />
      </div>
    </header>

    <main class="mx-auto max-w-2xl px-4 pb-24 pt-4">
      <slot />
    </main>
  </div>
</template>
