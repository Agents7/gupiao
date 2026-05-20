<template>
  <div class="p-3 border-t border-gray-200 dark:border-gray-700">
    <div class="flex items-center justify-between mb-2">
      <span class="text-xs font-semibold text-gray-500 uppercase">用户画像</span>
      <button
        @click="editing = !editing"
        class="text-xs text-primary hover:underline"
      >
        {{ editing ? '完成' : '编辑' }}
      </button>
    </div>

    <div v-if="!editing" class="space-y-1 text-xs text-gray-600 dark:text-gray-400">
      <div>风险偏好: <span class="font-medium">{{ riskLabel }}</span></div>
      <div>投资风格: <span class="font-medium">{{ styleLabel }}</span></div>
      <div>偏好市场: <span class="font-medium">{{ profile.preferred_markets }}</span></div>
      <div>经验水平: <span class="font-medium">{{ levelLabel }}</span></div>
      <div v-if="focusStocks.length">自选股: <span class="font-medium">{{ focusStocks.join(', ') }}</span></div>
    </div>

    <div v-else class="space-y-2">
      <select v-model="form.risk_tolerance" class="w-full text-xs border rounded px-2 py-1">
        <option value="conservative">保守</option>
        <option value="moderate">稳健</option>
        <option value="aggressive">激进</option>
      </select>
      <select v-model="form.investment_style" class="w-full text-xs border rounded px-2 py-1">
        <option value="day_trade">短线交易</option>
        <option value="swing">波段操作</option>
        <option value="long_term">长期持有</option>
        <option value="value">价值投资</option>
      </select>
      <select v-model="form.preferred_markets" class="w-full text-xs border rounded px-2 py-1">
        <option value="A股">A股</option>
        <option value="港股">港股</option>
        <option value="美股">美股</option>
        <option value="A股,港股">A股+港股</option>
      </select>
      <select v-model="form.experience_level" class="w-full text-xs border rounded px-2 py-1">
        <option value="beginner">入门</option>
        <option value="intermediate">中级</option>
        <option value="advanced">高级</option>
      </select>
      <button
        @click="saveProfile"
        :disabled="saving"
        class="w-full py-1 bg-primary text-white rounded text-xs hover:opacity-90"
      >
        {{ saving ? '保存中...' : '保存' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { getUserProfile, updateUserProfile } from "../../api/agent";

const props = defineProps({ profile: { type: Object, default: () => ({}) } });
const emit = defineEmits(["updated"]);

const editing = ref(false);
const saving = ref(false);
const form = ref({});

const focusStocks = computed(() => {
  try {
    const raw = props.profile.focus_stocks;
    if (!raw) return [];
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch { return []; }
});

const riskLabel = computed(() => ({ conservative: "保守", moderate: "稳健", aggressive: "激进" }[props.profile.risk_tolerance] || "-"));
const styleLabel = computed(() => ({ day_trade: "短线", swing: "波段", long_term: "长线", value: "价值" }[props.profile.investment_style] || "-"));
const levelLabel = computed(() => ({ beginner: "入门", intermediate: "中级", advanced: "高级" }[props.profile.experience_level] || "-"));

watch(() => props.profile, (p) => {
  form.value = {
    risk_tolerance: p.risk_tolerance || "moderate",
    investment_style: p.investment_style || "swing",
    preferred_markets: p.preferred_markets || "A股",
    experience_level: p.experience_level || "beginner",
  };
}, { immediate: true });

async function saveProfile() {
  saving.value = true;
  try {
    await updateUserProfile(form.value);
    editing.value = false;
    emit("updated");
  } finally {
    saving.value = false;
  }
}
</script>
