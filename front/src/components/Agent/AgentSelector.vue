<template>
  <div v-if="show" class="agent-selector" :style="{ top: `${top}px`, left: `${left}px` }">
    <div class="selector-header">
      <div class="tabs">
        <div 
          class="tab" 
          :class="{ active: activeTab === 'all' }"
          @click="switchTab('all')"
        >全部</div>
        <div 
          class="tab" 
          :class="{ active: activeTab === 'mine' }"
          @click="switchTab('mine')"
        >我的</div>
      </div>
    </div>
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>
    <div v-else-if="displayAgents.length === 0" class="no-results">
      <span>未找到Agent</span>
    </div>
    <ul v-else class="agent-list">
      <li 
        v-for="agent in displayAgents" 
        :key="agent.id"
        class="agent-item"
        :class="{ 'agent-item-active': selectedIndex === displayAgents.indexOf(agent) }"
        @click="selectAgent(agent)"
        @mouseenter="selectedIndex = displayAgents.indexOf(agent)"
      >
        <img src="https://via.placeholder.com/40x40?text=AI" alt="avatar" class="agent-avatar" />
        <div class="agent-info">
          <div class="agent-name">AI助手</div>
          <div class="agent-model">{{ agent.model }}</div>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue';
import agentService from '../../services/agent';
import userService from '../../services/user';
import type { Agent } from '../../services/agent';

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  top: {
    type: Number,
    default: 0
  },
  left: {
    type: Number,
    default: 0
  },
  query: {
    type: String,
    default: ''
  },
  mentionRange: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['select', 'close']);

const agents = ref<Agent[]>([]);
const filteredAgents = ref<Agent[]>([]);
const loading = ref(false);
const selectedIndex = ref(0);
const activeTab = ref('all'); // 默认显示全部标签页
const currentUserId = ref<number | null>(null); // 当前用户ID，从用户服务获取

// 获取当前用户信息
const fetchCurrentUser = async () => {
  try {
    // 首先尝试获取缓存的用户信息
    const cachedUser = userService.getCachedUserInfo();
    if (cachedUser && cachedUser.id) {
      currentUserId.value = cachedUser.id;
      console.log('从缓存获取当前用户ID:', currentUserId.value);
      return;
    }

    // 如果没有缓存，则从API获取
    const user = await userService.getCurrentUser();
    if (user && user.id) {
      currentUserId.value = user.id;
      console.log('从API获取当前用户ID:', currentUserId.value);
      // 缓存用户信息以供后续使用
      userService.cacheUserInfo(user);
    }
  } catch (error) {
    console.error('获取当前用户信息失败:', error);
    // 失败时使用默认值（可选）
    currentUserId.value = null;
  }
};

// 切换标签页
const switchTab = (tab: string) => {
  console.log('切换到标签页:', tab);
  activeTab.value = tab;
  selectedIndex.value = 0; // 重置选中项
};

// 根据当前标签页过滤要显示的agents
const displayAgents = computed(() => {
  if (activeTab.value === 'mine') {
    // 只显示当前用户的agents
    console.log('当前用户ID:', currentUserId.value, '筛选我的Agent列表');
    return filteredAgents.value.filter(agent => agent.user_id === currentUserId.value);
  } else {
    // 显示所有agents
    console.log('当前用户ID:', currentUserId.value, '显示全部Agent列表');
    return filteredAgents.value;
  }
});

// 获取所有agents
const fetchAgents = async () => {
  loading.value = true;
  try {
    console.log('开始获取Agents...');
    // 先获取用户ID（如果还没获取）
    if (!currentUserId.value) {
      await fetchCurrentUser();
    }
    
    // 尝试从服务器获取数据
    let result = [];
    try {
      console.log('使用用户ID获取Agent列表:', currentUserId.value);
      const apiResult = await agentService.getAllAgents();
      if (apiResult && apiResult.length > 0) {
        console.log('API成功返回Agents:', apiResult.length, '个');
        // 记录每个Agent的用户ID，确认数据正确性
        const userIds = apiResult.map(a => a.user_id);
        console.log('Agent所属用户ID列表:', userIds);
        result = apiResult;
      } else {
        console.warn('API返回的Agent列表为空');
      }
    } catch (apiError) {
      console.error('API获取失败:', apiError);
      // 使用模拟数据
      result = [
        {
          id: 1,
          user_id: currentUserId.value || 1, // 使用当前用户ID
          name: "创作小助手",
          avatar_url: "https://syngents-userfile-1321707147.cos.ap-beijing.myqcloud.com/toboss/files/2e47182a-7e70-4ec0-8d4e-c582a9027de1.png",
          system_prompt: "你是一个创作助手",
          model: "gpt-4.1-2025-04-14",
          max_memory: 100,
          model_settings: {
            temperature: 0.7,
            top_p: 1,
            frequency_penalty: 0,
            presence_penalty: 0,
            max_tokens: 32768
          },
          is_public: true,
          created_at: "2025-05-03T22:55:17.541398+00:00",
          updated_at: "2025-05-03T22:55:17.541398+00:00"
        },
        {
          id: 4,
          user_id: (currentUserId.value || 1) + 1, // 设置为不同于当前用户的ID
          name: "文案助手",
          avatar_url: "https://syngents-userfile-1321707147.cos.ap-beijing.myqcloud.com/toboss/files/94d3db4a-d541-43c9-9503-295ec12b14ed.jpeg",
          system_prompt: "你是文案助手",
          model: "gpt-4.1-2025-04-14",
          max_memory: 100,
          model_settings: {
            temperature: 0.7,
            top_p: 1,
            frequency_penalty: 0,
            presence_penalty: 0,
            max_tokens: 32768
          },
          is_public: true,
          created_at: "2025-05-03T23:12:52.149671+00:00",
          updated_at: "2025-05-03T23:12:52.149671+00:00"
        }
      ];
      console.log('使用模拟数据替代:', result);
    }
    
    agents.value = result;
    filteredAgents.value = result; // 初始化显示所有结果
    console.log('获取到的Agents:', result.length, '个');
    
    // 检查我的Agent是否正确分类
    const myAgents = result.filter(a => a.user_id === currentUserId.value);
    console.log(`当前用户(${currentUserId.value})的Agents:`, myAgents.length, '个');
  } catch (error) {
    console.error('获取Agent列表失败:', error);
    // 设置一些默认数据
    agents.value = [
      {
        id: 99,
        user_id: currentUserId.value || 1,
        system_prompt: "备用系统",
        model: "gpt-4",
        max_memory: 100,
        model_settings: {
          temperature: 0.7,
          top_p: 1,
          frequency_penalty: 0,
          presence_penalty: 0,
          max_tokens: 4000
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    ];
    filteredAgents.value = agents.value;
  } finally {
    loading.value = false;
  }
};

// 根据查询字符串过滤agents
const filterAgents = () => {
  if (!props.query) {
    filteredAgents.value = agents.value;
    return;
  }
  
  const query = props.query.toLowerCase();
  filteredAgents.value = agents.value.filter(agent => 
    agent.model.toLowerCase().includes(query)
  );
  
  console.log('过滤后的Agents:', filteredAgents.value);
};

// 选择agent
const selectAgent = (agent: Agent) => {
  console.log('选择Agent:', agent);
  emit('select', agent);
};

// 关闭选择器
const closeAgentSelector = () => {
  emit('close');
};

// 处理键盘导航
const handleKeyDown = (event: KeyboardEvent) => {
  if (!props.show) return;
  
  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault();
      selectedIndex.value = (selectedIndex.value + 1) % displayAgents.value.length;
      break;
    case 'ArrowUp':
      event.preventDefault();
      selectedIndex.value = (selectedIndex.value - 1 + displayAgents.value.length) % displayAgents.value.length;
      break;
    case 'Enter':
      event.preventDefault();
      if (displayAgents.value[selectedIndex.value]) {
        selectAgent(displayAgents.value[selectedIndex.value]);
      }
      break;
    case 'Escape':
      event.preventDefault();
      closeAgentSelector();
      break;
  }
};

// 监听查询字符串变化
watch(() => props.query, (newVal) => {
  console.log('查询字符串变化:', newVal);
  filterAgents();
});

// 监听显示状态变化
watch(() => props.show, (newVal) => {
  console.log('选择器显示状态变化:', newVal);
  if (newVal) {
    fetchAgents();
    selectedIndex.value = 0;
    activeTab.value = 'all'; // 每次打开时重置为全部标签
  }
});

onMounted(async () => {
  // 获取当前用户ID
  await fetchCurrentUser();
  
  if (props.show) {
    await fetchAgents();
  }
  document.addEventListener('keydown', handleKeyDown);
  
  // 监听自定义事件，接收模拟数据
  document.addEventListener('agent-selector-mock-data', ((event: CustomEvent) => {
    console.log('收到模拟数据事件:', event.detail);
    if (event.detail && Array.isArray(event.detail)) {
      agents.value = event.detail;
      filteredAgents.value = event.detail;
    }
  }) as EventListener);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown);
  document.removeEventListener('agent-selector-mock-data', (() => {}) as EventListener);
});

// 计算属性简化代码
watch(() => agents.value, filterAgents);

// 更新Agent查询字符串
const updateAgentQuery = () => {
  const selection = window.getSelection();
  if (!selection || selection.rangeCount === 0 || !props.mentionRange) return;
  
  try {
    const currentRange = selection.getRangeAt(0);
    const startContainer = props.mentionRange.startContainer;
    
    if (startContainer.nodeType === Node.TEXT_NODE) {
      const textContent = startContainer.textContent || '';
      const mentionStartOffset = props.mentionRange.startOffset;
      const currentOffset = currentRange.startOffset;
      
      // 提取@后面输入的文字作为查询
      if (currentOffset > mentionStartOffset) {
        const queryText = textContent.substring(mentionStartOffset, currentOffset);
        console.log('查询文本:', queryText);
        // 移除@符号，只保留后面的内容
        agentQuery.value = queryText.startsWith('@') ? queryText.substring(1) : queryText;
      } else {
        // 如果光标位置在@符号前，关闭选择器
        closeAgentSelector();
      }
    }
  } catch (error) {
    console.error('更新查询字符串时出错:', error);
    closeAgentSelector();
  }
};
</script>

<style scoped>
.agent-selector {
  position: absolute;
  z-index: 1000;
  width: 320px;
  max-height: 400px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(0, 0, 0, 0.1);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.selector-header {
  padding: 0;
  border-bottom: 1px solid #eee;
}

.tabs {
  display: flex;
  align-items: center;
}

.tab {
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
  color: #666;
}

.tab.active {
  color: #1677ff;
  border-bottom: 2px solid #1677ff;
}

.loading, .no-results {
  padding: 16px;
  text-align: center;
  color: #666;
}

.loading-spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: #09f;
  animation: spin 1s linear infinite;
  margin-right: 8px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.agent-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  max-height: 350px;
}

.agent-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.agent-item:hover, .agent-item-active {
  background-color: rgba(0, 0, 0, 0.05);
}

.agent-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  margin-right: 12px;
}

.agent-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.agent-name {
  font-size: 15px;
  font-weight: 500;
  color: #333;
  line-height: 1.2;
}

.agent-model {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
}
</style> 