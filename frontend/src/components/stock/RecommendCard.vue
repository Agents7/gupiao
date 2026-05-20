<template>
  <div
    class="recommend-card rounded-xl border p-4 cursor-pointer transition-all hover:shadow-md hover:-translate-y-0.5 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700"
    @click="$emit('analyze', stock.symbol)"
  >
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <span class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 font-mono">{{ stock.symbol }}</span>
        <span v-if="stock.source === 'hot_up'" class="text-xs px-1.5 py-0.5 rounded bg-orange-100 text-orange-600">飙升</span>
        <span v-else class="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-600">热门</span>
      </div>
      <span class="text-xs text-gray-400">#{{ stock.rank }}</span>
    </div>
    <div class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{{ stock.name }}</div>
    <div class="flex items-baseline gap-2 mt-1">
      <span class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ stock.price?.toFixed(2) }}</span>
      <span :class="stock.change_pct >= 0 ? 'text-red-500' : 'text-green-500'" class="text-sm font-mono">
        {{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct?.toFixed(2) }}%
      </span>
    </div>
    <div class="mt-2 text-xs text-primary">点击分析 →</div>
  </div>
</template>

<script setup>
defineProps({
  stock: { type: Object, required: true },
});
defineEmits(["analyze"]);
</script>
