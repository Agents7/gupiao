<template>
  <div class="stock-table-wrapper">
    <h3 class="text-sm font-semibold text-gray-600 dark:text-gray-400 mb-2">{{ title }}</h3>
    <el-table :data="stocks" size="small" stripe :height="380" class="stock-table">
      <el-table-column prop="symbol" label="代码" width="72" />
      <el-table-column prop="name" label="名称" min-width="80">
        <template #default="{ row }">
          <span class="cursor-pointer hover:text-primary" @click="$emit('analyze', row.symbol)">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="最新价" width="80" align="right">
        <template #default="{ row }">{{ row.price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="涨跌幅" width="80" align="right">
        <template #default="{ row }">
          <span :class="row.change_pct >= 0 ? 'text-red-500' : 'text-green-500'">
            {{ row.change_pct >= 0 ? '+' : '' }}{{ row.change_pct?.toFixed(2) }}%
          </span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: "" },
  stocks: { type: Array, default: () => [] },
});
defineEmits(["analyze"]);
</script>

<style scoped>
.stock-table :deep(.el-table__body tr) { cursor: pointer; }
.stock-table :deep(.el-table__body tr:hover) { background: #f0f5ff; }
</style>
