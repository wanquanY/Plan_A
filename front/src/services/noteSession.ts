import apiClient from './api';

export interface NoteSession {
  id: number;
  title: string;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
  // 会话的详细信息
  agent_id?: number;
  message_count?: number;
  last_message?: string;
}

export interface NoteSessionsResponse {
  note_id: number;
  sessions: NoteSession[];
}

class NoteSessionService {
  // 获取笔记的所有关联会话
  async getNoteSessions(noteId: number): Promise<NoteSession[]> {
    try {
      const response = await apiClient.get(`/note/${noteId}/sessions`);
      if (response.data && response.data.code === 200) {
        const sessions = response.data.data.sessions || [];
        
        // 按最近使用时间排序：最近使用的会话在前，主要会话优先级较高但不强制在最前
        return sessions.sort((a: NoteSession, b: NoteSession) => {
          // 首先按更新时间降序排序（最近使用的在前）
          const timeCompare = new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
          
          // 如果更新时间相同，主要会话优先
          if (timeCompare === 0) {
            if (a.is_primary && !b.is_primary) return -1;
            if (!a.is_primary && b.is_primary) return 1;
          }
          
          return timeCompare;
        });
      }
      throw new Error(response.data.msg || '获取笔记会话列表失败');
    } catch (error: any) {
      console.error('获取笔记会话列表失败:', error);
      throw error;
    }
  }

  // 创建新会话并关联到笔记
  async createSessionForNote(noteId: number): Promise<any> {
    try {
      const response = await apiClient.post('/chat/sessions', {
        title: '新对话',
        note_id: noteId
      });
      if (response.data && response.data.code === 200) {
        return response.data.data;
      }
      throw new Error(response.data.msg || '创建会话失败');
    } catch (error: any) {
      console.error('创建会话失败:', error);
      throw error;
    }
  }

  // 设置主要会话
  async setPrimarySession(noteId: number, sessionId: number): Promise<boolean> {
    try {
      const response = await apiClient.put(`/note/${noteId}/sessions/${sessionId}/set-primary`);
      if (response.data && response.data.code === 200) {
        return true;
      }
      throw new Error(response.data.msg || '设置主要会话失败');
    } catch (error: any) {
      console.error('设置主要会话失败:', error);
      throw error;
    }
  }

  // 删除笔记和会话的关联
  async unlinkSession(noteId: number, sessionId: number): Promise<boolean> {
    try {
      const response = await apiClient.delete(`/note/${noteId}/sessions/${sessionId}/unlink`);
      if (response.data && response.data.code === 200) {
        return true;
      }
      throw new Error(response.data.msg || '取消关联失败');
    } catch (error: any) {
      console.error('取消关联失败:', error);
      throw error;
    }
  }

  // 生成会话的显示标题
  generateSessionDisplayTitle(session: NoteSession): string {
    // 优先使用会话标题
    if (session.title && session.title.trim()) {
      // 截取前12个字符用于标签页显示
      return session.title.length > 12 ? session.title.substring(0, 12) + '...' : session.title;
    }
    
    // 如果没有标题，使用默认名称
    return '新对话';
  }
}

export default new NoteSessionService();