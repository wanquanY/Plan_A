<script setup lang="ts">
import { ref, computed, onMounted, nextTick, inject, watch } from 'vue';
import { useRoute } from 'vue-router';
import { 
  LogoutOutlined, 
  FileOutlined,
  PlusOutlined,
  LeftOutlined,
  RightOutlined,
  UserOutlined,
  RobotOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue';
import UserDropdownMenu from './UserDropdownMenu.vue';
import noteService from '../services/note';
import chatService from '../services/chat';
import { message } from 'ant-design-vue';

const route = useRoute();

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
  notes: {
    type: Array,
    default: () => []
  },
  activeTab: {
    type: String,
    default: 'notes'
  },
  currentSessionId: {
    type: [String, null],
    default: null
  },
  collapsed: {
    type: Boolean,
    default: false
  },
  pagination: {
    type: Object,
    default: () => ({})
  },
  notesPagination: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  },
  hasMore: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['logout', 'switch-tab', 'session-click', 'note-click', 'toggle-sidebar', 'new-note', 'nav-to', 'load-more', 'note-renamed', 'note-deleted']);

// 确保始终使用笔记标签
onMounted(() => {
  // 如果当前标签不是notes，则切换到notes
  if (props.activeTab !== 'notes') {
    emit('switch-tab', 'notes');
  }
});

// 监听activeTab变化，确保始终为notes
watch(() => props.activeTab, (newTab) => {
  if (newTab !== 'notes') {
    emit('switch-tab', 'notes');
  }
});

// 用户菜单显示状态
const userMenuVisible = ref(false);
const menuPosition = ref({ x: 0, y: 0 });

// 重命名对话框状态
const showRenameInput = ref(false);
const editingNoteId = ref<string | null>(null);
const newNoteName = ref('');

// 会话重命名状态
const showSessionRenameInput = ref(false);
const editingSessionId = ref<string | null>(null);
const newSessionName = ref('');

// 从全局布局中注入刷新笔记和会话列表的方法
const fetchNotes = inject('fetchNotes');
const fetchSessions = inject('fetchSessions');

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

// 处理滚动加载更多
const handleScroll = (e) => {
  if ((props.activeTab === 'sessions' && !props.hasMore) || 
      (props.activeTab === 'notes' && !props.notesPagination.hasMore) || 
      props.loading) return;
  
  const el = e.target;
  // 如果滚动到距离底部100px以内，触发加载更多
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 100) {
    emit('load-more');
  }
};

// 处理重命名笔记点击
const handleRenameClick = (event, note) => {
  event.stopPropagation();
  showRenameInput.value = true;
  editingNoteId.value = note.id;
  newNoteName.value = note.title;
  
  // 在下一个DOM更新周期后聚焦输入框
  nextTick(() => {
    const inputElement = document.querySelector('.rename-input');
    if (inputElement) {
      inputElement.focus();
      // 选中所有文本方便用户直接输入
      inputElement.select();
    }
  });
};

// 处理重命名提交
const submitRename = async (event) => {
  event.stopPropagation();
  if (!newNoteName.value.trim()) {
    message.error('笔记名称不能为空');
    return;
  }
  
  try {
    // 保存当前编辑的笔记ID，因为重置状态后会被清空
    const currentEditingNoteId = editingNoteId.value;
    const newTitle = newNoteName.value.trim();
    
    await noteService.updateNote(currentEditingNoteId, {
      title: newTitle
    });
    
    // 更新成功提示
    message.success('笔记重命名成功');
    
    // 重置状态
    showRenameInput.value = false;
    editingNoteId.value = null;
    
    // 刷新笔记列表 - 使用注入的fetchNotes方法，从第1页开始重新获取笔记
    if (fetchNotes) {
      fetchNotes(1, false);
    }

    // 发出note-renamed事件 - 使用保存的noteId
    emit('note-renamed', { noteId: currentEditingNoteId, title: newTitle });
  } catch (error) {
    console.error('重命名笔记失败:', error);
    message.error('重命名失败，请稍后重试');
  }
};

// 处理删除笔记点击
const handleDeleteClick = async (event, note) => {
  event.stopPropagation();
  
  try {
    // 确认删除
    if (confirm(`确定要删除笔记"${note.title}"吗？此操作不可恢复。`)) {
      // 保存删除前的笔记信息，用于确定下一个要打开的笔记
      const deletedNoteId = note.id;
      const currentNoteIndex = props.notes.findIndex(n => n.id === deletedNoteId);
      
      const success = await noteService.deleteNote(note.id);
      
      if (success) {
        message.success('笔记已删除');
        
        // 刷新笔记列表 - 使用注入的fetchNotes方法，从第1页开始重新获取笔记
        if (fetchNotes) {
          await fetchNotes(1, false);
        }
        
        // 发出note-deleted事件，传递被删除的笔记ID和索引信息
        emit('note-deleted', { 
          deletedNoteId: deletedNoteId,
          deletedNoteIndex: currentNoteIndex,
          totalNotes: props.notes.length
        });
      } else {
        message.error('删除笔记失败');
      }
    }
  } catch (error) {
    console.error('删除笔记失败:', error);
    message.error('删除失败，请稍后重试');
  }
};

// 取消重命名
const cancelRename = (event) => {
  event.stopPropagation();
  showRenameInput.value = false;
  editingNoteId.value = null;
  newNoteName.value = '';
};

// 处理重命名会话点击
const handleSessionRenameClick = (event, session) => {
  event.stopPropagation();
  showSessionRenameInput.value = true;
  editingSessionId.value = session.id;
  newSessionName.value = session.title;
  
  // 在下一个DOM更新周期后聚焦输入框
  nextTick(() => {
    const inputElement = document.querySelector('.session-rename-input');
    if (inputElement) {
      inputElement.focus();
      // 选中所有文本方便用户直接输入
      inputElement.select();
    }
  });
};

// 处理重命名会话提交
const submitSessionRename = async (event) => {
  event.stopPropagation();
  if (!newSessionName.value.trim()) {
    message.error('会话名称不能为空');
    return;
  }
  
  try {
    const success = await chatService.updateSession(editingSessionId.value, newSessionName.value.trim());
    
    if (success) {
      // 更新成功提示
      message.success('会话重命名成功');
      
      // 重置状态
      showSessionRenameInput.value = false;
      editingSessionId.value = null;
      
      // 刷新会话列表
      if (fetchSessions) {
        fetchSessions(1, false);
      } else if (window.refreshSessions) {
        window.refreshSessions();
      }
    } else {
      message.error('重命名失败，请稍后重试');
    }
  } catch (error) {
    console.error('重命名会话失败:', error);
    message.error('重命名失败，请稍后重试');
  }
};

// 取消重命名会话
const cancelSessionRename = (event) => {
  event.stopPropagation();
  showSessionRenameInput.value = false;
  editingSessionId.value = null;
  newSessionName.value = '';
};

// 处理删除会话点击
const handleSessionDeleteClick = async (event, session) => {
  event.stopPropagation();
  
  try {
    // 确认删除
    if (confirm(`确定要删除会话"${session.title}"吗？此操作不可恢复。`)) {
      const success = await chatService.deleteSession(session.id);
      
      if (success) {
        message.success('会话已删除');
        // 刷新会话列表
        if (fetchSessions) {
          fetchSessions(1, false);
        } else if (window.refreshSessions) {
          window.refreshSessions();
        }
      } else {
        message.error('删除会话失败');
      }
    }
  } catch (error) {
    console.error('删除会话失败:', error);
    message.error('删除失败，请稍后重试');
  }
};

// 处理笔记点击
const noteItemClick = (noteId: string, event: Event) => {
  console.log(`笔记被点击，ID: ${noteId}`);
  event.stopPropagation();
  emit('note-click', noteId);
};
</script>

<template>
  <!-- 侧边栏 -->
  <div class="sidebar" :class="{ 'sidebar-collapsed': collapsed }">
    <div class="sidebar-top">
      <div class="logo">
        <div class="logo-icon">P</div>
        <div class="logo-text-container">
          <span class="logo-text">Plan<span class="logo-highlight">_A</span></span>
        </div>
      </div>
    </div>
    
    <div class="sidebar-middle" @scroll="handleScroll">
      <button class="new-note-button" @click="emit('new-note')">
        <PlusOutlined />
        <span>新建笔记</span>
      </button>
      
      <div class="note-tabs">
        <div 
          class="note-tab" 
          :class="{ active: activeTab === 'notes' }"
          @click="emit('switch-tab', 'notes')"
        >
          <span>我的笔记</span>
        </div>
        <!-- 隐藏会话聊天标签
        <div 
          class="note-tab" 
          :class="{ active: activeTab === 'sessions' }"
          @click="emit('switch-tab', 'sessions')"
        >
          <span>聊天会话</span>
        </div>
        -->
      </div>
      
      <!-- 笔记列表 -->
      <div class="note-list">
        <div 
          v-for="note in notes" 
          :key="note.id" 
          class="note-item" 
          :class="{ active: note.id === route.query.note }"
          @click="noteItemClick(note.id, $event)"
        >
          <div class="note-content">
            <div v-if="showRenameInput && editingNoteId === note.id" class="rename-input-wrapper" @click.stop>
              <input
                type="text"
                v-model="newNoteName"
                class="rename-input"
                @keyup.enter="submitRename"
                @keyup.esc="cancelRename"
                ref="renameInput"
                placeholder="输入笔记名称，回车确认"
              />
              <div class="rename-tip">回车确认，Esc取消</div>
            </div>
            <div v-else class="note-title">{{ note.title }}</div>
            <div class="note-meta">
              <span class="time">{{ formatDate(note.updated_at) }}</span>
            </div>
          </div>
          <div class="note-actions">
            <button class="action-btn" @click="handleRenameClick($event, note)" title="重命名">
              <EditOutlined />
            </button>
            <button class="action-btn delete" @click="handleDeleteClick($event, note)" title="删除">
              <DeleteOutlined />
            </button>
          </div>
        </div>
        <div v-if="notes.length === 0" class="empty-state">
          暂无笔记，点击「新建笔记」开始创作
        </div>
        
        <!-- 加载状态指示器 -->
        <div v-if="notesPagination.loading" class="loading-indicator">
          <div class="loading-spinner"></div>
          <span>加载中...</span>
        </div>
        
        <!-- 全部加载完毕提示 -->
        <div v-else-if="!notesPagination.hasMore && notes.length > 0" class="end-message">
          已加载全部内容
        </div>
      </div>
      
      <!-- 会话列表已隐藏
      <div class="note-list" v-if="activeTab === 'sessions'">
        <div 
          v-for="session in sessions" 
          :key="session.id" 
          class="note-item" 
          :class="{ active: session.id === route.query.id }"
          @click="emit('session-click', session.id)"
        >
          <div class="note-content">
            <div v-if="showSessionRenameInput && editingSessionId === session.id" class="rename-input-wrapper" @click.stop>
              <input
                type="text"
                v-model="newSessionName"
                class="rename-input session-rename-input"
                @keyup.enter="submitSessionRename"
                @keyup.esc="cancelSessionRename"
                placeholder="输入会话名称，回车确认"
              />
              <div class="rename-tip">回车确认，Esc取消</div>
            </div>
            <div v-else class="note-title">{{ session.title }}</div>
            <div class="note-meta">
              <span class="message-preview">{{ truncateMessage(session.last_message) }}</span>
              <span class="time">{{ formatDate(session.updated_at) }}</span>
            </div>
          </div>
          <div class="note-actions">
            <button class="action-btn" @click="handleSessionRenameClick($event, session)" title="重命名">
              <EditOutlined />
            </button>
            <button class="action-btn delete" @click="handleSessionDeleteClick($event, session)" title="删除">
              <DeleteOutlined />
            </button>
          </div>
        </div>
        <div v-if="sessions.length === 0" class="empty-state">
          暂无聊天会话记录
        </div>
        
        加载状态指示器
        <div v-if="pagination.loading" class="loading-indicator">
          <div class="loading-spinner"></div>
          <span>加载中...</span>
        </div>
        
        全部加载完毕提示
        <div v-else-if="!pagination.hasMore && sessions.length > 0" class="end-message">
          已加载全部内容
        </div>
      </div>
      -->
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
  gap: 10px;
}

.logo-text-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.logo-icon {
  background: linear-gradient(135deg, #1890ff, #722ed1);
  color: white;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 18px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #333;
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.logo-highlight {
  color: #1890ff;
  font-weight: 800;
}

.sidebar-middle {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: auto;
  scrollbar-width: thin; /* Firefox */
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent; /* Firefox */
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
  background-color: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
  border: none;
  transition: background-color 0.2s ease;
}

.sidebar-middle::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.25);
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.note-item:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.note-item.active {
  background-color: rgba(0, 123, 255, 0.1);
}

.note-content {
  flex: 1;
  min-width: 0; /* 让子元素能够正常缩小 */
  margin-right: 10px; /* 为右侧按钮留出空间 */
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
  left: 14px;
  top: 50%;
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

/* 加载指示器样式 */
.loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15px 0;
  color: #888;
  font-size: 13px;
  gap: 8px;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(0, 123, 255, 0.3);
  border-radius: 50%;
  border-top-color: #007bff;
  animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.end-message {
  text-align: center;
  padding: 15px 0;
  color: #888;
  font-size: 13px;
}

/* 笔记操作按钮样式 */
.note-actions {
  display: none;
  gap: 6px;
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background-color: rgba(255, 255, 255, 0.9);
  padding: 2px;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.note-item:hover .note-actions {
  display: flex;
}

.action-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #666;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 12px;
}

.action-btn:hover {
  background-color: rgba(0, 0, 0, 0.08);
  color: #1890ff;
}

.action-btn.delete:hover {
  background-color: rgba(255, 0, 0, 0.1);
  color: #ff4d4f;
}

/* 重命名输入框样式 */
.rename-input-wrapper {
  width: 100%;
}

.rename-input {
  width: 100%;
  padding: 6px 8px;
  border-radius: 4px;
  border: 1px solid #d9d9d9;
  font-size: 14px;
  margin-bottom: 2px;
  box-sizing: border-box;
}

.rename-input:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.rename-tip {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style> 