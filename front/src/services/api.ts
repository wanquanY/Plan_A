import axios from 'axios';
import type { AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

// 获取API基础URL
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:1314/api/v1';

// 输出当前使用的API基础URL
console.log(`API服务配置: 使用基础URL ${apiBaseUrl}`);

// 创建axios实例
const apiClient = axios.create({
  baseURL: apiBaseUrl, // 使用环境变量配置API基础URL
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 从localStorage获取token
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // 简单日志
    console.log(`发送请求: ${config.method?.toUpperCase()} ${config.url}`);
    
    return config;
  },
  (error: any) => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log(`请求成功: ${response.config.method?.toUpperCase()} ${response.config.url}`);
    return response;
  },
  (error: any) => {
    console.error('响应错误:', error.message);
    
    // 处理401错误（未授权）
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token');
      // 可以在这里重定向到登录页
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

export default apiClient; 