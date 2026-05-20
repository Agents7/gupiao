<template>
  <div class="min-h-screen max-h-screen overflow-hidden grid lg:grid-cols-2">
    <!-- Left Content Section with Animated Characters -->
    <div class="relative hidden lg:flex flex-col justify-between bg-gradient-to-br from-gray-400 via-gray-500 to-gray-600 dark:from-white/90 dark:via-white/80 dark:to-white/70 p-12 text-white dark:text-gray-900">
      <div class="relative z-20">
        <router-link to="/" class="flex items-center gap-2 text-lg font-semibold">
          <div class="w-8 h-8 bg-white/10 backdrop-blur-sm rounded-lg flex items-center justify-center font-bold text-sm">
            G
          </div>
          <span>股小助手</span>
        </router-link>
      </div>

      <div class="relative z-20 flex items-end justify-center h-[500px]">
        <AnimatedCharacters
          :isTyping="isTyping"
          :showPassword="showPassword"
          :passwordLength="form.password.length"
        />
      </div>

      <div class="relative z-20 flex items-center gap-8 text-sm text-gray-600 dark:text-gray-700">
        <a href="#" class="hover:text-gray-900 dark:hover:text-black transition-colors">隐私政策</a>
        <a href="#" class="hover:text-gray-900 dark:hover:text-black transition-colors">服务条款</a>
      </div>

      <!-- Decorative elements -->
      <div class="absolute top-1/4 right-1/4 size-64 bg-gray-400/20 dark:bg-gray-300/30 rounded-full blur-3xl" />
      <div class="absolute bottom-1/4 left-1/4 size-96 bg-gray-300/20 dark:bg-gray-200/20 rounded-full blur-3xl" />
    </div>

    <!-- Right Signup Section -->
    <div class="flex items-center justify-center p-8 bg-background">
      <div class="w-full max-w-[420px]">
        <!-- Mobile Logo -->
        <div class="lg:hidden flex items-center justify-center gap-2 text-lg font-semibold mb-12">
          <div class="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center font-bold text-sm">
            G
          </div>
          <span>股小助手</span>
        </div>

        <!-- Header -->
        <div class="text-center mb-10">
          <h1 class="text-3xl font-bold tracking-tight mb-2">创建账号</h1>
          <p class="text-muted-foreground text-sm">请填写以下信息注册</p>
        </div>

        <!-- Signup Form -->
        <form @submit.prevent="handleSubmit" class="space-y-5">
          <div class="space-y-2">
            <label for="username" class="text-sm font-medium">用户名</label>
            <AppInput
              id="username"
              v-model="form.username"
              placeholder="3-32位字母/数字/下划线"
              :error="errors.username"
              @focus="isTyping = true"
              @blur="isTyping = false"
            />
            <p v-if="errors.username" class="text-sm text-destructive">{{ errors.username }}</p>
          </div>

          <div class="space-y-2">
            <label for="password" class="text-sm font-medium">密码</label>
            <div class="relative">
              <AppInput
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="至少6位字符"
                :error="errors.password"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <svg v-if="!showPassword" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/></svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49"/><path d="M14.084 14.158a3 3 0 0 1-4.242-4.242"/><path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143"/><path d="m2 2 20 20"/></svg>
              </button>
            </div>
            <p v-if="errors.password" class="text-sm text-destructive">{{ errors.password }}</p>
          </div>

          <div class="space-y-2">
            <label for="confirmPassword" class="text-sm font-medium">确认密码</label>
            <AppInput
              id="confirmPassword"
              v-model="form.confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              :error="errors.confirmPassword"
            />
            <p v-if="errors.confirmPassword" class="text-sm text-destructive">{{ errors.confirmPassword }}</p>
          </div>

          <div v-if="error" class="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/30 rounded-lg">
            {{ error }}
          </div>

          <InteractiveHoverButton
            type="submit"
            :text="loading ? '注册中...' : '注 册'"
            class="w-full h-12 text-base font-medium"
            :disabled="loading"
          />
        </form>

        <!-- Login Link -->
        <div class="text-center text-sm text-muted-foreground mt-8">
          已有账号？
          <router-link to="/login" class="text-foreground font-medium hover:underline">立即登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { useRouter, useRoute } from "vue-router";
import { register } from "../api/auth";
import { validateUsername, validatePassword, validateConfirmPassword } from "../utils/validate";
import AnimatedCharacters from "../components/ui/AnimatedCharacters.vue";
import InteractiveHoverButton from "../components/ui/InteractiveHoverButton.vue";
import AppInput from "../components/ui/AppInput.vue";

const router = useRouter();
const route = useRoute();

const isTyping = ref(false);
const showPassword = ref(false);
const loading = ref(false);
const error = ref("");

const form = reactive({
  username: "",
  password: "",
  confirmPassword: "",
});

const errors = reactive({
  username: "",
  password: "",
  confirmPassword: "",
});

function validate() {
  errors.username = validateUsername(form.username) || "";
  errors.password = validatePassword(form.password) || "";
  errors.confirmPassword = validateConfirmPassword(form.password, form.confirmPassword) || "";
  return !errors.username && !errors.password && !errors.confirmPassword;
}

async function handleSubmit() {
  if (!validate()) return;
  if (loading.value) return;

  loading.value = true;
  error.value = "";

  try {
    const res = await register(form.username, form.password, form.confirmPassword);
    const { access_token, username } = res.data;
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("username", username);
    router.push(route.query.redirect || "/");
  } catch (err) {
    if (err.response) {
      const detail = err.response.data?.detail;
      error.value = detail || "注册失败，请重试。";
    } else {
      error.value = "网络连接失败，请检查网络。";
    }
  } finally {
    loading.value = false;
  }
}
</script>
