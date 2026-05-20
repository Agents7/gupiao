<template>
  <div class="analysis-card bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 my-3">
    <!-- 行情数据 -->
    <div class="flex items-center justify-between mb-3" v-if="quoteData">
      <div>
        <span class="font-semibold text-lg">{{ quoteData.name }}</span>
        <span class="text-xs text-gray-400 ml-2">{{ quoteData.symbol }}</span>
      </div>
      <div class="text-right">
        <span class="text-xl font-bold">{{ quoteData.price }}</span>
        <span
          :class="changePct >= 0 ? 'text-green-500' : 'text-red-500'"
          class="ml-2 text-sm font-medium"
        >
          {{ changePct >= 0 ? '↑' : '↓' }}{{ Math.abs(changePct).toFixed(2) }}%
        </span>
      </div>
    </div>

    <!-- 行情详情 -->
    <div class="grid grid-cols-4 gap-2 mb-3 text-xs text-gray-500" v-if="quoteData">
      <div>开盘 {{ quoteData.open }}</div>
      <div>最高 {{ quoteData.high }}</div>
      <div>最低 {{ quoteData.low }}</div>
      <div>成交量 {{ formatVolume(quoteData.volume) }}</div>
    </div>

    <!-- 情绪 & 风险标签 -->
    <div class="flex gap-2 mb-3" v-if="sentiment || riskLevel">
      <span
        v-if="sentiment"
        :class="sentimentClass"
        class="px-2.5 py-0.5 rounded-full text-xs font-semibold"
      >
        {{ sentimentLabel }}
      </span>
      <span
        v-if="riskLevel"
        :class="riskClass"
        class="px-2.5 py-0.5 rounded-full text-xs font-semibold"
      >
        风险: {{ riskLabel }}
      </span>
    </div>

    <!-- K线形态 -->
    <div class="mb-3" v-if="klinePatterns">
      <span class="text-xs text-gray-400">K线形态：</span>
      <span class="text-sm font-medium text-purple-600 dark:text-purple-400">{{ klinePatterns }}</span>
    </div>

    <!-- 支撑/压力 -->
    <div class="grid grid-cols-2 gap-2 mb-3 text-xs" v-if="keyDataPoints?.support_level || keyDataPoints?.resistance_level">
      <div class="bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded px-2 py-1" v-if="keyDataPoints.support_level">
        支撑: {{ keyDataPoints.support_level }}
      </div>
      <div class="bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded px-2 py-1" v-if="keyDataPoints.resistance_level">
        压力: {{ keyDataPoints.resistance_level }}
      </div>
    </div>

    <!-- 风险因素 -->
    <div class="mb-3" v-if="riskFactors && riskFactors.length">
      <div class="text-xs text-gray-400 mb-1">风险因素：</div>
      <div v-for="(f, i) in riskFactors" :key="i" class="text-xs text-orange-600 dark:text-orange-400 flex gap-1">
        <span>⚠</span><span>{{ f }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  quoteData: { type: Object, default: null },
  sentiment: { type: String, default: null },
  riskLevel: { type: String, default: null },
  riskFactors: { type: Array, default: () => [] },
  klinePatterns: { type: String, default: "" },
  keyDataPoints: { type: Object, default: () => ({}) },
});

const changePct = computed(() => props.quoteData?.change_pct ?? 0);

const sentimentClass = computed(() => ({
  bullish: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  bearish: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  neutral: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300",
}[props.sentiment] || ""));

const sentimentLabel = computed(() => ({
  bullish: "🟢 偏多",
  bearish: "🔴 偏空",
  neutral: "⚪ 中性",
}[props.sentiment] || props.sentiment));

const riskClass = computed(() => ({
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-red-100 text-red-700",
}[props.riskLevel] || ""));

const riskLabel = computed(() => ({
  low: "低",
  medium: "中",
  high: "高",
}[props.riskLevel] || props.riskLevel));

function formatVolume(v) {
  if (!v) return "-";
  if (v >= 1e8) return (v / 1e8).toFixed(2) + "亿";
  if (v >= 1e4) return (v / 1e4).toFixed(1) + "万";
  return v.toString();
}
</script>
