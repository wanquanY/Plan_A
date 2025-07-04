<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import { UserOutlined, LockOutlined, MobileOutlined } from '@ant-design/icons-vue';
import authService from '../services/auth';

const router = useRouter();
const loading = ref(false);

const formState = reactive({
  username: '',
  phone: '',
  password: '',
  password_confirm: '',
});

// 验证规则
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度必须在2-20个字符之间', trigger: 'blur' }
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号码', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  password_confirm: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule: any, value: string) => {
        if (value !== formState.password) {
          return Promise.reject('两次输入的密码不一致');
        }
        return Promise.resolve();
      },
      trigger: 'blur'
    }
  ]
};

// 表单引用
const formRef = ref();

// 注册处理
const handleRegister = async () => {
  try {
    // 验证表单
    await formRef.value.validate();
    
    // 设置加载状态
    loading.value = true;
    
    // 调用注册API
    const response = await authService.register(formState);
    
    // 显示成功消息
    message.success('注册成功');
    
    // 获取默认笔记ID
    const defaultNoteId = response.data.default_note?.id;
    
    if (defaultNoteId) {
      // 如果有默认笔记，直接登录并跳转到该笔记页面
      try {
        await authService.login(formState.username, formState.password);
        // 跳转到默认笔记页面
        router.push(`/?note=${defaultNoteId}`);
      } catch (loginError) {
        // 如果登录失败，仍然跳转到登录页
        message.warning('注册成功，请重新登录');
        router.push('/login');
      }
    } else {
      // 如果没有默认笔记，跳转到登录页
      router.push('/login');
    }
  } catch (error: any) {
    // 显示错误消息
    if (error.response && error.response.data) {
      message.error(error.response.data.msg || '注册失败，请检查输入信息');
    } else if (error.message) {
      message.error(error.message);
    } else {
      message.error('注册失败，请检查输入信息');
    }
  } finally {
    loading.value = false;
  }
};

// 跳转到登录页面
const goToLogin = () => {
  router.push('/login');
};
</script>

<template>
  <div class="register-container">
    <div class="register-wrapper">
      <div class="logo-area">
        <div class="app-logo">
          <div class="title-container">
            <h1 class="app-title">Plan<span class="highlight">_A</span></h1>
            <p class="app-desc">AI native办公平台</p>
          </div>
        </div>
      </div>
      
      <div class="right-section">
        <a-card class="register-card">
          <div class="card-header">
            <h2 class="card-title">用户注册</h2>
            <p class="card-subtitle">创建您的Plan_A账号</p>
          </div>
          <a-form
            :model="formState"
            :rules="rules"
            ref="formRef"
            @finish="handleRegister"
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
            
            <a-form-item name="phone">
              <a-input 
                v-model:value="formState.phone" 
                placeholder="手机号"
                size="large"
              >
                <template #prefix>
                  <MobileOutlined />
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
            
            <a-form-item name="password_confirm">
              <a-input-password 
                v-model:value="formState.password_confirm" 
                placeholder="确认密码"
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
                class="register-button"
              >
                注册
              </a-button>
            </a-form-item>
            
            <div class="form-footer">
              <a-button type="link" @click="goToLogin" class="login-link">
                已有账号？去登录
              </a-button>
            </div>
          </a-form>
        </a-card>
      </div>
    </div>
    
    <div class="register-footer">
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
.register-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  width: 100vw;
  background: #f0f2f5; /* 浅灰色背景 */
  position: relative;
  overflow: hidden;
  padding: 20px;
}

/* 粒子背景容器 (如果使用，颜色也需要调整) */
.particles-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  /* 粒子颜色应与浅色背景协调 */
}

.register-wrapper {
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

.app-logo {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Logo icon 样式调整为浅色主题 */
.logo-icon {
  background: linear-gradient(135deg, #007aff, #005bb5); /* 科技蓝渐变 */
  color: white;
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 36px;
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3); /* 调整阴影颜色和透明度 */
}

.app-title {
  font-size: 48px;
  font-weight: bold;
  color: #1f2937; /* 深灰色字体 */
  margin-bottom: 8px;
  letter-spacing: 1px;
}

.app-title .highlight {
  color: #007aff; /* 科技蓝高亮 (调整为更适合浅色的蓝色) */
}

.app-desc {
  color: #4b5563; /* 中灰色字体 */
  font-size: 18px;
  margin-bottom: 0;
}

.register-card {
  width: 100%;
  max-width: 420px;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 122, 255, 0.15); /* 科技蓝阴影 (调整透明度) */
  background: #ffffff; /* 白色背景 */
  border: 1px solid #e5e7eb; /* 浅灰色边框 */
  padding: 25px;
}

.card-header {
  text-align: center;
  margin-bottom: 24px;
}

.card-title {
  font-size: 26px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1f2937; /* 深灰色字体 */
}

.card-subtitle {
  color: #6b7280; /* 中灰色字体 */
  font-size: 14px;
}

/* 输入框样式调整 - 与Login.vue保持一致 */
:deep(.ant-input-affix-wrapper) {
  background-color: #f9fafb !important; /* 非常浅的灰色背景 */
  border: 1px solid #d1d5db !important; /* 浅灰色边框 */
  border-radius: 6px !important;
}

:deep(.ant-input) {
  background-color: transparent !important;
  color: #1f2937 !important; /* 深灰色字体 */
  font-size: 16px !important;
}

:deep(.ant-input::placeholder) {
  color: #9ca3af !important; /* 较浅的灰色占位符 */
}

:deep(.ant-input-prefix .anticon) {
  color: #007aff !important; /* 科技蓝图标 */
}

.register-button {
  height: 48px;
  font-size: 18px;
  background: linear-gradient(90deg, #007aff, #005bb5); /* 科技蓝渐变 (调整颜色) */
  color: #ffffff; /* 白色文字 */
  border: none;
  border-radius: 6px;
  margin-bottom: 12px;
  letter-spacing: 0.5px;
  transition: all 0.3s ease;
}

.register-button:hover,
.register-button:focus {
  background: linear-gradient(90deg, #005bb5, #007aff);
  box-shadow: 0 0 15px rgba(0, 122, 255, 0.3); /* 悬浮辉光效果 */
  transform: translateY(-2px);
}

.form-footer {
  text-align: center;
  margin-top: 20px;
}

.login-link {
  color: #007aff; /* 科技蓝链接 */
  font-size: 14px;
  transition: color 0.3s ease;
}

.login-link:hover {
  color: #005bb5;
}

.register-footer {
  text-align: center;
  color: #6b7280; /* 中灰色字体 */
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
  .register-wrapper {
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

  .register-card {
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
  .register-card {
    padding: 20px;
    max-width: 100%;
  }
  .card-title {
    font-size: 22px;
  }
  .register-button {
    height: 44px;
    font-size: 16px;
  }
}
</style> 