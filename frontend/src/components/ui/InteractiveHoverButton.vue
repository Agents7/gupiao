<template>
  <button
    :type="type"
    :disabled="disabled"
    class="group relative cursor-pointer overflow-hidden rounded-full border bg-background px-6 py-2 text-center font-semibold transition-all disabled:pointer-events-none disabled:opacity-50"
    :class="computedClass"
  >
    <span
      class="inline-block transition-all duration-300 group-hover:translate-x-12 group-hover:opacity-0"
    >
      {{ text }}
    </span>
    <div
      class="absolute inset-0 z-10 flex items-center justify-center gap-2 bg-primary text-primary-foreground opacity-0 transition-all duration-300 group-hover:opacity-100 rounded-full"
    >
      <span>{{ text }}</span>
      <slot name="icon">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M5 12h14" />
          <path d="m12 5 7 7-7 7" />
        </svg>
      </slot>
    </div>
  </button>
</template>

<script setup>
defineProps({
  text: { type: String, default: "Button" },
  type: { type: String, default: "submit" },
  disabled: { type: Boolean, default: false },
  computedClass: { type: String, default: "" },
});
</script>
