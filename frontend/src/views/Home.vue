<template>
  <div class="dashboard bg-gray-50 dark:bg-gray-950 min-h-screen">
    <!-- 顶部导航栏 -->
    <header class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 px-6 py-3">
      <div class="flex items-center justify-between max-w-7xl mx-auto">
        <div class="flex items-center gap-4">
          <h1 class="text-lg font-bold text-gray-800 dark:text-gray-100">
            <span class="text-primary">股小助手</span> · 智能看板
          </h1>
          <router-link to="/agent" class="text-xs text-primary hover:underline">AI 分析 →</router-link>
        </div>
        <IndexTicker v-if="data.indices?.length" :indices="data.indices" />
        <div class="flex items-center gap-3 ml-4">
          <span class="text-xs text-gray-400">
            {{ lastUpdated }}
          </span>
          <el-button size="small" :icon="RefreshIcon" circle @click="refresh" :loading="loading" />
          <span class="text-sm text-gray-600 dark:text-gray-400">{{ username }}</span>
          <el-button size="small" type="danger" text @click="handleLogout">退出</el-button>
        </div>
      </div>
    </header>

    <!-- 主体内容 -->
    <main class="max-w-7xl mx-auto p-4 space-y-4">
      <el-alert v-if="data.errors?.length" :title="`部分数据获取失败: ${data.errors.join(', ')}`" type="warning" show-icon closable class="mb-2" />

      <!-- 第一行：热门推荐 + 涨跌幅排行 -->
      <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <!-- 热门推荐 -->
        <div class="lg:col-span-2 space-y-3">
          <div class="flex items-center justify-between">
            <h2 class="text-base font-semibold text-gray-700 dark:text-gray-300">🔥 热门推荐</h2>
            <span class="text-xs text-gray-400">来源: 东方财富热榜</span>
          </div>
          <div v-if="data.hot_stocks?.length" class="grid grid-cols-2 gap-3">
            <RecommendCard
              v-for="stock in data.hot_stocks"
              :key="stock.symbol"
              :stock="stock"
              @analyze="goAnalyze"
            />
          </div>
          <el-skeleton v-else :rows="4" animated />
        </div>

        <!-- 涨幅榜 -->
        <div class="lg:col-span-1.5">
          <StockTable
            title="📈 涨幅榜 Top10"
            :stocks="data.top_gainers || []"
            @analyze="goAnalyze"
          />
        </div>

        <!-- 跌幅榜 -->
        <div class="lg:col-span-1.5">
          <StockTable
            title="📉 跌幅榜 Top10"
            :stocks="data.top_losers || []"
            @analyze="goAnalyze"
          />
        </div>
      </div>

      <!-- 第二行：板块 / 热门个股 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SectorTags
          title="🏭 热门行业板块"
          :sectors="data.hot_sectors || []"
          @analyze="goAnalyze"
        />
        <SectorTags
          title="💡 热门概念 / 强势个股"
          :sectors="data.hot_concepts || []"
          @analyze="goAnalyze"
        />
      </div>

      <!-- 第三行：市场情绪统计 -->
      <div v-if="data.market_breadth?.up !== undefined" class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <div class="stat-card">
          <div class="stat-value text-red-500">{{ data.market_breadth.up }}</div>
          <div class="stat-label">上涨家数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value text-green-500">{{ data.market_breadth.down }}</div>
          <div class="stat-label">下跌家数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value text-gray-500">{{ data.market_breadth.flat }}</div>
          <div class="stat-label">平盘</div>
        </div>
        <div class="stat-card">
          <div class="stat-value text-red-600">{{ data.market_breadth.real_limit_up }}</div>
          <div class="stat-label">涨停 (真实)</div>
        </div>
        <div class="stat-card">
          <div class="stat-value text-green-600">{{ data.market_breadth.real_limit_down }}</div>
          <div class="stat-label">跌停 (真实)</div>
        </div>
        <div class="stat-card">
          <div class="stat-value text-orange-500">{{ data.market_breadth.limit_up }}</div>
          <div class="stat-label">涨停 (含ST)</div>
        </div>
        <div class="stat-card">
          <div class="stat-value text-blue-500">{{ data.market_breadth.limit_down }}</div>
          <div class="stat-label">跌停 (含ST)</div>
        </div>
        <div class="stat-card">
          <div class="stat-value text-purple-500">{{ data.market_breadth.activity }}%</div>
          <div class="stat-label">市场活跃度</div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { getDashboardData } from "../api/agent";
import IndexTicker from "../components/stock/IndexTicker.vue";
import StockTable from "../components/stock/StockTable.vue";
import SectorTags from "../components/stock/SectorTags.vue";
import RecommendCard from "../components/stock/RecommendCard.vue";

const router = useRouter();
const username = localStorage.getItem("username") || "未知";
const loading = ref(false);
const data = reactive({
  indices: [],
  top_gainers: [],
  top_losers: [],
  hot_sectors: [],
  hot_concepts: [],
  hot_stocks: [],
  market_breadth: {},
  errors: [],
});

const lastUpdated = ref("--");

let refreshTimer = null;

onMounted(async () => {
  await refresh();
  refreshTimer = setInterval(refresh, 60000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});

async function refresh() {
  loading.value = true;
  try {
    const res = await getDashboardData();
    Object.assign(data, res.data);
    const now = new Date();
    lastUpdated.value = now.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch (err) {
    console.error("[Dashboard] 数据加载失败:", err);
  } finally {
    loading.value = false;
  }
}

function goAnalyze(keyword) {
  router.push({ path: "/agent", query: { q: `分析 ${keyword}` } });
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm("确定要退出登录吗？", "提示", { confirmButtonText: "确定", cancelButtonText: "取消", type: "warning" });
  } catch {
    return;
  }
  localStorage.removeItem("access_token");
  localStorage.removeItem("username");
  ElMessage.success("已退出登录");
  router.push("/login");
}
</script>

<style scoped>
.dashboard { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px 16px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.dark .stat-card { background: #1f2937; }

.stat-value { font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.2; }
.stat-label { font-size: 11px; color: #9ca3af; margin-top: 4px; }
</style>
