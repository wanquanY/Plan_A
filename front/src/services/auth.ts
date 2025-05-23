import apiClient from './api';
import axios from 'axios';
import type { User } from './user';

// API响应接口
export interface ApiResponse<T> {
  code: number;
  msg: string;
  data: T;
  errors: any;
  timestamp: string;
  request_id: string;
}

interface RegisterData {
  username: string;
  password: string;
  confirm_password: string;
  phone: string;
}

interface RegisterResponse {
  user: User;
  default_note?: {
    id: number;
    title: string;
  };
}

interface LoginResponse {
  access_token: string;
  token_type: string;
}

interface DefaultNote {
  id: number;
  title: string;
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

    const response = await apiClient.post<{
      access_token: string,
      token_type: string
    }>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    // 后端直接返回token信息，不是包装在ApiResponse中
    if (response.data && response.data.access_token) {
      const { access_token, token_type } = response.data;
      
      // 存储token到localStorage
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('token_type', token_type || 'bearer');
      
      // 存储用户信息到localStorage（从token中解析或从其他接口获取）
      // 暂时存储基本信息，可以后续通过其他接口获取完整用户信息
      const userInfo = {
        username: username,
        // 可以从JWT token中解析更多信息
      };
      localStorage.setItem('user_info', JSON.stringify(userInfo));
      
      return response.data;
    } else {
      throw new Error('登录响应格式错误');
    }
  },

  // 退出登录
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('default_note_id'); // 同时清除默认笔记ID
    localStorage.removeItem('user_info'); // 清除用户信息
  },

  // 检查是否已登录
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  },
  
  // 获取默认笔记ID
  getDefaultNoteId: (): number | null => {
    const noteId = localStorage.getItem('default_note_id');
    return noteId ? parseInt(noteId) : null;
  },
  
  // 获取缓存的用户信息
  getCachedUser: (): User | null => {
    try {
      const userJson = localStorage.getItem('user_info');
      if (userJson) {
        return JSON.parse(userJson) as User;
      }
    } catch (error) {
      console.error('解析缓存用户信息失败:', error);
    }
    return null;
  },
  
  // 清除缓存的用户信息
  clearCachedUser: () => {
    localStorage.removeItem('user_info');
  }
};

export default authService; 