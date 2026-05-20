<template>
  <div class="index-ticker flex items-center gap-4 overflow-x-auto px-2">
    <div
      v-for="idx in indices"
      :key="idx.code"
      class="flex items-center gap-2 px-3 py-1 rounded-lg whitespace-nowrap text-sm"
      :class="idx.change_pct >= 0 ? 'bg-red-50 dark:bg-red-950/30' : 'bg-green-50 dark:bg-green-950/30'"
    >
      <span class="font-medium text-gray-700 dark:text-gray-300">{{ idx.name }}</span>
      <span class="font-mono font-semibold" :class="idx.change_pct >= 0 ? 'text-red-500' : 'text-green-500'">
        {{ idx.price.toFixed(2) }}
      </span>
      <span class="font-mono text-xs px-1.5 py-0.5 rounded" :class="idx.change_pct >= 0 ? 'bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-400' : 'bg-green-100 dark:bg-green-900/50 text-green-600 dark:text-green-400'">
        {{ idx.change_pct >= 0 ? '+' : '' }}{{ idx.change_pct.toFixed(2) }}%
      </span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  indices: { type: Array, default: () => [] },
});
</script>
