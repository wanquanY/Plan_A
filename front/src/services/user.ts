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

// 用户的缓存键
const USER_CACHE_KEY = 'user_info';

// 获取当前用户信息
const getCurrentUser = async (): Promise<User | null> => {
  try {
    console.log('开始请求当前用户信息');
    const response = await apiClient.get<ApiResponse<User>>('/users/me');
    console.log('获取当前用户信息成功:', response.data.data);
    return response.data.code === 200 ? response.data.data : null;
  } catch (error) {
    console.error('获取当前用户信息失败:', error);
    return null;
  }
};

// 更新用户信息
const updateUserInfo = async (userData: UserUpdate): Promise<User | null> => {
  try {
    const response = await apiClient.put<ApiResponse<User>>('/users/me', userData);
    return response.data.code === 200 ? response.data.data : null;
  } catch (error) {
    console.error('更新用户信息失败:', error);
    return null;
  }
};

// 缓存用户信息到localStorage
const cacheUserInfo = (user: User): void => {
  try {
    localStorage.setItem(USER_CACHE_KEY, JSON.stringify(user));
    console.log('用户信息已缓存:', user.username, 'ID:', user.id);
  } catch (e) {
    console.error('缓存用户信息失败:', e);
  }
};

// 从缓存获取用户信息
const getCachedUserInfo = (): User | null => {
  try {
    const cachedUser = localStorage.getItem(USER_CACHE_KEY);
    if (cachedUser) {
      const user = JSON.parse(cachedUser) as User;
      console.log('从缓存获取到用户信息:', user.username, 'ID:', user.id);
      return user;
    }
  } catch (e) {
    console.error('获取缓存用户信息失败:', e);
  }
  console.log('缓存中没有用户信息');
  return null;
};

// 清除缓存的用户信息
const clearCachedUserInfo = (): void => {
  try {
    localStorage.removeItem(USER_CACHE_KEY);
    console.log('已清除缓存的用户信息');
  } catch (e) {
    console.error('清除缓存用户信息失败:', e);
  }
};

const userService = {
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

  getCurrentUser,
  updateUserInfo,
  cacheUserInfo,
  getCachedUserInfo,
  clearCachedUserInfo: clearCachedUserInfo
};

export default userService; 