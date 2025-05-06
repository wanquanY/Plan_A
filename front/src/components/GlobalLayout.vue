<script setup lang="ts">
import { ref, computed, onMounted, provide, reactive } from 'vue';
import { useRouter } from 'vue-router';
import Sidebar from './Sidebar.vue';
import { message } from 'ant-design-vue';
import chatService from '../services/chat';
import noteService from '../services/note';

// 状态
const router = useRouter();
const username = ref('用户');
const sidebarCollapsed = ref(false);
const sessions = ref([]);
const notes = ref([]);
const currentSessionId = ref(null);
const activeTab = ref('notes');

// 分页相关数据
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  pages: 1,
  loading: false,
  hasMore: true
});

// 笔记分页相关数据
const notesPagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  pages: 1,
  loading: false,
  hasMore: true
});

// 从token中解析用户名
onMounted(() => {
  const token = localStorage.getItem('access_token') || '';
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.sub) {
        username.value = payload.sub;
      }
    } catch (e) {
      console.error('解析token失败', e);
    }
  }
  
  // 获取笔记列表
  fetchNotes();
  
  // 在其他组件中可以调用window.refreshSessions()来刷新会话列表
  if (typeof window !== 'undefined') {
    const originalRefreshSessions = window.refreshSessions;
    window.refreshSessions = async () => {
      await originalRefreshSessions?.();
      if (window.sessionData) {
        // 使用全局刷新的会话数据更新本地状态
        sessions.value = window.sessionData;
      }
    };
  }
});

// 获取笔记列表
const fetchNotes = async (page = 1, isLoadMore = false) => {
  try {
    console.log(`开始请求笔记列表，页码: ${page}...`);
    notesPagination.loading = true;
    
    if (page === 1) {
      notesPagination.hasMore = true; // 重置hasMore状态
    }
    
    const { notes: notesData, total, pages } = await noteService.getNotes(page, notesPagination.pageSize);
    
    console.log('笔记列表请求完成，结果:', notesData ? '成功' : '失败', 
      notesData ? `获取到${notesData.length}条笔记记录，总数: ${total}, 总页数: ${pages}` : '');
    
    if (notesData) {
      if (isLoadMore) {
        // 追加笔记列表
        notes.value = [...notes.value, ...notesData];
      } else {
        // 替换笔记列表
        notes.value = notesData;
      }
      
      notesPagination.current = page;
      notesPagination.total = total;
      notesPagination.pages = pages;
      
      // 判断是否还有更多数据
      notesPagination.hasMore = page < pages;
      
      console.log('笔记列表更新成功，当前笔记数量:', notes.value.length, '是否还有更多:', notesPagination.hasMore);
    }
  } catch (error) {
    console.error('获取笔记列表失败:', error);
  } finally {
    notesPagination.loading = false;
  }
};

// 获取会话列表
const fetchSessions = async (page = 1, isLoadMore = false) => {
  try {
    console.log(`开始请求会话列表，页码: ${page}...`);
    pagination.loading = true;
    
    if (page === 1) {
      pagination.hasMore = true; // 重置hasMore状态
    }
    
    const { sessions: sessionsData, total, pages } = await chatService.getSessions(page, pagination.pageSize);
    
    console.log('会话列表请求完成，结果:', sessionsData ? '成功' : '失败', 
      sessionsData ? `获取到${sessionsData.length}条会话记录，总数: ${total}, 总页数: ${pages}` : '');
    
    if (sessionsData) {
      if (isLoadMore) {
        // 追加会话列表
        sessions.value = [...sessions.value, ...sessionsData];
      } else {
        // 替换会话列表
        sessions.value = sessionsData;
      }
      
      pagination.current = page;
      pagination.total = total;
      pagination.pages = pages;
      
      // 判断是否还有更多数据
      pagination.hasMore = page < pages;
      
      console.log('会话列表更新成功，当前会话数量:', sessions.value.length, '是否还有更多:', pagination.hasMore);
    }
  } catch (error) {
    console.error('获取会话列表失败:', error);
  } finally {
    pagination.loading = false;
  }
};

// 处理加载更多
const handleLoadMore = () => {
  // 只处理笔记加载更多，不再处理会话加载更多
  if (notesPagination.loading || !notesPagination.hasMore) return;
  
  const nextPage = notesPagination.current + 1;
  if (nextPage <= notesPagination.pages) {
    fetchNotes(nextPage, true);
  }
};

// 处理会话点击
const fetchSessionDetail = async (sessionId) => {
  try {
    router.push(`/?id=${sessionId}`);
  } catch (error) {
    console.error('导航到会话详情失败:', error);
  }
};

// 处理笔记点击
const handleNoteClick = async (noteId) => {
  try {
    // 获取笔记的详细信息
    const noteDetail = await noteService.getNoteDetail(noteId);
    
    // 不管笔记是否关联会话，始终只使用笔记ID导航
    if (noteDetail) {
      // 只使用笔记ID进行导航，确保始终显示笔记内容
      router.push(`/?note=${noteId}`);
    } else {
      message.error('无法打开笔记，请稍后重试');
    }
  } catch (error) {
    console.error('打开笔记失败:', error);
    message.error('打开笔记失败，请稍后重试');
  }
};

// 处理标签切换
const handleTabSwitch = (tab) => {
  // 只处理笔记标签，忽略会话标签
  if (tab === 'notes') {
    activeTab.value = tab;
    fetchNotes();
  }
  // 不再处理会话标签的切换
};

// 处理登出
const handleLogout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('access_token');
  router.push('/login');
};

// 处理新建笔记
const handleNewNote = async () => {
  try {
    // 使用note服务创建新笔记，不设置默认标题
    const { note_id } = await noteService.createNote({
      title: "", // 空标题，将在用户输入第一行时自动设置
      content: "<p></p>"
    });
    
    // 清空当前会话ID
    currentSessionId.value = null;
    
    // 刷新笔记列表
    await fetchNotes();
    
    // 导航到新笔记（不再使用会话ID参数）
    router.push(`/?note=${note_id}`);
  } catch (error) {
    console.error("创建新笔记失败:", error);
    message.error("创建新笔记失败，请稍后重试");
  }
};

// 处理导航
const handleNavigation = (path) => {
  router.push(path);
};

// 提供全局数据给子组件
provide('sessions', sessions);
provide('notes', notes);
provide('fetchSessions', fetchSessions);
provide('fetchNotes', fetchNotes);
provide('currentSessionId', currentSessionId);
</script>

<template>
  <div class="layout-container">
    <div class="global-layout">
      <!-- 侧边栏 -->
      <Sidebar 
        :username="username"
        :sessions="sessions"
        :notes="notes"
        :current-session-id="currentSessionId"
        :active-tab="activeTab"
        :collapsed="sidebarCollapsed"
        :pagination="pagination"
        :notes-pagination="notesPagination"
        :loading="activeTab === 'notes' ? notesPagination.loading : pagination.loading"
        :hasMore="activeTab === 'notes' ? notesPagination.hasMore : pagination.hasMore"
        @logout="handleLogout"
        @switch-tab="handleTabSwitch"
        @session-click="fetchSessionDetail"
        @note-click="handleNoteClick"
        @toggle-sidebar="sidebarCollapsed = !sidebarCollapsed"
        @new-note="handleNewNote"
        @nav-to="handleNavigation"
        @load-more="handleLoadMore"
      />
      
      <!-- 主内容区 -->
      <div class="main-content" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
        <router-view></router-view>
      </div>
    </div>
  </div>
</template>

<style scoped>
.global-layout {
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