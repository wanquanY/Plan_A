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
        <h1 class="app-title">Plan<span class="highlight">_A</span></h1>
        <p class="app-desc">简单、高效的写作平台</p>
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
  justify-content: space-between;
  min-height: 100vh;
  height: 100vh;
  width: 100vw;
  max-width: 100%;
  margin: 0;
  padding: 0;
  background-color: #f8fafc;
  position: relative;
  overflow: hidden;
}

.login-wrapper {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  flex: 1;
  padding: 0 16px;
}

.logo-area {
  text-align: center;
  margin-bottom: 40px;
  position: relative;
  z-index: 5;
}

.app-title {
  font-size: 42px;
  font-weight: bold;
  background: linear-gradient(45deg, #1890ff, #722ed1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 8px;
}

.app-desc {
  color: #666;
  font-size: 16px;
  margin-bottom: 0;
}

.login-card {
  width: 100%;
  max-width: 400px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  background: white;
}

.card-header {
  text-align: center;
  margin-bottom: 24px;
}

.card-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.card-subtitle {
  color: #666;
  font-size: 14px;
}

.login-button {
  height: 44px;
  font-size: 16px;
  background: linear-gradient(45deg, #1890ff, #40a9ff);
  border: none;
  margin-bottom: 12px;
  letter-spacing: -0.5px;
}

.login-button:hover {
  background: linear-gradient(45deg, #0084ff, #2994ff);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
}

.form-footer {
  text-align: center;
  margin-top: 16px;
}

.register-link {
  color: #1890ff;
  font-size: 14px;
}

.login-footer {
  text-align: center;
  color: rgba(0, 0, 0, 0.45);
  font-size: 14px;
  padding: 16px 0;
  width: 100%;
  z-index: 10;
}

/* 装饰性元素 */
.decoration-circle {
  position: fixed;
  border-radius: 50%;
  opacity: 0.4;
  z-index: 1;
}

.circle-1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #1890ff, #40a9ff);
  top: -200px;
  right: -200px;
}

.circle-2 {
  width: 800px;
  height: 800px;
  background: linear-gradient(135deg, #52c41a, #85e45b);
  bottom: -300px;
  left: -300px;
}

.circle-3 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #722ed1, #a878eb);
  top: 40%;
  right: -100px;
}

.decoration-square {
  position: fixed;
  opacity: 0.2;
  transform: rotate(45deg);
  z-index: 1;
}

.square-1 {
  width: 200px;
  height: 200px;
  background: #faad14;
  bottom: 5%;
  right: 10%;
}

.square-2 {
  width: 150px;
  height: 150px;
  background: #f5222d;
  top: 20%;
  left: 5%;
}

@media (min-width: 992px) {
  .login-container {
    padding: 0;
  }
  
  .login-wrapper {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr;
    gap: 40px;
    padding: 0 48px;
    align-items: center;
    height: 100%;
  }
  
  .logo-area {
    grid-column: 1;
    grid-row: 1;
    text-align: left;
    margin-bottom: 0;
    max-width: 500px;
  }

  .right-section {
    grid-column: 2;
    grid-row: 1;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    width: 100%;
  }
  
  .login-footer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
  }
  
  .app-title {
    font-size: 56px;
  }
  
  .app-desc {
    font-size: 22px;
  }
}
</style>