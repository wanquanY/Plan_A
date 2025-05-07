import apiClient from './api';
import axios from 'axios';

interface RegisterData {
  username: string;
  phone: string;
  password: string;
  password_confirm: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
}

interface DefaultNote {
  id: number;
  title: string;
}

interface RegisterResponse {
  user: {
    id: number;
    username: string;
    phone: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
  };
  default_note?: DefaultNote;
}

interface ApiResponse<T> {
  code: number;
  msg: string;
  data: T;
  errors: any;
  timestamp: string;
  request_id: string;
}

const authService = {
  // 用户注册
  register: async (data: RegisterData) => {
    const response = await apiClient.post<ApiResponse<RegisterResponse>>('/auth/register', data);
    // 如果有默认笔记，存储默认笔记ID到本地存储，便于登录后自动打开
    if (response.data.data.default_note) {
      localStorage.setItem('default_note_id', response.data.data.default_note.id.toString());
    }
    return response.data;
  },

  // 用户登录
  login: async (username: string, password: string) => {
    // 登录接口需要使用表单数据格式
    const formData = new URLSearchParams();
    formData.append('grant_type', 'password');
    formData.append('username', username);
    formData.append('password', password);
    formData.append('scope', '');
    formData.append('client_id', 'string');
    formData.append('client_secret', 'string');

    const response = await apiClient.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    // 存储token到localStorage
    localStorage.setItem('access_token', response.data.access_token);
    return response.data;
  },

  // 退出登录
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('default_note_id'); // 同时清除默认笔记ID
  },

  // 检查是否已登录
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  },
  
  // 获取默认笔记ID
  getDefaultNoteId: (): number | null => {
    const noteId = localStorage.getItem('default_note_id');
    return noteId ? parseInt(noteId) : null;
  }
};

export default authService; 