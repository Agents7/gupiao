<template>
  <input
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :id="id"
    :disabled="disabled"
    class="flex h-12 w-full rounded-full border border-border/60 bg-background px-4 py-2 text-base ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
    :class="error ? 'border-destructive focus-visible:ring-destructive' : 'focus:border-primary'"
    @input="$emit('update:modelValue', $event.target.value)"
    @focus="$emit('focus', $event)"
    @blur="$emit('blur', $event)"
  />
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: "" },
  type: { type: String, default: "text" },
  placeholder: { type: String, default: "" },
  id: { type: String, default: "" },
  disabled: { type: Boolean, default: false },
  error: { type: String, default: "" },
});

defineEmits(["update:modelValue", "focus", "blur"]);
</script>
