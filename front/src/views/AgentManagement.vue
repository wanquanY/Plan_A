<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { message, Modal, Tabs } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import CreateAgentForm from '@/components/CreateAgentForm.vue';
import MainLayout from '@/components/MainLayout.vue';
import agentService from '@/services/agent';
import userService from '@/services/user';
import type { Agent } from '@/services/agent';
import type { User } from '@/services/user';

// 状态
const username = ref('用户');
const userId = ref<number | null>(null);
const allAgents = ref<Agent[]>([]);
const loading = ref(false);
const createModalVisible = ref(false);
const activeTab = ref('myAgents');

// 获取用户信息
const fetchUserInfo = async () => {
  const cachedUser = userService.getCachedUserInfo();
  
  if (cachedUser) {
    username.value = cachedUser.username;
    userId.value = cachedUser.id;
  } else {
    try {
      const user = await userService.getCurrentUser();
      if (user) {
        username.value = user.username;
        userId.value = user.id;
        userService.cacheUserInfo(user);
      }
    } catch (error) {
      console.error('获取用户信息失败:', error);
    }
  }
};

// 过滤我的Agent和公开Agent
const myAgents = computed(() => {
  return allAgents.value.filter(agent => agent.user_id === userId.value);
});

const publicAgents = computed(() => {
  // 显示所有公开的Agent，无论是谁创建的
  return allAgents.value.filter(agent => agent.is_public);
});

// 获取 Agent 列表
const fetchAgents = async () => {
  loading.value = true;
  try {
    const agentsData = await agentService.getAllAgents();
    allAgents.value = agentsData;
  } catch (error) {
    console.error('获取Agent列表失败:', error);
    message.error('获取Agent列表失败');
  } finally {
    loading.value = false;
  }
};

// 打开创建 Agent 表单
const showCreateAgentModal = () => {
  createModalVisible.value = true;
};

// 创建 Agent 成功后的回调
const handleAgentCreated = () => {
  createModalVisible.value = false;
  fetchAgents();
  message.success('Agent创建成功');
};

// 格式化日期时间
const formatDateTime = (dateString: string) => {
  const date = new Date(dateString);
  return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
};

// 处理标签页切换
const handleTabChange = (key) => {
  activeTab.value = key;
};

// 页面加载时获取用户信息和Agent列表
onMounted(async () => {
  await fetchUserInfo();
  await fetchAgents();
  // 默认显示公开Agent
  activeTab.value = 'publicAgents';
});
</script>

<template>
  <MainLayout :username="username" editorTitle="Agent 管理">
    <div class="agent-management">
      <div class="page-header">
        <h1>Agent 管理</h1>
        <button class="create-agent-btn" @click="showCreateAgentModal">
          <PlusOutlined />
          <span>创建新 Agent</span>
        </button>
      </div>

      <div class="agent-tabs-container" v-if="!loading">
        <Tabs v-model:activeKey="activeTab" @change="handleTabChange">
          <Tabs.TabPane key="publicAgents" tab="公开 Agent">
            <div v-if="publicAgents.length === 0" class="empty-state">
              暂无公开的 Agent
            </div>
            
            <div v-else class="agent-grid">
              <div v-for="agent in publicAgents" :key="agent.id" class="agent-card">
                <div class="agent-header">
                  <div class="agent-avatar">
                    <img :src="agent.avatar_url" alt="Agent Avatar" />
                  </div>
                  <div class="agent-title">
                    <h3 class="agent-name">{{ agent.name }}</h3>
                    <span class="agent-visibility">公开</span>
                  </div>
                </div>
                <div class="agent-info">
                  <div class="agent-model">{{ agent.model }}</div>
                  <div class="agent-prompt-preview">{{ agent.system_prompt.substring(0, 50) }}{{ agent.system_prompt.length > 50 ? '...' : '' }}</div>
                  <div class="agent-meta">
                    <span class="agent-created">创建于: {{ formatDateTime(agent.created_at) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </Tabs.TabPane>
          
          <Tabs.TabPane key="myAgents" tab="我的 Agent">
            <div v-if="myAgents.length === 0" class="empty-state">
              暂无个人 Agent，点击"创建新 Agent"按钮创建您的第一个 Agent
            </div>
            
            <div v-else class="agent-grid">
              <div v-for="agent in myAgents" :key="agent.id" class="agent-card">
                <div class="agent-header">
                  <div class="agent-avatar">
                    <img :src="agent.avatar_url" alt="Agent Avatar" />
                  </div>
                  <div class="agent-title">
                    <h3 class="agent-name">{{ agent.name }}</h3>
                    <span class="agent-visibility">{{ agent.is_public ? '公开' : '私有' }}</span>
                  </div>
                </div>
                <div class="agent-info">
                  <div class="agent-model">{{ agent.model }}</div>
                  <div class="agent-prompt-preview">{{ agent.system_prompt.substring(0, 50) }}{{ agent.system_prompt.length > 50 ? '...' : '' }}</div>
                  <div class="agent-meta">
                    <span class="agent-created">创建于: {{ formatDateTime(agent.created_at) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </Tabs.TabPane>
        </Tabs>
      </div>
      
      <div v-else class="loading-state">
        加载中...
      </div>

      <!-- 创建 Agent 弹窗 -->
      <Modal
        v-model:visible="createModalVisible"
        title="创建新 Agent"
        width="700px"
        :footer="null"
        @cancel="createModalVisible = false"
      >
        <CreateAgentForm @success="handleAgentCreated" @cancel="createModalVisible = false" />
      </Modal>
    </div>
  </MainLayout>
</template>

<style scoped>
.agent-management {
  padding: 24px;
  max-width: 1500px;
  margin: 0 auto;
  height: 100%;
  overflow: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

h1 {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.create-agent-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.create-agent-btn:hover {
  background-color: #0069d9;
}

.agent-tabs-container {
  margin-bottom: 24px;
}

.agent-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-top: 20px;
}

@media (max-width: 1400px) {
  .agent-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 900px) {
  .agent-grid {
    grid-template-columns: 1fr;
  }
}

.agent-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 20px;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  height: 100%;
  cursor: pointer;
}

.agent-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.agent-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.agent-avatar {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 16px;
  flex-shrink: 0;
}

.agent-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.agent-title {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.agent-name {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 6px 0;
}

.agent-visibility {
  font-size: 12px;
  padding: 2px 8px;
  background-color: #f0f0f0;
  border-radius: 10px;
  width: fit-content;
}

.agent-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.agent-model {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.agent-prompt-preview {
  font-size: 14px;
  color: #888;
  margin-bottom: 20px;
  line-height: 1.6;
  flex: 1;
}

.agent-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
  margin-top: auto;
}

.empty-state {
  text-align: center;
  padding: 40px;
  background-color: #f9f9f9;
  border-radius: 8px;
  color: #666;
  margin-top: 20px;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: #666;
}

:deep(.ant-tabs-nav) {
  margin-bottom: 0;
}

:deep(.ant-tabs-tab) {
  padding: 12px 20px;
}

:deep(.ant-tabs-tab-active) {
  font-weight: 500;
}

:deep(.ant-tabs-content) {
  padding-top: 16px;
}
</style> 