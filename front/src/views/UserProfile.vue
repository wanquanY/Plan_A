<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { message, Form, Input, Button, Upload, Avatar, Divider, Row, Col, Card } from 'ant-design-vue';
import {
  UserOutlined,
  MobileOutlined,
  KeyOutlined,
  UploadOutlined,
  LoadingOutlined,
  SaveOutlined,
  CheckCircleOutlined
} from '@ant-design/icons-vue';
import type { UploadChangeParam } from 'ant-design-vue';
import userService from '@/services/user';
import type { User, UserUpdate, PasswordChange } from '@/services/user';

// 用户信息
const userInfo = ref<User>({
  id: 0,
  username: '',
  phone: '',
  avatar_url: '',
  is_active: true,
  created_at: '',
  updated_at: ''
});

// 加载状态
const loading = ref(false);
const saveLoading = ref(false);
const uploadLoading = ref(false);
const passwordLoading = ref(false);

// 密码修改表单
const passwordForm = ref<PasswordChange>({
  current_password: '',
  new_password: '',
  confirm_password: ''
});

// 表单引用
const formRef = ref();
const passwordFormRef = ref();

// 从服务器获取用户信息
const fetchUserInfo = async () => {
  loading.value = true;
  try {
    const user = await userService.getCurrentUser();
    if (user) {
      userInfo.value = user;
      userService.cacheUserInfo(user);
    } else {
      message.error('获取用户信息失败');
    }
  } catch (error) {
    console.error('获取用户信息出错:', error);
    message.error('获取用户信息失败');
  } finally {
    loading.value = false;
  }
};

// 保存用户信息
const saveUserInfo = async () => {
  try {
    formRef.value.validate().then(async () => {
      saveLoading.value = true;
      
      try {
        const updateData: UserUpdate = {
          username: userInfo.value.username,
          phone: userInfo.value.phone,
          avatar_url: userInfo.value.avatar_url
        };
        
        const updatedUser = await userService.updateUserInfo(updateData);
        if (updatedUser) {
          message.success('用户信息更新成功');
          userInfo.value = updatedUser;
          userService.cacheUserInfo(updatedUser);
        } else {
          message.error('更新用户信息失败');
        }
      } catch (error) {
        console.error('更新用户信息出错:', error);
        message.error('更新用户信息失败');
      } finally {
        saveLoading.value = false;
      }
    });
  } catch (error) {
    console.error('表单验证失败:', error);
  }
};

// 修改密码
const changePassword = async () => {
  try {
    passwordFormRef.value.validate().then(async () => {
      if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
        message.error('新密码和确认密码不一致');
        return;
      }
      
      passwordLoading.value = true;
      
      try {
        const success = await userService.changePassword(passwordForm.value);
        if (success) {
          message.success('密码修改成功');
          // 清空表单
          passwordForm.value.current_password = '';
          passwordForm.value.new_password = '';
          passwordForm.value.confirm_password = '';
          passwordFormRef.value.resetFields();
        } else {
          message.error('密码修改失败');
        }
      } catch (error) {
        console.error('修改密码出错:', error);
        message.error('密码修改失败');
      } finally {
        passwordLoading.value = false;
      }
    });
  } catch (error) {
    console.error('表单验证失败:', error);
  }
};

// 处理文件上传前的校验
const beforeUpload = (file) => {
  const isImage = file.type.startsWith('image/');
  if (!isImage) {
    message.error('只能上传图片文件!');
  }
  const isLt2M = file.size / 1024 / 1024 < 2;
  if (!isLt2M) {
    message.error('图片大小不能超过2MB!');
  }
  return isImage && isLt2M;
};

// 处理文件上传变化
const handleChange = (info: UploadChangeParam) => {
  if (info.file.status === 'uploading') {
    uploadLoading.value = true;
    return;
  }
  
  if (info.file.status === 'done') {
    uploadLoading.value = false;
    if (info.file.response && info.file.response.success) {
      const fileInfo = info.file.response.file_info;
      userInfo.value.avatar_url = fileInfo.url;
      message.success('头像上传成功!');
    } else {
      message.error('上传失败: ' + (info.file.response?.message || '未知错误'));
    }
  } else if (info.file.status === 'error') {
    uploadLoading.value = false;
    message.error('上传失败: ' + info.file.response?.message || '未知错误');
  }
};

// 上传组件属性
const uploadProps = {
  name: 'file',
  multiple: false,
  action: 'http://14.103.155.104:18000/api/upload',
  data: { folder: 'avatar' },
  headers: {},
  beforeUpload: beforeUpload,
  onChange: handleChange,
  showUploadList: false
};

// 格式化日期
const formatDate = (dateStr: string): string => {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return dateStr;
  }
};

// 初始化
onMounted(() => {
  fetchUserInfo();
});
</script>

<template>
  <div class="user-profile">
    <div class="page-header">
      <h1>个人资料</h1>
      <p class="subtitle">管理您的账户信息和密码</p>
    </div>
    
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <p>加载中，请稍候...</p>
    </div>
    
    <div v-else class="profile-content">
      <Row :gutter="32">
        <!-- 左侧个人信息 -->
        <Col :xs="24" :lg="16" :xl="14">
          <Card class="profile-card info-card" :bordered="false">
            <template #title>
              <div class="card-title">
                <UserOutlined />
                <span>基本信息</span>
              </div>
            </template>
            
            <div class="avatar-section">
              <div class="avatar-container">
                <Avatar 
                  :size="120" 
                  :src="userInfo.avatar_url" 
                  v-if="userInfo.avatar_url"
                  class="user-avatar"
                />
                <Avatar 
                  :size="120" 
                  :icon="UserOutlined" 
                  v-else 
                  class="user-avatar"
                />
                
                <Upload
                  name="file"
                  :multiple="false"
                  :action="'http://14.103.155.104:18000/api/upload'"
                  :data="{ folder: 'avatar' }"
                  :showUploadList="false"
                  :beforeUpload="beforeUpload"
                  @change="handleChange"
                >
                  <div class="upload-overlay">
                    <UploadOutlined />
                    <span>更换头像</span>
                  </div>
                </Upload>
              </div>
              
              <div class="user-meta">
                <h2>{{ userInfo.username }}</h2>
                <p>账号创建于: {{ formatDate(userInfo.created_at) }}</p>
              </div>
            </div>
            
            <Divider />
            
            <Form
              ref="formRef"
              :model="userInfo"
              layout="vertical"
              class="profile-form"
            >
              <Row :gutter="24">
                <Col :span="24">
                  <Form.Item
                    label="用户名"
                    name="username"
                    :rules="[{ required: true, message: '请输入用户名' }]"
                  >
                    <Input 
                      v-model:value="userInfo.username" 
                      placeholder="请输入用户名" 
                      size="large"
                    >
                      <template #prefix>
                        <UserOutlined />
                      </template>
                    </Input>
                  </Form.Item>
                </Col>
                
                <Col :span="24">
                  <Form.Item
                    label="手机号"
                    name="phone"
                    :rules="[
                      { required: true, message: '请输入手机号' },
                      { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号码' }
                    ]"
                  >
                    <Input 
                      v-model:value="userInfo.phone" 
                      placeholder="请输入手机号" 
                      size="large"
                    >
                      <template #prefix>
                        <MobileOutlined />
                      </template>
                    </Input>
                  </Form.Item>
                </Col>
              </Row>
              
              <Form.Item class="form-actions">
                <Button 
                  type="primary" 
                  @click="saveUserInfo" 
                  :loading="saveLoading"
                  size="large"
                  class="save-button"
                >
                  <template #icon>
                    <SaveOutlined />
                  </template>
                  保存修改
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>
        
        <!-- 右侧密码修改 -->
        <Col :xs="24" :lg="8" :xl="10">
          <Card class="profile-card password-card" :bordered="false">
            <template #title>
              <div class="card-title">
                <KeyOutlined />
                <span>修改密码</span>
              </div>
            </template>
            
            <Form
              ref="passwordFormRef"
              :model="passwordForm"
              layout="vertical"
              class="password-form"
            >
              <Form.Item
                label="当前密码"
                name="current_password"
                :rules="[{ required: true, message: '请输入当前密码' }]"
              >
                <Input.Password 
                  v-model:value="passwordForm.current_password" 
                  placeholder="请输入当前密码" 
                  size="large"
                >
                  <template #prefix>
                    <KeyOutlined />
                  </template>
                </Input.Password>
              </Form.Item>
              
              <Form.Item
                label="新密码"
                name="new_password"
                :rules="[
                  { required: true, message: '请输入新密码' },
                  { min: 6, message: '密码长度不能少于6个字符' }
                ]"
              >
                <Input.Password 
                  v-model:value="passwordForm.new_password" 
                  placeholder="请输入新密码" 
                  size="large"
                >
                  <template #prefix>
                    <KeyOutlined />
                  </template>
                </Input.Password>
              </Form.Item>
              
              <Form.Item
                label="确认新密码"
                name="confirm_password"
                :rules="[
                  { required: true, message: '请确认新密码' },
                  { validator: (_, value) => 
                    value === passwordForm.new_password ? Promise.resolve() : Promise.reject('两次输入的密码不一致')
                  }
                ]"
              >
                <Input.Password 
                  v-model:value="passwordForm.confirm_password" 
                  placeholder="请确认新密码" 
                  size="large"
                >
                  <template #prefix>
                    <KeyOutlined />
                  </template>
                </Input.Password>
              </Form.Item>
              
              <Form.Item class="form-actions">
                <Button 
                  type="primary" 
                  @click="changePassword" 
                  :loading="passwordLoading"
                  size="large"
                  class="change-password-button"
                >
                  <template #icon>
                    <CheckCircleOutlined />
                  </template>
                  修改密码
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  </div>
</template>

<style scoped>
.user-profile {
  padding: 32px 40px;
  max-width: 1600px;
  margin: 0 auto;
  height: 100%;
  overflow: auto;
}

.page-header {
  margin-bottom: 40px;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 20px;
}

.page-header h1 {
  font-size: 32px;
  font-weight: 600;
  margin: 0;
  color: #262626;
}

.subtitle {
  margin-top: 12px;
  color: #8c8c8c;
  font-size: 18px;
}

.profile-content {
  padding-bottom: 60px;
}

.profile-card {
  border-radius: 16px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  height: 100%;
  transition: all 0.3s ease;
  padding: 32px;
}

.profile-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.info-card {
  background: linear-gradient(to bottom, #ffffff, #f9fafb);
}

.password-card {
  background: linear-gradient(to bottom, #ffffff, #f9f9ff);
}

.card-title {
  display: flex;
  align-items: center;
  font-size: 20px;
  font-weight: 600;
  color: #1890ff;
}

.card-title :deep(svg) {
  margin-right: 10px;
  font-size: 22px;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 32px;
}

.avatar-container {
  position: relative;
  margin-bottom: 20px;
}

.user-avatar {
  border: 4px solid #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.upload-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  color: white;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border-radius: 50%;
  opacity: 0;
  transition: opacity 0.3s;
  cursor: pointer;
}

.upload-overlay:hover {
  opacity: 1;
}

.upload-overlay :deep(svg) {
  font-size: 24px;
  margin-bottom: 4px;
}

.user-meta {
  text-align: center;
}

.user-meta h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 600;
  color: #262626;
}

.user-meta p {
  margin: 6px 0 0;
  color: #8c8c8c;
  font-size: 15px;
}

.profile-form, .password-form {
  margin-top: 24px;
}

.form-actions {
  margin-top: 32px;
  display: flex;
  justify-content: flex-end;
}

.save-button, .change-password-button {
  min-width: 140px;
  height: 44px;
  border-radius: 8px;
  font-size: 16px;
}

.save-button {
  background: linear-gradient(135deg, #1890ff, #096dd9);
}

.change-password-button {
  background: linear-gradient(135deg, #52c41a, #389e0d);
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
}

.loading-spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border-left-color: #1890ff;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

@media (max-width: 1400px) {
  .user-profile {
    max-width: 1200px;
    padding: 24px 32px;
  }
  
  .profile-card {
    padding: 28px; /* 中等屏幕稍微减少内边距 */
  }
}

@media (max-width: 1200px) {
  .user-profile {
    max-width: 100%;
    padding: 24px;
  }
  
  .page-header h1 {
    font-size: 28px;
  }
  
  .subtitle {
    font-size: 16px;
  }
  
  .profile-card {
    padding: 24px;
  }
}

@media (max-width: 992px) {
  .user-profile {
    padding: 20px;
  }
  
  .page-header {
    margin-bottom: 32px;
  }
  
  .profile-content {
    padding-bottom: 40px;
  }
  
  .profile-card + .profile-card {
    margin-top: 24px;
  }
  
  .avatar-section {
    margin-bottom: 24px;
  }
  
  .user-avatar {
    width: 100px !important;
    height: 100px !important;
  }
}

@media (max-width: 767px) {
  .user-profile {
    padding: 16px;
  }
  
  .page-header {
    margin-bottom: 24px;
  }
  
  .page-header h1 {
    font-size: 24px;
  }
  
  .subtitle {
    font-size: 14px;
  }
  
  .profile-card {
    padding: 20px;
    border-radius: 12px;
  }
  
  .card-title {
    font-size: 18px;
  }
  
  .user-meta h2 {
    font-size: 22px;
  }
  
  .user-avatar {
    width: 80px !important;
    height: 80px !important;
  }
  
  .save-button, .change-password-button {
    min-width: 120px;
    height: 40px;
    font-size: 14px;
  }
  
  .profile-card + .profile-card {
    margin-top: 24px;
  }
}

@media (max-width: 480px) {
  .user-profile {
    padding: 12px;
  }
  
  .profile-card {
    padding: 16px;
  }
  
  .page-header h1 {
    font-size: 20px;
  }
  
  .user-meta h2 {
    font-size: 20px;
  }
  
  .form-actions {
    margin-top: 24px;
  }
}

/* 表单标签样式优化 */
.profile-form :deep(.ant-form-item-label > label),
.password-form :deep(.ant-form-item-label > label) {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
}

/* 表单项间距优化 */
.profile-form :deep(.ant-form-item),
.password-form :deep(.ant-form-item) {
  margin-bottom: 24px;
}

/* 输入框样式优化 */
.profile-form :deep(.ant-input),
.profile-form :deep(.ant-input-password),
.password-form :deep(.ant-input),
.password-form :deep(.ant-input-password) {
  border-radius: 8px;
  border: 2px solid #f0f0f0;
  transition: all 0.3s ease;
}

.profile-form :deep(.ant-input:focus),
.profile-form :deep(.ant-input-password:focus),
.password-form :deep(.ant-input:focus),
.password-form :deep(.ant-input-password:focus) {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.1);
}

/* 分割线样式优化 */
.profile-card :deep(.ant-divider) {
  margin: 32px 0;
  border-color: #f0f0f0;
}
</style> 