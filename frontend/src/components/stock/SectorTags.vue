<template>
  <div class="sector-tags">
    <h3 class="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-2">{{ title }}</h3>
    <div class="flex flex-wrap gap-2">
      <el-tooltip
        v-for="s in sectors"
        :key="s.code"
        :content="`领涨: ${s.leader} ${s.leader_change >= 0 ? '+' : ''}${s.leader_change?.toFixed(2)}% | 涨${s.up_count}家 跌${s.down_count}家`"
        placement="top"
        :show-after="300"
      >
        <span
          class="cursor-pointer px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
          :class="sectorClass(s.change_pct)"
          @click="$emit('analyze', s.name)"
        >
          {{ s.name }}
          <span class="ml-1 font-mono">{{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct?.toFixed(2) }}%</span>
        </span>
      </el-tooltip>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: "" },
  sectors: { type: Array, default: () => [] },
});
defineEmits(["analyze"]);

function sectorClass(pct) {
  if (pct > 3) return "bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-400";
  if (pct > 1) return "bg-red-50 dark:bg-red-950/20 text-red-600 dark:text-red-400";
  if (pct > -1) return "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400";
  if (pct > -3) return "bg-green-50 dark:bg-green-950/20 text-green-600 dark:text-green-400";
  return "bg-green-100 dark:bg-green-950/50 text-green-700 dark:text-green-400";
}
</script>
