<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue';
import authService from '../services/auth';

const router = useRouter();
const loading = ref(false);

const formState = reactive({
  username: '',
  password: '',
});

// 验证规则
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
};

// 表单引用
const formRef = ref();

// 登录处理
const handleLogin = async () => {
  try {
    // 验证表单
    await formRef.value.validate();
    
    // 设置加载状态
    loading.value = true;
    
    // 调用登录API
    const loginResult = await authService.login(formState.username, formState.password);
    
    // 显示成功消息
    message.success('登录成功');
    
    // 跳转到首页，路由守卫会自动处理跳转到最新笔记
    router.push('/');
  } catch (error: any) {
    // 显示错误消息
    if (error.response && error.response.data) {
      message.error(error.response.data.msg || '登录失败，请检查用户名和密码');
    } else if (error.message) {
      message.error(error.message);
    } else {
      message.error('登录失败，请检查用户名和密码');
    }
  } finally {
    loading.value = false;
  }
};

// 跳转到注册页面
const goToRegister = () => {
  router.push('/register');
};
</script>

<template>
  <div class="login-container">
    <div class="login-wrapper">
      <div class="logo-area">
        <div class="app-logo">
          <div class="title-container">
            <h1 class="app-title">Plan<span class="highlight">_A</span></h1>
            <p class="app-desc">简单、高效的写作平台</p>
          </div>
        </div>
      </div>
      
      <div class="right-section">
        <a-card class="login-card" :bordered="false">
          <div class="card-header">
            <h2 class="card-title">用户登录</h2>
            <p class="card-subtitle">欢迎回来，请登录您的账号</p>
          </div>
          
          <a-form
            :model="formState"
            :rules="rules"
            ref="formRef"
            @finish="handleLogin"
          >
            <a-form-item name="username">
              <a-input 
                v-model:value="formState.username" 
                placeholder="用户名"
                size="large"
              >
                <template #prefix>
                  <UserOutlined />
                </template>
              </a-input>
            </a-form-item>
            
            <a-form-item name="password">
              <a-input-password 
                v-model:value="formState.password" 
                placeholder="密码"
                size="large"
              >
                <template #prefix>
                  <LockOutlined />
                </template>
              </a-input-password>
            </a-form-item>
            
            <a-form-item>
              <a-button 
                type="primary" 
                html-type="submit" 
                size="large"
                block
                :loading="loading"
                class="login-button"
              >
                登录
              </a-button>
            </a-form-item>
            
            <div class="form-footer">
              <a-button type="link" @click="goToRegister" class="register-link">
                还没有账号？去注册
              </a-button>
            </div>
          </a-form>
        </a-card>
      </div>
    </div>
    
    <div class="login-footer">
      <p>Plan_A &copy; 2025 - 高效写作平台</p>
    </div>
    
    <!-- 装饰性元素 -->
    <div class="decoration-circle circle-1"></div>
    <div class="decoration-circle circle-2"></div>
    <div class="decoration-circle circle-3"></div>
    <div class="decoration-square square-1"></div>
    <div class="decoration-square square-2"></div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  width: 100vw;
  background: #f0f2f5;
  position: relative;
  overflow: hidden;
  padding: 20px;
}


.particles-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
}

.login-wrapper {
  width: 100%;
  max-width: 960px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  position: relative;
}

.logo-area {
  text-align: center;
  margin-bottom: 30px;
}

.app-title {
  font-size: 48px;
  font-weight: bold;
  color: #1f2937;
  margin-bottom: 8px;
  letter-spacing: 1px;
}

.app-title .highlight {
  color: #007aff;
}

.app-desc {
  color: #4b5563;
  font-size: 18px;
  margin-bottom: 0;
}

.login-card {
  width: 100%;
  max-width: 400px;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 122, 255, 0.15);
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

.card-header {
  text-align: center;
  margin-bottom: 24px;
}

.card-title {
  font-size: 26px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1f2937;
}

.card-subtitle {
  color: #6b7280;
  font-size: 14px;
}

:deep(.ant-input-affix-wrapper) {
  background-color: #f9fafb !important;
  border: 1px solid #d1d5db !important;
  border-radius: 6px !important;
}

:deep(.ant-input) {
  background-color: transparent !important;
  color: #1f2937 !important;
  font-size: 16px !important;
}

:deep(.ant-input::placeholder) {
  color: #9ca3af !important;
}

:deep(.ant-input-prefix .anticon) {
  color: #007aff !important;
}

.login-button {
  height: 48px;
  font-size: 18px;
  background: linear-gradient(90deg, #007aff, #005bb5);
  color: #ffffff;
  border: none;
  border-radius: 6px;
  margin-bottom: 12px;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
}

.login-button:hover,
.login-button:focus {
  background: linear-gradient(90deg, #005bb5, #007aff);
  box-shadow: 0 0 15px rgba(0, 122, 255, 0.3);
  transform: translateY(-2px);
}

.form-footer {
  text-align: center;
  margin-top: 20px;
}

.register-link {
  color: #007aff;
  font-size: 14px;
  transition: color 0.3s ease;
}

.register-link:hover {
  color: #005bb5;
}

.login-footer {
  text-align: center;
  color: #6b7280;
  font-size: 14px;
  padding: 20px 0;
  width: 100%;
  z-index: 10;
  position: absolute;
  bottom: 0;
  left: 0;
}

.decoration-circle,
.decoration-square {
  display: none;
}

@media (min-width: 768px) {
  .login-wrapper {
    flex-direction: row;
    justify-content: space-around;
    align-items: center;
    gap: 40px;
  }

  .logo-area {
    text-align: left;
    margin-bottom: 0;
    max-width: 450px;
  }
  
  .app-title {
    font-size: 54px;
  }

  .app-desc {
    font-size: 20px;
  }

  .login-card {
    margin-left: auto;
  }
}

@media (max-width: 767px) {
  .logo-area {
    margin-bottom: 40px;
  }
  .app-title {
    font-size: 36px;
  }
  .app-desc {
    font-size: 16px;
  }
  .login-card {
    padding: 20px;
  }
  .card-title {
    font-size: 22px;
  }
  .login-button {
    height: 44px;
    font-size: 16px;
  }
}
</style>