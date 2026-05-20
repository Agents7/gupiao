<template>
  <div class="agent-container h-screen flex bg-gray-50 dark:bg-gray-900">
    <!-- 侧边栏 -->
    <aside class="w-64 flex-shrink-0 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
      <div class="p-4 border-b border-gray-200 dark:border-gray-700">
        <router-link to="/" class="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700">
          <span>← 返回首页</span>
        </router-link>
      </div>
      <ConversationList
        :conversations="conversations"
        :activeId="activeConvId"
        @select="selectConversation"
        @new-conversation="startNewConversation"
      />
      <ProfilePanel
        :profile="profile"
        @updated="loadProfile"
      />
    </aside>

    <!-- 对话区 -->
    <main class="flex-1 flex flex-col min-w-0">
      <!-- 顶部 -->
      <header class="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <h1 class="text-lg font-semibold">股小助手</h1>
        <p class="text-xs text-gray-400">AI 股票分析师 · 对话式交互</p>
      </header>

      <!-- 消息列表 -->
      <div class="flex-1 overflow-y-auto px-6 py-4 space-y-4" ref="msgContainer">
        <div v-if="messages.length === 0 && !loading" class="text-center text-gray-400 mt-32">
          <div class="text-4xl mb-4">📊</div>
          <div class="text-lg font-medium mb-2">欢迎使用股小助手</div>
          <div class="text-sm">输入股票代码或名称，获取 AI 驱动的专业分析</div>
          <div class="mt-6 grid grid-cols-2 gap-2 max-w-sm mx-auto">
            <button
              v-for="q in quickQuestions"
              :key="q"
              @click="sendQuick(q)"
              class="text-xs px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50 text-left transition-colors"
            >
              {{ q }}
            </button>
          </div>
        </div>

        <div
          v-for="(msg, i) in messages"
          :key="i"
          :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']"
        >
          <!-- 用户消息 -->
          <div
            v-if="msg.role === 'user'"
            class="max-w-[70%] px-4 py-2 bg-primary text-primary-foreground rounded-2xl rounded-br-md"
          >
            {{ msg.content }}
          </div>

          <!-- 系统/tool 消息不展示 -->

          <!-- Assistant 消息 -->
          <div
            v-else-if="msg.role === 'assistant'"
            class="max-w-[85%]"
          >
            <!-- 尝试解析 JSON -->
            <template v-if="parseAssistantMsg(msg)">
              <div
                class="px-4 py-3 bg-white dark:bg-gray-800 rounded-2xl rounded-bl-md shadow-sm border border-gray-200 dark:border-gray-700 markdown-body text-sm"
                v-html="parseAssistantMsg(msg).replyHtml"
              />
              <AnalysisCard
                v-if="parseAssistantMsg(msg).hasAnalysis"
                :quote-data="parseAssistantMsg(msg).quoteData"
                :sentiment="parseAssistantMsg(msg).sentiment"
                :risk-level="parseAssistantMsg(msg).riskLevel"
                :risk-factors="parseAssistantMsg(msg).riskFactors"
                :kline-patterns="parseAssistantMsg(msg).klinePatterns"
                :key-data-points="parseAssistantMsg(msg).keyDataPoints"
              />
            </template>
            <div
              v-else
              class="px-4 py-3 bg-white dark:bg-gray-800 rounded-2xl rounded-bl-md shadow-sm border border-gray-200 dark:border-gray-700 text-sm"
            >
              {{ msg.content }}
            </div>
          </div>
        </div>

        <!-- 加载/流式动画 -->
        <div v-if="loading" class="flex justify-start">
          <div class="px-4 py-3 bg-white dark:bg-gray-800 rounded-2xl rounded-bl-md shadow-sm border max-w-[85%]">
            <template v-if="streamingText">
              <div class="markdown-body text-sm whitespace-pre-wrap">{{ streamingText }}<span class="streaming-cursor">|</span></div>
            </template>
            <template v-else>
              <div class="flex gap-1.5">
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0s" />
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.15s" />
                <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.3s" />
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="px-6 py-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <div class="flex gap-3 max-w-3xl mx-auto">
          <input
            v-model="inputMsg"
            @keydown.enter="sendMessage"
            :disabled="loading"
            placeholder="输入股票代码或问题，如「分析 600519」"
            class="flex-1 px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-xl bg-gray-50 dark:bg-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50"
          />
          <button
            @click="sendMessage"
            :disabled="loading || !inputMsg.trim()"
            class="px-5 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            发送
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  sendMessage as apiSend,
  sendMessageStream,
  getConversations,
  getMessages,
  createConversation,
  getUserProfile,
} from "../api/agent";
import ConversationList from "../components/stock/ConversationList.vue";
import ProfilePanel from "../components/stock/ProfilePanel.vue";
import AnalysisCard from "../components/stock/AnalysisCard.vue";

const route = useRoute();
const router = useRouter();

const activeConvId = ref(route.params.id || null);
const conversations = ref([]);
const messages = ref([]);
const profile = ref({});
const inputMsg = ref("");
const loading = ref(false);
const streamingText = ref("");
const msgContainer = ref(null);

const quickQuestions = [
  "分析 600519 贵州茅台",
  "000001 平安银行怎么样",
  "最近有什么热门板块",
  "帮我看看 AAPL",
];

onMounted(async () => {
  await loadProfile();
  await loadConversations();
  if (activeConvId.value) {
    await loadMessages(activeConvId.value);
  }
  // 从看板跳转过来时自动填入查询
  const q = route.query.q;
  if (q && typeof q === "string") {
    inputMsg.value = q;
    await sendMessage();
  }
});

async function loadProfile() {
  try {
    const res = await getUserProfile();
    profile.value = res.data;
  } catch { /* ignore */ }
}

async function loadConversations() {
  try {
    const res = await getConversations();
    conversations.value = res.data;
  } catch { /* ignore */ }
}

async function loadMessages(convId) {
  try {
    const res = await getMessages(convId);
    messages.value = res.data.filter(m => {
      if (m.role === "tool") return false;
      // 过滤掉 tool_calls 原始数组消息（非用户可读内容）
      if (m.role === "assistant" && /^\s*\[\s*\{/.test(m.content) && m.content.includes('"function"')) return false;
      return true;
    });
  } catch { /* ignore */ }
}

function selectConversation(id) {
  activeConvId.value = id;
  router.replace(`/agent/${id}`);
  loadMessages(id);
}

async function startNewConversation() {
  try {
    const res = await createConversation();
    const conv = res.data;
    conversations.value.unshift(conv);
    activeConvId.value = conv.id;
    messages.value = [];
    router.replace(`/agent/${conv.id}`);
  } catch { /* ignore */ }
}

async function sendQuick(q) {
  inputMsg.value = q;
  await sendMessage();
}

async function sendMessage() {
  const text = inputMsg.value.trim();
  if (!text || loading.value) return;
  inputMsg.value = "";

  messages.value.push({ role: "user", content: text });
  scrollToBottom();

  loading.value = true;
  streamingText.value = "";

  try {
    const stream = sendMessageStream(activeConvId.value, text);
    for await (const event of stream) {
      switch (event.type) {
        case "status":
          // 状态提示显示在流式文本中
          break;
        case "delta":
          streamingText.value += event.content;
          scrollToBottom();
          break;
        case "done": {
          const data = event.result;
          if (!activeConvId.value && data.conversation_id) {
            activeConvId.value = data.conversation_id;
            router.replace(`/agent/${data.conversation_id}`);
            loadConversations();
          }
          // 构造结构化消息
          const assistantMsg = JSON.stringify({
            reply: data.reply,
            sentiment: data.sentiment,
            risk_level: data.risk_level,
            risk_factors: data.risk_factors,
            kline_patterns: data.kline_patterns,
            key_data_points: data.key_data_points,
            quote_data: data.quote_data,
          });
          messages.value.push({ role: "assistant", content: assistantMsg });
          streamingText.value = "";
          scrollToBottom();
          break;
        }
        case "error":
          messages.value.push({ role: "assistant", content: JSON.stringify({ reply: `❌ ${event.content}` }) });
          streamingText.value = "";
          break;
      }
    }
  } catch (err) {
    messages.value.push({ role: "assistant", content: JSON.stringify({ reply: `❌ 请求失败: ${err.message}` }) });
    streamingText.value = "";
  } finally {
    loading.value = false;
  }
}

function parseAssistantMsg(msg) {
  try {
    const parsed = JSON.parse(msg.content);
    if (parsed.reply !== undefined) {
      return {
        replyHtml: parsed.reply.replace(/\n/g, "<br>"),
        hasAnalysis: !!(parsed.sentiment || parsed.quote_data),
        sentiment: parsed.sentiment,
        riskLevel: parsed.risk_level,
        riskFactors: parsed.risk_factors,
        klinePatterns: parsed.kline_patterns,
        keyDataPoints: parsed.key_data_points,
        quoteData: parsed.quote_data,
      };
    }
  } catch { /* not JSON */ }
  return null;
}

function scrollToBottom() {
  nextTick(() => {
    const el = msgContainer.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
}
</script>

<style scoped>
.agent-container {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.markdown-body br + br {
  display: block;
  content: "";
  margin-top: 0.5em;
}

.streaming-cursor {
  display: inline-block;
  color: #409eff;
  font-weight: 700;
  animation: blink 0.7s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
