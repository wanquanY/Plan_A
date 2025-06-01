import api from './api';

export interface Note {
  id: number;
  title: string;
  content: string;
  session_id: number | null;
  is_public: boolean;
  last_edited_position?: number;
  created_at: string;
  updated_at: string;
}

export interface NoteCreate {
  title?: string;
  content?: string;
  is_public?: boolean;
}

export interface NoteUpdate {
  title?: string;
  content?: string;
  is_public?: boolean;
  last_edited_position?: number;
}

class NoteService {
  /**
   * 创建新笔记
   */
  async createNote(noteData: NoteCreate): Promise<{ note_id: number; title: string }> {
    try {
      const response = await api.post('/note', noteData);
      return response.data.data;
    } catch (error) {
      console.error('创建笔记失败:', error);
      throw error;
    }
  }

  /**
   * 获取笔记列表
   */
  async getNotes(page = 1, pageSize = 20): Promise<{ notes: Note[]; total: number; pages: number }> {
    try {
      const skip = (page - 1) * pageSize;
      const response = await api.get('/note', {
        params: {
          skip,
          limit: pageSize
        }
      });
      
      const data = response.data.data;
      return {
        notes: data.notes,
        total: data.total,
        pages: Math.ceil(data.total / pageSize)
      };
    } catch (error) {
      console.error('获取笔记列表失败:', error);
      throw error;
    }
  }

  /**
   * 获取笔记详情
   */
  async getNoteDetail(noteId: number): Promise<Note> {
    try {
      console.log(`NoteService.getNoteDetail 正在请求笔记详情，ID: ${noteId}`);
      const response = await api.get(`/note/${noteId}`);
      console.log(`NoteService.getNoteDetail 请求成功, 返回数据:`, response.data);
      
      // 检查返回的数据格式是否符合预期
      if (!response.data || !response.data.data) {
        console.error('getNoteDetail: API返回数据格式异常', response.data);
        // 返回一个包含默认值的Note对象，避免上层调用崩溃
        return {
          id: noteId,
          title: '无法加载笔记',
          content: '<p>笔记加载失败，请刷新页面重试</p>',
          session_id: null,
          is_public: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
      }
      
      return response.data.data;
    } catch (error) {
      console.error('获取笔记详情失败:', error);
      // 抛出一个更明确的错误，同时提供默认的Note对象
      const err = new Error('获取笔记详情失败') as any;
      err.noteData = {
        id: noteId,
        title: '无法加载笔记',
        content: '<p>笔记加载失败，请刷新页面重试</p>',
        session_id: null,
        is_public: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      throw err;
    }
  }

  /**
   * 更新笔记内容
   */
  async updateNote(noteId: number, noteData: NoteUpdate): Promise<{ id: number; title: string; updated_at: string }> {
    try {
      const response = await api.put(`/note/${noteId}`, noteData);
      return response.data.data;
    } catch (error) {
      console.error('更新笔记失败:', error);
      throw error;
    }
  }

  /**
   * 删除笔记
   */
  async deleteNote(noteId: number): Promise<boolean> {
    try {
      await api.delete(`/note/${noteId}`);
      return true;
    } catch (error) {
      console.error('删除笔记失败:', error);
      return false;
    }
  }

  /**
   * 自动保存笔记
   * 使用节流或防抖动技术优化，避免频繁请求
   */
  async autoSaveNote(noteId: number, content: string, title?: string): Promise<boolean> {
    try {
      const updateData: NoteUpdate = { content };
      if (title) {
        updateData.title = title;
      }
      
      await this.updateNote(noteId, updateData);
      return true;
    } catch (error) {
      console.error('自动保存笔记失败:', error);
      return false;
    }
  }

  /**
   * Agent编辑笔记
   * 专门用于处理agent的笔记编辑请求
   */
  async editNoteByAgent(noteId: number, editData: any): Promise<any> {
    try {
      const response = await api.post(`/note/${noteId}/edit`, editData);
      return response.data;
    } catch (error) {
      console.error('Agent编辑笔记失败:', error);
      throw error;
    }
  }

  /**
   * 应用预览编辑到笔记
   * 用户确认后真正保存编辑内容
   */
  async applyEditPreview(noteId: number, editData: any): Promise<any> {
    try {
      const response = await api.post(`/note/${noteId}/apply-edit`, editData);
      return response.data;
    } catch (error) {
      console.error('应用预览编辑失败:', error);
      throw error;
    }
  }

  /**
   * 从会话ID获取关联的笔记
   */
  async getNoteBySessionId(sessionId: number): Promise<Note | null> {
    try {
      const response = await api.get('/note', {
        params: {
          session_id: sessionId
        }
      });
      
      const notes = response.data.data.notes;
      if (notes && notes.length > 0) {
        return notes[0];
      }
      return null;
    } catch (error) {
      console.error('通过会话ID获取笔记失败:', error);
      return null;
    }
  }
}

export default new NoteService(); 