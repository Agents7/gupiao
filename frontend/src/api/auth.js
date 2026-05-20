import axios from "axios";
import { ElMessage } from "element-plus";

const api = axios.create({
  baseURL: "/api",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// ── 请求拦截器：自动附加 token ─────────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error("[API] 请求拦截器错误:", error);
    return Promise.reject(error);
  }
);

// ── 响应拦截器：统一错误处理 ────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      console.warn(`[API] 响应错误 ${status}:`, data);

      switch (status) {
        case 401:
          ElMessage.error(data.detail || "登录已过期，请重新登录");
          localStorage.removeItem("access_token");
          localStorage.removeItem("username");
          window.location.href = "/login";
          break;
        case 422:
          ElMessage.error(data.detail || "输入数据校验不通过");
          break;
        case 500:
          ElMessage.error("服务器内部错误，请稍后重试");
          break;
        default:
          ElMessage.error(data.detail || `请求失败 (${status})`);
      }
    } else if (error.code === "ECONNABORTED") {
      ElMessage.error("请求超时，请检查网络");
    } else {
      console.error("[API] 网络错误:", error.message);
      ElMessage.error("网络连接失败");
    }
    return Promise.reject(error);
  }
);

// ── API 方法 ────────────────────────────────────────────────────────────────

export function login(username, password) {
  return api.post("/auth/login", { username, password });
}

export function register(username, password, confirmPassword) {
  return api.post("/auth/register", {
    username,
    password,
    confirm_password: confirmPassword,
  });
}

export function getProfile() {
  return api.get("/auth/me");
}

export default api;
