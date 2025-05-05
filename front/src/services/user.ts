import apiClient from './api';

// 用户信息接口
export interface User {
  id: number;
  username: string;
  phone: string;
  avatar_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserUpdate {
  username?: string;
  phone?: string;
  avatar_url?: string;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface ApiResponse<T> {
  code: number;
  msg: string;
  data: T;
  errors: any;
  timestamp: string;
  request_id: string;
}

const userService = {
  // 获取当前登录用户信息
  getCurrentUser: async (): Promise<User | null> => {
    try {
      const response = await apiClient.get<ApiResponse<User>>('/users/me');
      return response.data.code === 200 ? response.data.data : null;
    } catch (error) {
      console.error('获取用户信息失败:', error);
      return null;
    }
  },

  // 更新用户信息
  updateUserInfo: async (userData: UserUpdate): Promise<User | null> => {
    try {
      const response = await apiClient.put<ApiResponse<User>>('/users/me', userData);
      return response.data.code === 200 ? response.data.data : null;
    } catch (error) {
      console.error('更新用户信息失败:', error);
      return null;
    }
  },

  // 修改用户密码
  changePassword: async (passwordData: PasswordChange): Promise<boolean> => {
    try {
      const response = await apiClient.put<ApiResponse<null>>('/users/me/password', passwordData);
      return response.data.code === 200;
    } catch (error) {
      console.error('修改密码失败:', error);
      return false;
    }
  },

  // 缓存用户信息
  cacheUserInfo: (user: User) => {
    localStorage.setItem('user_info', JSON.stringify(user));
  },

  // 从缓存获取用户信息
  getCachedUserInfo: (): User | null => {
    const userInfo = localStorage.getItem('user_info');
    return userInfo ? JSON.parse(userInfo) : null;
  },

  // 清除用户信息缓存
  clearUserCache: () => {
    localStorage.removeItem('user_info');
  }
};

export default userService; 