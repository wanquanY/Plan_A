import { watch, onBeforeMount } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import authService from '../services/auth';

export function useRouteManager() {
  const router = useRouter();
  const route = useRoute();

  // 处理路由初始化逻辑
  const initializeRoute = (
    fetchNoteDetail: (noteId: number) => Promise<any>,
    fetchSessionDetail: (sessionId: number) => Promise<any>,
    fetchNoteBySessionId: (sessionId: number) => Promise<any>,
    createNewNote: () => void,
    clearSidebarHistory: () => void,
    fetchNotes?: (page?: number, autoLoad?: boolean) => void
  ) => {
    onBeforeMount(() => {
      // 只有当前路由是Home页面时才执行初始化逻辑
      if (route.name !== 'Home') {
        console.log('当前路由不是Home页面，跳过初始化逻辑');
        return;
      }
      
      // 首先检查URL中是否有笔记ID参数
      if (route.query.note) {
        // 无论是否有会话ID，只要有笔记ID就加载笔记内容
        const noteId = parseInt(route.query.note as string);
        if (!isNaN(noteId)) {
          console.log(`从URL参数设置笔记ID: ${noteId}`);
          
          // 如果同时有会话ID，也设置会话ID，但优先加载笔记内容
          if (route.query.id) {
            const sessionId = parseInt(route.query.id as string);
            if (!isNaN(sessionId)) {
              console.log(`URL中同时有会话ID: ${sessionId}，但优先加载笔记内容`);
            }
          }
          
          // 加载笔记内容
          fetchNoteDetail(noteId);
        }
      }
      // 如果只有会话ID参数，没有笔记ID参数
      else if (route.query.id) {
        const sessionId = parseInt(route.query.id as string);
        if (!isNaN(sessionId)) {
          // 设置当前会话ID并获取详情
          fetchSessionDetail(sessionId);
          
          // 尝试查找关联的笔记ID，但不加载笔记内容
          fetchNoteBySessionId(sessionId);
        }
      } else if (route.query.new) {
        // 如果URL中有new参数，表示用户想创建一个新笔记
        console.log('URL新建笔记，清理侧边栏对话历史记录');
        clearSidebarHistory();
        createNewNote();
      } else {
        // 如果URL中没有任何参数，且用户已登录，检查是否有默认笔记
        if (authService.isAuthenticated()) {
          const defaultNoteId = authService.getDefaultNoteId();
          if (defaultNoteId) {
            console.log(`发现默认笔记ID: ${defaultNoteId}，自动加载`);
            fetchNoteDetail(defaultNoteId);

            // 加载成功后清除默认笔记ID，这样只有首次登录会自动打开
            localStorage.removeItem('default_note_id');
          } else if (fetchNotes) {
            // 如果没有默认笔记，加载用户的笔记列表
            console.log('没有默认笔记，加载笔记列表');
            fetchNotes(1, true);
          }
        } else if (fetchNotes) {
          // 未登录状态，加载笔记列表
          fetchNotes(1, true);
        }
      }
    });
  };

  // 监听路由变化
  const watchRouteChanges = (
    fetchNoteDetail: (noteId: number) => Promise<any>,
    fetchSessionDetail: (sessionId: number) => Promise<any>,
    fetchNoteBySessionId: (sessionId: number) => Promise<any>,
    createNewNote: () => void,
    clearSidebarHistory: () => void
  ) => {
    watch(() => route.query, (newQuery) => {
      // 只有当前路由是Home页面时才执行路由监听逻辑
      if (route.name !== 'Home') {
        console.log('当前路由不是Home页面，跳过路由监听逻辑');
        return;
      }
      
      // 首先检查URL中是否有笔记ID参数
      if (newQuery.note) {
        // 无论是否有会话ID，只要有笔记ID就加载笔记内容
        const noteId = parseInt(newQuery.note as string);
        if (!isNaN(noteId)) {
          console.log(`从URL参数变化设置笔记ID: ${noteId}`);
          
          // 如果同时有会话ID，也设置会话ID，但优先加载笔记内容
          if (newQuery.id) {
            const sessionId = parseInt(newQuery.id as string);
            if (!isNaN(sessionId)) {
              console.log(`URL中同时有会话ID: ${sessionId}，但优先加载笔记内容`);
            }
          }
          
          // 加载笔记内容
          fetchNoteDetail(noteId);
        }
      }
      // 如果只有会话ID参数，没有笔记ID参数
      else if (newQuery.id) {
        const sessionId = parseInt(newQuery.id as string);
        if (!isNaN(sessionId)) {
          fetchSessionDetail(sessionId);
          
          // 尝试查找关联的笔记ID，但不加载笔记内容
          fetchNoteBySessionId(sessionId);
        }
      } else if (newQuery.new) {
        // 如果URL中有new参数，表示用户想创建一个新笔记
        console.log('URL新建笔记，清理侧边栏对话历史记录');
        clearSidebarHistory();
        createNewNote();
      }
    }, { deep: true });
  };

  // 导航到其他页面
  const handleNavigation = (path: string) => {
    router.push(path);
  };

  // 更新URL参数
  const updateUrlParams = (params: Record<string, any>) => {
    router.push({
      query: {
        ...route.query,
        ...params
      }
    });
  };

  return {
    router,
    route,
    initializeRoute,
    watchRouteChanges,
    handleNavigation,
    updateUrlParams
  };
} 