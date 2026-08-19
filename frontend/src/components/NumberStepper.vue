<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [Number, null], default: null },
  step: { type: Number, default: 2.5 },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 999 },
  suffix: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  compact: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'commit'])

const current = computed(() => props.modelValue ?? 0)

function clamp(value) {
  return Math.min(props.max, Math.max(props.min, Math.round(value * 100) / 100))
}

function bump(delta) {
  const next = clamp(current.value + delta)
  emit('update:modelValue', next)
  emit('commit', next)
  // Vibración corta: confirma la pulsación sin mirar la pantalla.
  navigator.vibrate?.(8)
}

function onInput(event) {
  const raw = event.target.value
  if (raw === '') {
    emit('update:modelValue', null)
    return
  }
  emit('update:modelValue', clamp(Number(raw)))
}

function onBlur() {
  if (props.modelValue !== null) emit('commit', props.modelValue)
}
</script>

<template>
  <div class="flex items-stretch gap-2">
    <button
      type="button"
      class="btn-ghost shrink-0 font-bold"
      :class="compact ? 'w-11 text-xl' : 'w-16 text-2xl'"
      :aria-label="`Restar ${step}`"
      @click="bump(-step)"
    >
      −
    </button>

    <div class="relative min-w-0 flex-1">
      <input
        :value="modelValue"
        type="number"
        inputmode="decimal"
        :step="step"
        :min="min"
        :max="max"
        :placeholder="placeholder"
        class="field h-full text-center font-bold tabular-nums"
        :class="[compact ? 'px-1 text-lg' : 'text-2xl', suffix && 'pr-9']"
        @input="onInput"
        @blur="onBlur"
      />
      <span
        v-if="suffix"
        class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm font-medium text-slate-500"
      >
        {{ suffix }}
      </span>
    </div>

    <button
      type="button"
      class="btn-ghost shrink-0 font-bold"
      :class="compact ? 'w-11 text-xl' : 'w-16 text-2xl'"
      :aria-label="`Sumar ${step}`"
      @click="bump(step)"
    >
      +
    </button>
  </div>
</template>
