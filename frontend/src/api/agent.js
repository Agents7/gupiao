import axios from "axios";
import { ElMessage } from "element-plus";

const api = axios.create({
  baseURL: "/api",
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const msg = err.response?.data?.detail || "请求失败";
    ElMessage.error(msg);
    return Promise.reject(err);
  }
);

// Agent 对话（非流式，保留兼容）
export function sendMessage(conversationId, message) {
  return api.post("/agent/chat", { conversation_id: conversationId, message });
}

// Agent 对话（流式 — SSE）
export async function* sendMessageStream(conversationId, message) {
  const token = localStorage.getItem("access_token");
  if (!token) throw new Error("未登录");

  const response = await fetch("/api/agent/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          yield JSON.parse(line.slice(6));
        } catch {
          // 忽略解析失败的行
        }
      }
    }
  }
}

// 对话管理
export function getConversations() {
  return api.get("/agent/conversations");
}

export function createConversation() {
  return api.post("/agent/conversations");
}

export function getMessages(convId) {
  return api.get(`/agent/conversations/${convId}/messages`);
}

export function deleteConversation(id) {
  return api.delete(`/agent/conversations/${id}`);
}

// 用户画像
export function getUserProfile() {
  return api.get("/agent/profile");
}

export function updateUserProfile(fields) {
  return api.patch("/agent/profile", fields);
}

// 技能库
export function getUserSkills() {
  return api.get("/agent/skills");
}

// 股票数据
export function getStockQuote(symbol) {
  return api.get("/stock/quote", { params: { symbol } });
}

export function getAnalyses() {
  return api.get("/stock/analyses");
}

// 市场看板
export function getDashboardData() {
  return api.get("/market/dashboard");
}
