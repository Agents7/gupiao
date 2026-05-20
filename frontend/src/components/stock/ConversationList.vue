<template>
  <div class="flex flex-col h-full">
    <button
      @click="$emit('new-conversation')"
      class="mx-2 mb-3 px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
    >
      <span>+</span> 新对话
    </button>

    <div class="flex-1 overflow-y-auto px-2 space-y-1">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        @click="$emit('select', conv.id)"
        :class="[
          'px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors truncate',
          activeId === conv.id
            ? 'bg-primary/10 text-primary font-medium'
            : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
        ]"
      >
        <div class="truncate">{{ conv.title || '新对话' }}</div>
        <div class="text-xs text-gray-400 mt-0.5">{{ formatTime(conv.updated_at || conv.created_at) }}</div>
      </div>
      <div v-if="conversations.length === 0" class="text-center text-gray-400 text-sm py-8">
        暂无对话
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  conversations: { type: Array, default: () => [] },
  activeId: { type: String, default: null },
});

defineEmits(["select", "new-conversation"]);

function formatTime(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}
</script>
