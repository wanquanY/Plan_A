<template>
  <div class="sidebar-header">
    <!-- 会话标签页区域 -->
    <div class="session-tabs-container">
      <div class="session-tabs">
        <div
          v-for="session in displayedSessions"
          :key="session.id"
          class="session-tab"
          :class="{ active: session.id === currentSessionId }"
          @click="switchToSession(session.id)"
        >
          <span class="session-title">{{ getSessionDisplayTitle(session) }}</span>
          <button
            v-if="sessions.length > 1"
            class="session-close"
            @click.stop="hideSession(session.id)"
            title="隐藏对话"
          >
            ×
          </button>
        </div>
        
        <!-- 如果有更多会话，显示省略号指示器 -->
        <div v-if="sessions.length > 3" class="more-sessions-indicator" title="还有更多会话">
          <span>...</span>
        </div>
      </div>
      
      <!-- 创建新会话按钮 -->
      <button class="new-session-button" @click="createNewSession" title="创建新对话">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
      
      <!-- 历史记录按钮 -->
      <button 
        class="history-button" 
        @click="toggleHistoryDropdown" 
        title="查看会话历史"
        ref="historyButtonRef"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12,6 12,12 16,14"></polyline>
        </svg>
      </button>
    </div>
    
    <!-- 关闭按钮 -->
    <button class="close-button" @click="$emit('close')" title="关闭侧边栏">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </button>
    
    <!-- 历史记录弹窗 -->
    <Teleport to="body">
      <div 
        v-if="showHistoryDropdown" 
        class="history-dropdown-overlay" 
        @click="closeHistoryDropdown"
      >
        <div 
          class="history-dropdown" 
          :style="historyDropdownPosition"
          @click.stop
        >
          <div class="history-dropdown-header">
            <h4>会话历史记录</h4>
            <span class="history-count">{{ sessions.length }} 个会话</span>
          </div>
          <div class="history-dropdown-content">
            <div 
              v-for="session in sessions" 
              :key="session.id"
              class="history-item"
              :class="{ 
                active: session.id === currentSessionId,
                hidden: hiddenSessionIds.has(session.id)
              }"
              @click="switchToSessionFromHistory(session.id)"
            >
              <div class="history-item-content">
                <div class="history-item-title">
                  {{ getSessionDisplayTitle(session) }}
                  <span v-if="hiddenSessionIds.has(session.id)" class="hidden-indicator">(已隐藏)</span>
                </div>
                <div class="history-item-meta">
                  <span class="history-item-time">{{ formatSessionTime(session.updated_at) }}</span>
                  <span class="message-count">{{ session.message_count || 0 }} 条消息</span>
                </div>
              </div>
              <div class="history-item-actions">
                <button 
                  v-if="sessions.length > 1"
                  class="unlink-btn"
                  @click.stop="removeSessionFromHistory(session.id)"
                  title="取消关联"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>
            </div>
            <div v-if="sessions.length === 0" class="no-sessions">
              暂无会话记录
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, inject, nextTick, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import noteSessionService, { type NoteSession } from '../../../services/noteSession';

const props = defineProps({
  noteId: {
    type: [Number, String, null],
    default: null
  }
});

const emit = defineEmits(['close', 'session-switched']);

const router = useRouter();
const sessions = ref<NoteSession[]>([]);
const currentSessionId = ref<number | null>(null);

// 历史记录弹窗相关状态
const showHistoryDropdown = ref(false);
const historyButtonRef = ref(null);
const historyDropdownPosition = ref({});

// 隐藏的会话ID列表
const hiddenSessionIds = ref<Set<number>>(new Set());

// 从全局注入当前会话ID
const globalCurrentSessionId = inject<any>('currentSessionId');

// 加载笔记的会话列表
const loadNoteSessions = async (noteId: number) => {
  try {
    console.log('[AgentSidebarHeader] 开始加载笔记会话列表, noteId:', noteId);
    const sessionList = await noteSessionService.getNoteSessions(noteId);
    sessions.value = sessionList;
    
    console.log('[AgentSidebarHeader] 加载会话列表成功:', sessionList.map(s => ({
      id: s.id,
      title: s.title,
      is_primary: s.is_primary,
      display_title: getSessionDisplayTitle(s)
    })));
    
    // 如果没有当前会话ID，设置为最近使用的会话（列表中第一个）
    if (!currentSessionId.value && sessionList.length > 0) {
      // 由于会话列表已经按最近使用时间排序，直接选择第一个会话
      const recentSession = sessionList[0];
      console.log('[AgentSidebarHeader] 设置当前会话ID为最近使用的会话:', recentSession.id);
      currentSessionId.value = recentSession.id;
      if (globalCurrentSessionId) {
        globalCurrentSessionId.value = recentSession.id;
      }
    }
  } catch (error) {
    console.error('[AgentSidebarHeader] 加载笔记会话列表失败:', error);
    sessions.value = [];
  }
};

// 计算属性：最多显示3个会话，优先显示当前活跃会话，排除隐藏的会话
const displayedSessions = computed(() => {
  // 过滤掉隐藏的会话
  const visibleSessions = sessions.value.filter(s => !hiddenSessionIds.value.has(s.id));
  
  if (visibleSessions.length <= 3) {
    return visibleSessions;
  }
  
  // 如果有超过3个会话，优先显示当前活跃会话
  const currentSession = visibleSessions.find(s => s.id === currentSessionId.value);
  const otherSessions = visibleSessions.filter(s => s.id !== currentSessionId.value);
  
  const result = [];
  
  // 先加入当前会话（如果存在）
  if (currentSession) {
    result.push(currentSession);
  }
  
  // 然后按优先级加入其他会话，直到达到3个
  const remainingSlots = 3 - result.length;
  result.push(...otherSessions.slice(0, remainingSlots));
  
  return result;
});

// 生成会话显示标题
const getSessionDisplayTitle = (session: NoteSession): string => {
  return noteSessionService.generateSessionDisplayTitle(session);
};

// 监听全局会话ID变化
watch(() => globalCurrentSessionId?.value, (newSessionId) => {
  if (newSessionId && newSessionId !== currentSessionId.value) {
    currentSessionId.value = Number(newSessionId);
  }
}, { immediate: true });

// 监听笔记ID变化，重新加载会话列表
watch(() => props.noteId, async (newNoteId) => {
  console.log('[AgentSidebarHeader] 笔记ID变化:', newNoteId);
  if (newNoteId) {
    await loadNoteSessions(Number(newNoteId));
  } else {
    console.log('[AgentSidebarHeader] 没有笔记ID，清空会话列表');
    sessions.value = [];
  }
}, { immediate: true });

// 切换到指定会话
const switchToSession = (sessionId: number) => {
  if (sessionId === currentSessionId.value) return;
  
  console.log('[AgentSidebarHeader] 切换到会话:', sessionId);
  
  currentSessionId.value = sessionId;
  if (globalCurrentSessionId) {
    globalCurrentSessionId.value = sessionId;
  }
  
  // 更新URL
  router.push({
    query: {
      ...router.currentRoute.value.query,
      id: sessionId
    }
  });
  
  emit('session-switched', sessionId);
};

// 创建新会话
const createNewSession = async () => {
  console.log('[AgentSidebarHeader] 创建新会话按钮被点击');
  console.log('[AgentSidebarHeader] 当前noteId:', props.noteId);
  console.log('[AgentSidebarHeader] 创建前 - currentSessionId:', currentSessionId.value);
  console.log('[AgentSidebarHeader] 创建前 - globalCurrentSessionId:', globalCurrentSessionId?.value);
  console.log('[AgentSidebarHeader] 创建前 - sessions数量:', sessions.value.length);
  
  if (!props.noteId) {
    console.error('[AgentSidebarHeader] 没有noteId，无法创建会话');
    message.error('请先选择一个笔记');
    return;
  }
  
  try {
    console.log('[AgentSidebarHeader] 开始创建新会话，笔记ID:', props.noteId);
    
    const newSession = await noteSessionService.createSessionForNote(Number(props.noteId));
    
    console.log('[AgentSidebarHeader] 新会话创建成功:', newSession);
    
    // 先更新当前会话ID到新会话
    console.log('[AgentSidebarHeader] 步骤1: 设置currentSessionId为新会话ID:', newSession.id);
    currentSessionId.value = newSession.id;
    if (globalCurrentSessionId) {
      globalCurrentSessionId.value = newSession.id;
      console.log('[AgentSidebarHeader] 步骤1: 已更新globalCurrentSessionId为:', newSession.id);
    }
    
    // 重新加载会话列表
    console.log('[AgentSidebarHeader] 步骤2: 开始重新加载会话列表');
    await loadNoteSessions(Number(props.noteId));
    console.log('[AgentSidebarHeader] 步骤2: 会话列表重新加载完成，当前sessions数量:', sessions.value.length);
    
    // 确保新会话被设置为当前会话（防止loadNoteSessions重置）
    console.log('[AgentSidebarHeader] 步骤3: 再次确保设置currentSessionId为:', newSession.id);
    currentSessionId.value = newSession.id;
    if (globalCurrentSessionId) {
      globalCurrentSessionId.value = newSession.id;
      console.log('[AgentSidebarHeader] 步骤3: 再次确保globalCurrentSessionId为:', newSession.id);
    }
    
    // 使用nextTick确保Vue组件更新
    await nextTick();
    console.log('[AgentSidebarHeader] 步骤4: nextTick完成，当前显示的会话数量:', displayedSessions.value.length);
    console.log('[AgentSidebarHeader] 步骤4: 当前活跃会话ID:', currentSessionId.value);
    console.log('[AgentSidebarHeader] 步骤4: displayedSessions:', displayedSessions.value.map(s => ({
      id: s.id,
      title: s.title,
      isActive: s.id === currentSessionId.value
    })));
    
    // 更新URL
    console.log('[AgentSidebarHeader] 步骤5: 更新URL');
    router.push({
      query: {
        ...router.currentRoute.value.query,
        id: newSession.id
      }
    });
    
    // 发射会话切换事件
    console.log('[AgentSidebarHeader] 步骤6: 发射会话切换事件:', newSession.id);
    emit('session-switched', newSession.id);
    
    console.log('[AgentSidebarHeader] 创建新会话流程完成 - 最终currentSessionId:', currentSessionId.value);
    console.log('[AgentSidebarHeader] 创建新会话流程完成 - 最终globalCurrentSessionId:', globalCurrentSessionId?.value);
    
    message.success('新对话创建成功');
  } catch (error) {
    console.error('[AgentSidebarHeader] 创建新会话失败:', error);
    message.error('创建新对话失败');
  }
};

// 隐藏会话（从标签中移除，但不取消关联）
const hideSession = async (sessionId: number) => {
  // 检查是否是最后一个可见的会话
  const visibleSessions = sessions.value.filter(s => !hiddenSessionIds.value.has(s.id));
  if (visibleSessions.length <= 1) {
    message.warning('至少需要保留一个显示的对话');
    return;
  }
  
  // 将会话ID添加到隐藏列表
  hiddenSessionIds.value.add(sessionId);
  
  // 如果隐藏的是当前会话，切换到第一个可见的会话
  if (sessionId === currentSessionId.value) {
    const remainingVisibleSessions = sessions.value.filter(s => !hiddenSessionIds.value.has(s.id));
    if (remainingVisibleSessions.length > 0) {
      switchToSession(remainingVisibleSessions[0].id);
    }
  }
  
  message.success('对话已从标签中移除，可在历史记录中找到');
};

// 移除会话关联（保持原有功能，仅在历史记录弹窗中使用）
const removeSession = async (sessionId: number) => {
  if (!props.noteId || sessions.value.length <= 1) {
    message.warning('至少需要保留一个对话');
    return;
  }
  
  try {
    await noteSessionService.unlinkSession(Number(props.noteId), sessionId);
    
    // 重新加载会话列表
    await loadNoteSessions(Number(props.noteId));
    
    // 如果移除的是当前会话，切换到第一个会话
    if (sessionId === currentSessionId.value && sessions.value.length > 0) {
      switchToSession(sessions.value[0].id);
    }
    
    message.success('对话关联已取消');
  } catch (error) {
    console.error('取消会话关联失败:', error);
    message.error('取消关联失败');
  }
};

// 切换历史记录弹窗显示状态
const toggleHistoryDropdown = () => {
  if (showHistoryDropdown.value) {
    closeHistoryDropdown();
  } else {
    openHistoryDropdown();
  }
};

// 打开历史记录弹窗
const openHistoryDropdown = () => {
  if (historyButtonRef.value) {
    const rect = historyButtonRef.value.getBoundingClientRect();
    historyDropdownPosition.value = {
      position: 'fixed',
      top: rect.bottom + 8 + 'px',
      left: rect.left - 250 + 'px', // 向左偏移，避免超出屏幕
      zIndex: 1000
    };
  }
  showHistoryDropdown.value = true;
};

// 关闭历史记录弹窗
const closeHistoryDropdown = () => {
  showHistoryDropdown.value = false;
};

// 从历史记录中切换会话
const switchToSessionFromHistory = (sessionId: number) => {
  // 如果是隐藏的会话，先显示它
  if (hiddenSessionIds.value.has(sessionId)) {
    hiddenSessionIds.value.delete(sessionId);
    message.success('对话已重新添加到标签');
  }
  
  switchToSession(sessionId);
  closeHistoryDropdown();
};

// 从历史记录中移除会话
const removeSessionFromHistory = async (sessionId: number) => {
  await removeSession(sessionId);
  // 弹窗会在loadNoteSessions重新加载后自动更新
};

// 格式化会话时间
const formatSessionTime = (timeString: string): string => {
  if (!timeString) return '';
  
  const date = new Date(timeString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor(diff / (1000 * 60));
  
  if (days > 0) {
    return `${days}天前`;
  } else if (hours > 0) {
    return `${hours}小时前`;
  } else if (minutes > 0) {
    return `${minutes}分钟前`;
  } else {
    return '刚刚';
  }
};

// 截断文本
const truncateText = (text: string, maxLength: number): string => {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

onMounted(() => {
  if (props.noteId) {
    loadNoteSessions(Number(props.noteId));
  }
  
  // 添加点击外部关闭弹窗的监听
  document.addEventListener('click', handleClickOutside);
});

// 组件卸载时移除监听器
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

// 处理点击外部关闭弹窗
const handleClickOutside = (event: Event) => {
  if (showHistoryDropdown.value && historyButtonRef.value) {
    const target = event.target as Element;
    if (!historyButtonRef.value.contains(target)) {
      closeHistoryDropdown();
    }
  }
};

// 暴露方法给父组件
defineExpose({
  refreshSessions: () => {
    if (props.noteId) {
      console.log('[AgentSidebarHeader] 外部调用刷新会话列表');
      loadNoteSessions(Number(props.noteId));
    }
  }
});
</script>

<style scoped>
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
  min-height: 48px;
}

.session-tabs-container {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.session-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.session-tabs::-webkit-scrollbar {
  display: none;
}

.session-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px 6px 0 0;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
  max-width: 100px;
  font-size: 12px;
  position: relative;
  color: #64748b;
  border-bottom: 2px solid transparent;
}

.session-tab:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
  color: #475569;
}

.session-tab.active {
  background: #ffffff;
  border-color: #3b82f6;
  color: #1e40af;
  border-bottom-color: #3b82f6;
  font-weight: 500;
}

.session-tab.active::before {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  right: 0;
  height: 2px;
  background: #3b82f6;
  border-radius: 1px 1px 0 0;
}

.session-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  font-weight: inherit;
}

.session-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  background: transparent;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 11px;
  line-height: 1;
  opacity: 0;
  transition: all 0.15s ease;
  color: inherit;
}

.session-tab:hover .session-close {
  opacity: 0.6;
}

.session-close:hover {
  opacity: 1;
  background: rgba(248, 113, 113, 0.1);
  color: #dc2626;
}

.session-tab.active .session-close {
  opacity: 0.5;
}

.session-tab.active .session-close:hover {
  opacity: 1;
  background: rgba(248, 113, 113, 0.1);
  color: #dc2626;
}

.more-sessions-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 6px;
  color: #9ca3af;
  font-size: 11px;
  font-weight: normal;
  cursor: help;
  opacity: 0.7;
}

.new-session-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.15s ease;
  margin-left: 6px;
  flex-shrink: 0;
}

.new-session-button:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #475569;
}

.close-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.15s ease;
  margin-left: 6px;
  flex-shrink: 0;
}

.close-button:hover {
  background: #f1f5f9;
  color: #475569;
}

.history-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.15s ease;
  margin-left: 6px;
  flex-shrink: 0;
}

.history-button:hover {
  background: #f1f5f9;
  color: #475569;
}

.history-dropdown-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.3);
  z-index: 999;
}

.history-dropdown {
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  width: 320px;
  max-height: 400px;
  overflow: hidden;
}

.history-dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #f8fafc;
}

.history-dropdown-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1e40af;
}

.history-count {
  font-size: 12px;
  color: #64748b;
  background: #e2e8f0;
  padding: 2px 6px;
  border-radius: 10px;
}

.history-dropdown-content {
  max-height: 320px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
}

.history-dropdown-content::-webkit-scrollbar {
  width: 4px;
}

.history-dropdown-content::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}

.history-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
  border: 1px solid transparent;
}

.history-item:hover {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.history-item.active {
  background: #eff6ff;
  border-color: #3b82f6;
}

.history-item.hidden {
  opacity: 0.6;
  background: #f9fafb;
  border-color: #e5e7eb;
  border-style: dashed;
}

.history-item.hidden:hover {
  opacity: 0.8;
  background: #f3f4f6;
}

.history-item-content {
  flex: 1;
  min-width: 0;
}

.history-item-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
}

.hidden-indicator {
  font-size: 12px;
  color: #6b7280;
  font-weight: normal;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid #d1d5db;
}

.history-item-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #6b7280;
}

.history-item-time {
  color: #9ca3af;
}

.message-count {
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.history-item-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 8px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.history-item:hover .history-item-actions {
  opacity: 1;
}

.unlink-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
  color: #ef4444;
}

.unlink-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}

.no-sessions {
  text-align: center;
  padding: 32px 16px;
  color: #9ca3af;
  font-size: 13px;
}
</style> 