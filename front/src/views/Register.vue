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
        <h1 class="app-title">FreeWrite</h1>
        <p class="app-desc">简单、高效的写作平台</p>
      </div>
      
      <div class="right-section">
        <a-card class="register-card">
          <div class="card-header">
            <h2 class="card-title">用户注册</h2>
            <p class="card-subtitle">创建您的FreeWrite账号</p>
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
      <p>FreeWrite &copy; 2024 - 高效写作平台</p>
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

.register-wrapper {
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
  margin-bottom: 12px;
  letter-spacing: -0.5px;
}

.app-desc {
  font-size: 18px;
  color: rgba(0, 0, 0, 0.65);
  margin-bottom: 24px;
}

.register-card {
  width: 100%;
  max-width: 400px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  background: white;
}

.card-header {
  padding: 24px 24px 0;
}

.card-title {
  font-size: 24px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.85);
  margin-bottom: 8px;
}

.card-subtitle {
  color: rgba(0, 0, 0, 0.45);
  margin-bottom: 24px;
}

.register-button {
  height: 48px;
  font-size: 16px;
  background: linear-gradient(45deg, #722ed1, #a878eb);
  border: none;
  transition: all 0.3s;
}

.register-button:hover {
  background: linear-gradient(45deg, #642ab5, #9a6ce0);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(114, 46, 209, 0.3);
}

.form-footer {
  text-align: center;
  margin-top: 16px;
}

.login-link {
  color: #722ed1;
  font-size: 14px;
}

.register-footer {
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
  background: linear-gradient(135deg, #722ed1, #a878eb);
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
  background: linear-gradient(135deg, #1890ff, #40a9ff);
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
  .register-container {
    padding: 0;
  }
  
  .register-wrapper {
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
  
  .register-footer {
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