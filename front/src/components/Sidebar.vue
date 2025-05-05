<script setup lang="ts">
import { ref, computed } from 'vue';
import { 
  LogoutOutlined, 
  FileOutlined,
  PlusOutlined,
  LeftOutlined,
  RightOutlined,
  UserOutlined,
  RobotOutlined
} from '@ant-design/icons-vue';
import UserDropdownMenu from './UserDropdownMenu.vue';

const props = defineProps({
  username: {
    type: String,
    default: '用户'
  },
  editorTitle: {
    type: String,
    default: ''
  },
  sessions: {
    type: Array,
    default: () => []
  },
  activeTab: {
    type: String,
    default: 'notes'
  },
  currentSessionId: {
    type: [Number, String, null],
    default: null
  },
  collapsed: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['logout', 'switch-tab', 'session-click', 'toggle-sidebar', 'new-note', 'nav-to']);

// 用户菜单显示状态
const userMenuVisible = ref(false);
const menuPosition = ref({ x: 0, y: 0 });

// 切换用户菜单显示状态
const toggleUserMenu = (event) => {
  event.stopPropagation();
  
  const userInfoElement = event.currentTarget;
  const rect = userInfoElement.getBoundingClientRect();
  
  // 更新菜单位置 - 调整为用户信息区域上方显示，避免被底部遮挡
  menuPosition.value = {
    x: rect.left,
    y: rect.top - 150 // 将菜单置于用户信息上方
  };
  
  userMenuVisible.value = !userMenuVisible.value;
};

// 关闭用户菜单
const closeUserMenu = () => {
  userMenuVisible.value = false;
};

// 导航到指定页面
const navigateTo = (path) => {
  emit('nav-to', path);
  closeUserMenu();
};

// 处理注销
const handleLogout = () => {
  emit('logout');
};

// 截取会话消息
const truncateMessage = (message, length = 30) => {
  if (!message) return '';
  if (message.length <= length) return message;
  return message.substring(0, length) + '...';
};

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000); // 差距的秒数
  
  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}天前`;
  
  // 超过一周返回具体日期
  return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')}`;
};
</script>

<template>
  <!-- 侧边栏 -->
  <div class="sidebar" :class="{ 'sidebar-collapsed': collapsed }">
    <div class="sidebar-top">
      <div class="logo">
        <span class="logo-text">FreeWrite</span>
      </div>
    </div>
    
    <div class="sidebar-middle">
      <button class="new-note-button" @click="emit('new-note')">
        <PlusOutlined />
        <span>{{ activeTab === 'notes' ? '新建笔记' : '新建会话' }}</span>
      </button>
      
      <div class="note-tabs">
        <div 
          class="note-tab" 
          :class="{ active: activeTab === 'notes' }"
          @click="emit('switch-tab', 'notes')"
        >
          <span>我的笔记</span>
        </div>
        <div 
          class="note-tab" 
          :class="{ active: activeTab === 'sessions' }"
          @click="emit('switch-tab', 'sessions')"
        >
          <span>会话记录</span>
        </div>
      </div>
      
      <!-- 笔记列表 -->
      <div class="note-list" v-if="activeTab === 'notes'">
        <div class="note-item active">
          <div class="note-title">{{ editorTitle }}</div>
          <div class="note-meta">刚刚编辑</div>
        </div>
        <div class="note-item">
          <div class="note-title">未来科技趋势</div>
          <div class="note-meta">1小时前编辑</div>
        </div>
        <div class="note-item">
          <div class="note-title">旅行清单</div>
          <div class="note-meta">昨天编辑</div>
        </div>
        <div class="note-item">
          <div class="note-title">书籍推荐</div>
          <div class="note-meta">2天前编辑</div>
        </div>
      </div>
      
      <!-- 会话列表 -->
      <div class="note-list" v-if="activeTab === 'sessions'">
        <div 
          v-for="session in sessions" 
          :key="session.id" 
          class="note-item" 
          :class="{ active: currentSessionId === session.id }"
          @click="emit('session-click', session.id)"
        >
          <div class="note-title">{{ session.title }}</div>
          <div class="note-meta">
            <span class="message-preview">{{ truncateMessage(session.last_message) }}</span>
            <span class="time">{{ formatDate(session.updated_at) }}</span>
          </div>
        </div>
        <div v-if="sessions.length === 0" class="empty-state">
          暂无聊天会话记录
        </div>
      </div>
    </div>
    
    <div class="sidebar-bottom">
      <div class="user-info" @click="toggleUserMenu">
        <div class="avatar">{{ username.charAt(0).toUpperCase() }}</div>
        <div class="username">{{ username }}</div>
      </div>
      
      <button class="settings-button" @click="emit('logout')">
        <LogoutOutlined />
      </button>
    </div>
    
    <!-- 中央收起侧边栏按钮 -->
    <div class="sidebar-collapse-button" @click="emit('toggle-sidebar')">
      <LeftOutlined />
    </div>
  </div>
  
  <!-- 展开侧边栏按钮 -->
  <div class="sidebar-expand-button" v-if="collapsed" @click="emit('toggle-sidebar')">
    <RightOutlined />
  </div>
  
  <!-- 用户下拉菜单 -->
  <UserDropdownMenu 
    :visible="userMenuVisible" 
    :position="menuPosition" 
    @close="closeUserMenu"
    @navigate="navigateTo"
    @logout="handleLogout"
  />
</template>

<style scoped>
/* 侧边栏样式 */
.sidebar {
  width: 260px;
  background-color: #f0f0f0;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: inset -1px 0 0 rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  position: relative;
  z-index: 10;
}

.sidebar-collapsed {
  width: 0;
  min-width: 0;
  overflow: hidden;
}

.sidebar-top {
  padding: 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #333;
  letter-spacing: -0.5px;
}

.sidebar-middle {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: auto;
  scrollbar-width: thin; /* Firefox */
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent; /* Firefox */
}

.sidebar-middle::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.sidebar-middle::-webkit-scrollbar-track {
  background: transparent;
  border-radius: 3px;
}

.sidebar-middle::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
  border: none;
}

.sidebar-middle::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.3);
}

.sidebar-middle::-webkit-scrollbar-corner {
  background-color: transparent;
}

.new-note-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.new-note-button:hover {
  background-color: #0069d9;
}

.note-tabs {
  display: flex;
  margin-bottom: 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.07);
}

.note-tab {
  padding: 8px 12px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  position: relative;
  transition: color 0.2s;
}

.note-tab:hover {
  color: #333;
}

.note-tab.active {
  color: #007bff;
  font-weight: 500;
}

.note-tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 2px;
  background-color: #007bff;
}

.note-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.note-item {
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.note-item:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.note-item.active {
  background-color: rgba(0, 123, 255, 0.1);
}

.note-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #333;
}

.note-meta {
  font-size: 12px;
  color: #888;
  display: flex;
  justify-content: space-between;
}

.message-preview {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
}

.time {
  font-size: 11px;
  color: #999;
}

.empty-state {
  text-align: center;
  padding: 20px 0;
  color: #888;
  font-size: 14px;
}

.sidebar-bottom {
  padding: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.07);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 5px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #007bff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
}

.username {
  font-size: 14px;
  color: #333;
}

.settings-button {
  background: none;
  border: none;
  color: #666;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.settings-button:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #333;
}

/* 中央收起侧边栏按钮 */
.sidebar-collapse-button {
  position: absolute;
  top: 50%;
  right: -14px;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  background-color: #fff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #999;
  font-size: 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 20;
  transition: all 0.2s ease;
}

.sidebar-collapse-button:hover {
  background-color: #f5f5f5;
  color: #333;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

/* 展开侧边栏按钮 */
.sidebar-expand-button {
  position: fixed;
  top: 50%;
  left: 14px;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  background-color: #fff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #999;
  font-size: 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 20;
  transition: all 0.2s ease;
}

.sidebar-expand-button:hover {
  background-color: #f5f5f5;
  color: #333;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

@media (max-width: 768px) {
  .sidebar {
    width: 240px;
  }
}

@media (max-width: 576px) {
  .sidebar {
    display: none;
  }
}
</style> 