<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { message, Modal, Tabs } from 'ant-design-vue';
import { PlusOutlined, EditOutlined, CopyOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import CreateAgentForm from '@/components/Agent/CreateAgentForm.vue';
import agentService from '@/services/agent';
import userService from '@/services/user';
import type { Agent } from '@/services/agent';
import type { User } from '@/services/user';
import { useRouter } from 'vue-router';

// 状态
const username = ref('用户');
const userId = ref<number | null>(null);
const allAgents = ref<Agent[]>([]);
const loading = ref(false);
const activeTab = ref('myAgents');
const router = useRouter();
const deleteModalVisible = ref(false);
const agentIdToDelete = ref<number | null>(null);

// 获取用户信息
const fetchUserInfo = async () => {
  try {
    // 优先从API获取最新的用户信息
    const user = await userService.getCurrentUser();
    if (user && user.id) {
      username.value = user.username;
      userId.value = user.id;
      userService.cacheUserInfo(user);
      console.log('从API获取用户信息成功:', username.value, 'ID:', userId.value);
      return;
    }
  } catch (error) {
    console.error('从API获取用户信息失败:', error);
  }
  
  // 如果API获取失败，尝试从缓存获取
  const cachedUser = userService.getCachedUserInfo();
  if (cachedUser && cachedUser.id) {
    username.value = cachedUser.username;
    userId.value = cachedUser.id;
    console.log('从缓存获取用户信息成功:', username.value, 'ID:', userId.value);
  } else {
    console.error('缓存中也没有有效的用户信息');
  }
};

// 过滤我的Agent和公开Agent
const myAgents = computed(() => {
  if (!userId.value) {
    console.warn('用户ID为空，无法筛选我的Agent');
    return [];
  }
  
  const filtered = allAgents.value.filter(agent => {
    const isOwned = agent.user_id === userId.value;
    if (isOwned) {
      console.log(`Agent ${agent.id} 属于当前用户(${userId.value})`);
    }
    return isOwned;
  });
  
  console.log(`我的Agent筛选结果: 找到 ${filtered.length} 个属于用户 ${userId.value} 的Agent`);
  return filtered;
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
    console.log('获取到的Agent列表:', agentsData.length, '个');
    
    // 检查每个Agent的user_id
    const userIds = new Set(agentsData.map(agent => agent.user_id));
    console.log('Agent列表中的用户ID:', Array.from(userIds));
    console.log('当前用户ID:', userId.value);
    
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
  router.push('/create-agent');
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

// 检查是否是自己创建的Agent
const isOwnAgent = (agent: Agent): boolean => {
  return agent.user_id === userId.value;
};

// 复制公开Agent创建自己的副本
const copyAgent = async (agentId: number) => {
  loading.value = true;
  message.loading('正在创建Agent副本...', 0);
  
  try {
    const newAgent = await agentService.createAgentFromTemplate(agentId);
    if (newAgent) {
      message.success('成功创建Agent副本');
      await fetchAgents();
      // 切换到"我的Agent"标签
      activeTab.value = 'myAgents';
    } else {
      message.error('创建Agent副本失败');
    }
  } catch (error) {
    console.error('复制Agent失败:', error);
    message.error('复制Agent失败');
  } finally {
    loading.value = false;
    message.destroy(); // 关闭加载提示
  }
};

// 删除Agent确认
const deleteAgentConfirm = (agentId: number) => {
  agentIdToDelete.value = agentId;
  deleteModalVisible.value = true;
};

// 确认删除
const confirmDelete = async () => {
  if (!agentIdToDelete.value) return;
  
  try {
    const success = await agentService.deleteAgent(agentIdToDelete.value);
    if (success) {
      message.success('Agent删除成功');
      await fetchAgents(); // 重新获取列表
    } else {
      message.error('删除失败');
    }
  } catch (error) {
    console.error('删除Agent失败:', error);
    message.error('删除Agent失败');
  } finally {
    deleteModalVisible.value = false;
    agentIdToDelete.value = null;
  }
};

// 取消删除
const cancelDelete = () => {
  deleteModalVisible.value = false;
  agentIdToDelete.value = null;
};

// 页面加载时获取用户信息和Agent列表
onMounted(async () => {
  // 先获取用户信息
  await fetchUserInfo();
  console.log('页面加载时获取到的用户ID:', userId.value);
  
  // 确保有用户信息后再获取Agent列表
  if (userId.value) {
    await fetchAgents();
    // 默认显示我的Agent
    activeTab.value = 'myAgents';
  } else {
    console.error('未能获取用户信息，无法加载Agent列表');
    message.error('获取用户信息失败，请刷新页面重试');
  }
});
</script>

<template>
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
              <div class="card-actions">
                <div class="edit-button" v-if="isOwnAgent(agent)" @click.stop="router.push(`/create-agent?id=${agent.id}`)">
                  <EditOutlined />
                </div>
                <div class="copy-button" v-if="!isOwnAgent(agent)" @click.stop="copyAgent(agent.id)">
                  <CopyOutlined />
                </div>
              </div>
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
                <div class="agent-prompt-preview">{{ agent.system_prompt?.substring(0, 50) }}{{ agent.system_prompt?.length > 50 ? '...' : '' }}</div>
                <div class="agent-tools" v-if="agent.tools_enabled">
                  <div class="tool-badges">
                    <span class="tool-badge" v-if="agent.tools_enabled.tavily?.enabled">搜索能力</span>
                  </div>
                </div>
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
              <div class="card-actions">
                <div class="edit-button" @click.stop="router.push(`/create-agent?id=${agent.id}`)">
                  <EditOutlined />
                </div>
                <div class="delete-button" @click.stop="deleteAgentConfirm(agent.id)">
                  <DeleteOutlined />
                </div>
              </div>
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
                <div class="agent-prompt-preview">{{ agent.system_prompt?.substring(0, 50) }}{{ agent.system_prompt?.length > 50 ? '...' : '' }}</div>
                <div class="agent-tools" v-if="agent.tools_enabled">
                  <div class="tool-badges">
                    <span class="tool-badge" v-if="agent.tools_enabled.tavily?.enabled">搜索能力</span>
                  </div>
                </div>
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

    <!-- 删除确认弹窗 -->
    <Modal
      v-model:visible="deleteModalVisible"
      title="删除确认"
      @ok="confirmDelete"
      @cancel="cancelDelete"
      okText="确认删除"
      cancelText="取消"
      :okButtonProps="{ danger: true }"
    >
      <p>确定要删除这个Agent吗？此操作不可撤销。</p>
    </Modal>
  </div>
</template>

<style scoped>
.agent-management {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
  width: 100%;
  height: 100%;
  overflow: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.create-agent-btn {
  background: linear-gradient(135deg, #1890ff, #52c41a);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s;
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.15);
}

.create-agent-btn:hover {
  background: linear-gradient(135deg, #40a9ff, #73d13d);
  transform: translateY(-2px);
  box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
}

.create-agent-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}

.agent-tabs-container {
  margin-bottom: 32px;
}

.agent-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-top: 20px;
}

@media (max-width: 1600px) {
  .agent-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1200px) {
  .agent-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .agent-grid {
    grid-template-columns: 1fr;
  }
}

.agent-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 24px;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  height: 100%;
  cursor: pointer;
  position: relative;
}

.agent-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.card-actions {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  gap: 10px;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 10;
}

.agent-card:hover .card-actions {
  opacity: 1;
}

.edit-button, .copy-button, .delete-button {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.9);
  border: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.edit-button:hover {
  background-color: #e6f7ff;
  border-color: #1890ff;
  color: #1890ff;
  transform: scale(1.1);
}

.copy-button:hover {
  background-color: #f6ffed;
  border-color: #52c41a;
  color: #52c41a;
  transform: scale(1.1);
}

.delete-button:hover {
  background-color: #fff1f0;
  border-color: #ff4d4f;
  color: #ff4d4f;
  transform: scale(1.1);
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
  margin-bottom: 15px;
  line-height: 1.6;
  flex: 1;
}

.agent-tools {
  margin-bottom: 15px;
}

.tool-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tool-badge {
  background-color: #e6f7ff;
  color: #1890ff;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid #91d5ff;
}

.agent-meta {
  font-size: 12px;
  color: #aaa;
  margin-top: auto;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
  background-color: #f9f9f9;
  border-radius: 8px;
  margin-top: 20px;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: #666;
  font-size: 16px;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .agent-management {
    padding: 16px;
  }
  
  .page-header {
    margin-bottom: 24px;
  }
  
  .agent-tabs-container {
    margin-bottom: 24px;
  }
}
</style> 