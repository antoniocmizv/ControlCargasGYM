<script setup>
defineProps({
  icon: { type: String, default: '' },
  title: { type: String, required: true },
  message: { type: String, default: '' }
})
</script>

<template>
  <div class="card flex flex-col items-center gap-2 py-10 text-center">
    <span v-if="icon" class="text-4xl">{{ icon }}</span>
    <p class="text-lg font-semibold">{{ title }}</p>
    <p v-if="message" class="max-w-sm text-sm text-slate-400">{{ message }}</p>
    <slot />
  </div>
</template>
