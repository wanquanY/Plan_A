import { watch, onBeforeMount } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import authService from '../services/auth';
import noteService from '../services/note';

export function useRouteManager() {
  const router = useRouter();
  const route = useRoute();

  // 加载最新笔记
  const loadLatestNote = async (fetchNoteDetail: (noteId: string) => Promise<any>) => {
    try {
      const { notes } = await noteService.getNotes(1, 1); // 获取第一页的第一条笔记（最新的）
      
      if (notes && notes.length > 0) {
        const latestNote = notes[0];
        console.log('自动加载最新笔记:', latestNote.id);
        
        // 更新URL参数
        router.push({
          query: {
            ...route.query,
            note: latestNote.id
          }
        });
        
        // 加载笔记详情
        await fetchNoteDetail(latestNote.id);
      } else {
        console.log('没有找到任何笔记');
      }
    } catch (error) {
      console.error('加载最新笔记失败:', error);
    }
  };

  // 处理路由初始化逻辑
  const initializeRoute = (
    fetchNoteDetail: (noteId: string) => Promise<any>,
    fetchSessionDetail: (sessionId: string) => Promise<any>,
    fetchNoteBySessionId: (sessionId: string) => Promise<any>,
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
        const noteId = route.query.note as string;
        if (noteId) {
          console.log(`从URL参数设置笔记ID: ${noteId}`);
          
          // 立即保存到localStorage，确保即使异步加载失败也能获取到
          localStorage.setItem('lastNoteId', noteId);
          
          // 如果同时有会话ID，也设置会话ID，但优先加载笔记内容
          if (route.query.id) {
            const sessionId = route.query.id as string;
            if (sessionId) {
              console.log(`URL中同时有会话ID: ${sessionId}，但优先加载笔记内容`);
            }
          }
          
          // 加载笔记内容
          fetchNoteDetail(noteId).catch(error => {
            console.error('加载笔记详情失败，但笔记ID已保存到localStorage:', error);
          });
        }
      }
      // 如果只有会话ID参数，没有笔记ID参数
      else if (route.query.id) {
        const sessionId = route.query.id as string;
        if (sessionId) {
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
        // 如果URL中没有任何参数，且用户已登录，自动加载最新笔记
        if (authService.isAuthenticated()) {
          const defaultNoteId = authService.getDefaultNoteId();
          if (defaultNoteId) {
            console.log(`发现默认笔记ID: ${defaultNoteId}，自动加载`);
            fetchNoteDetail(defaultNoteId);

            // 加载成功后清除默认笔记ID，这样只有首次登录会自动打开
            localStorage.removeItem('default_note_id');
          } else {
            // 如果没有默认笔记，自动加载最新笔记
            console.log('没有默认笔记，自动加载最新笔记');
            loadLatestNote(fetchNoteDetail);
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
    fetchNoteDetail: (noteId: string) => Promise<any>,
    fetchSessionDetail: (sessionId: string) => Promise<any>,
    fetchNoteBySessionId: (sessionId: string) => Promise<any>,
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
        const noteId = newQuery.note as string;
        if (noteId) {
          console.log(`从URL参数变化设置笔记ID: ${noteId}`);
          
          // 立即保存到localStorage，确保即使异步加载失败也能获取到
          localStorage.setItem('lastNoteId', noteId);
          
          // 如果同时有会话ID，也设置会话ID，但优先加载笔记内容
          if (newQuery.id) {
            const sessionId = newQuery.id as string;
            if (sessionId) {
              console.log(`URL中同时有会话ID: ${sessionId}，但优先加载笔记内容`);
            }
          }
          
          // 加载笔记内容
          fetchNoteDetail(noteId).catch(error => {
            console.error('加载笔记详情失败，但笔记ID已保存到localStorage:', error);
          });
        }
      }
      // 如果只有会话ID参数，没有笔记ID参数
      else if (newQuery.id) {
        const sessionId = newQuery.id as string;
        if (sessionId) {
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