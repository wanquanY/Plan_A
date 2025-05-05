<script setup lang="ts">
import { ref } from 'vue';
import Sidebar from './Sidebar.vue';
import { useRouter } from 'vue-router';

const props = defineProps({
  username: {
    type: String,
    default: '用户'
  },
  editorTitle: {
    type: String,
    default: ''
  }
});

const router = useRouter();
const sidebarCollapsed = ref(false);
const sessions = ref([]);
const activeTab = ref('notes');
const currentSessionId = ref(null);

// 处理登出
const handleLogout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('access_token');
  router.push('/login');
};

// 处理切换侧边栏
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value;
};

// 处理导航
const handleNavigation = (path) => {
  router.push(path);
};

// 处理切换标签
const handleTabSwitch = (tab) => {
  activeTab.value = tab;
};

// 处理会话点击
const handleSessionClick = (sessionId) => {
  // 处理会话切换逻辑
};

// 处理新建笔记
const handleNewNote = () => {
  // 新建笔记逻辑
};
</script>

<template>
  <div class="layout-container">
    <div class="notebook-layout">
      <!-- 使用侧边栏组件 -->
      <Sidebar 
        :username="username"
        :editor-title="editorTitle"
        :sessions="sessions"
        :active-tab="activeTab"
        :current-session-id="currentSessionId"
        :collapsed="sidebarCollapsed"
        @logout="handleLogout"
        @switch-tab="handleTabSwitch"
        @session-click="handleSessionClick"
        @toggle-sidebar="toggleSidebar"
        @new-note="handleNewNote"
        @nav-to="handleNavigation"
      />
      
      <!-- 主内容区 -->
      <div class="main-content" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notebook-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  background-color: #f9f9f9;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', sans-serif;
}

/* 主内容区样式 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: auto;
  background-color: white;
  position: relative;
  transition: margin-left 0.3s ease;
  margin-left: 0;
}

.main-content.sidebar-collapsed {
  margin-left: 0;
}

@media (max-width: 768px) {
  .main-content {
    width: 100%;
  }
}
</style> 