<template>
  <div v-if="showSelector" class="agent-selector" ref="selectorRef">
    <div class="agent-selector-header">
      <div class="header-title">选择AI助手</div>
    </div>
    <div class="agent-list">
      <div
        v-for="agent in availableAgents"
        :key="agent.id"
        class="agent-item"
        @click="selectAgent(agent)"
      >
        <div class="agent-avatar">
          <img :src="agent.avatar_url" alt="Agent avatar" onerror="this.src='https://placehold.co/40x40?text=AI'" />
        </div>
        <div class="agent-info">
          <div class="agent-name">{{ agent.name }}</div>
          <div class="agent-description">{{ agent.system_prompt }}</div>
        </div>
      </div>
      <div v-if="loading" class="no-agents">
        加载中...
      </div>
      <div v-if="!loading && availableAgents.length === 0" class="no-agents">
        暂无可用AI助手
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import agentService from '../services/agent';

const props = defineProps({
  showSelector: {
    type: Boolean,
    default: false
  },
  currentRange: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close', 'agent-selected']);

const selectorRef = ref<HTMLElement | null>(null);
const agents = ref<any[]>([]);
const loading = ref(false);

// 获取可用的AI助手
const availableAgents = computed(() => {
  return agents.value;
});

// 加载所有代理
const fetchAgents = async () => {
  loading.value = true;
  try {
    const agentList = await agentService.getAllAgents();
    agents.value = agentList;
    console.log(`已加载${agentList.length}个AI助手`);
  } catch (error) {
    console.error('加载AI助手列表失败:', error);
  } finally {
    loading.value = false;
  }
};

// 监听点击事件，检查是否点击在选择器外部
const handleClickOutside = (event: MouseEvent) => {
  if (selectorRef.value && !selectorRef.value.contains(event.target as Node)) {
    emit('close');
  }
};

// 选择AI助手
const selectAgent = (agent: any) => {
  // 获取最近创建的"无Agent"输入框
  const noAgentInputs = document.querySelectorAll('.agent-input.no-agent');
  if (noAgentInputs.length === 0) {
    console.error('未找到等待关联Agent的输入框');
    emit('close');
    return;
  }
  
  // 获取最后一个"无Agent"输入框（最近创建的）
  const inputElement = noAgentInputs[noAgentInputs.length - 1] as HTMLInputElement;
  if (!inputElement) {
    console.error('无法获取输入框元素');
    emit('close');
    return;
  }
  
  // 获取输入框的容器
  const inputContainer = inputElement.closest('.agent-input-container');
  if (!inputContainer) {
    console.error('无法获取输入框容器');
    emit('close');
    return;
  }
  
  // 获取选择按钮并更新为已选择的Agent
  const selectorButton = inputContainer.querySelector('.agent-selector-button');
  if (selectorButton) {
    // 设置按钮内容为已选择的Agent
    selectorButton.innerHTML = `
      <img src="${agent.avatar_url || 'https://placehold.co/40x40?text=AI'}" 
           alt="${agent.name}" 
           onerror="this.src='https://placehold.co/40x40?text=AI'" />
      <span>${agent.name}</span>
    `;
  }
  
  // 更新输入框属性和状态
  inputElement.disabled = false;
  inputElement.placeholder = `问${agent.name}...`;
  inputElement.classList.remove('no-agent');
  inputElement.setAttribute('data-agent-id', agent.id);
  
  // 启用发送按钮
  const sendButton = inputContainer.querySelector('.agent-send-button');
  if (sendButton) {
    sendButton.removeAttribute('disabled');
  }
  
  // 聚焦到输入框
  setTimeout(() => {
    inputElement.focus();
  }, 0);
  
  // 关闭选择器
  emit('close');
  emit('select', agent);
};

// 当组件显示时，加载AI助手
watch(() => props.showSelector, (value) => {
  if (value) {
    fetchAgents();
  }
});

onMounted(() => {
  if (props.showSelector) {
    fetchAgents();
  }
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

// 更新选择器位置方法
const updateSelectorPosition = () => {
  if (!selectorRef.value || !props.range) return;
  
  const rect = props.range.getBoundingClientRect();
  const selectorElement = selectorRef.value;
  
  // 获取编辑器容器
  const editorContainer = document.querySelector('.editor-content');
  if (!editorContainer) return;
  
  const editorRect = editorContainer.getBoundingClientRect();
  
  // 计算选择器应该显示的位置，优先显示在输入框下方
  const inputContainer = props.range.parentElement;
  if (inputContainer && inputContainer.classList.contains('agent-input-container')) {
    const inputRect = inputContainer.getBoundingClientRect();
    
    // 设置位置到输入框下方
    selectorElement.style.top = `${inputRect.bottom + 5}px`;
    selectorElement.style.left = `${inputRect.left}px`;
    
    // 确保选择器不会超出编辑器的右边界
    const rightOverflow = inputRect.left + selectorElement.offsetWidth - (editorRect.left + editorRect.width);
    if (rightOverflow > 0) {
      selectorElement.style.left = `${inputRect.left - rightOverflow - 10}px`;
    }
  } else {
    // 设置位置到光标位置下方
    selectorElement.style.top = `${rect.bottom + 5}px`;
    selectorElement.style.left = `${rect.left}px`;
    
    // 确保选择器不会超出编辑器的右边界
    const rightOverflow = rect.left + selectorElement.offsetWidth - (editorRect.left + editorRect.width);
    if (rightOverflow > 0) {
      selectorElement.style.left = `${rect.left - rightOverflow - 10}px`;
    }
  }
};

// 暴露方法给父组件
defineExpose({
  selectAgent,
  updateSelectorPosition
});
</script>

<style scoped>
.agent-selector {
  position: absolute;
  z-index: 1000;
  min-width: 320px;
  max-width: 400px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid #e8e8e8;
  overflow: hidden;
}

.agent-selector-header {
  padding: 10px 16px;
  border-bottom: 1px solid #f0f0f0;
  background-color: #fafafa;
}

.header-title {
  font-size: 14px;
  font-weight: 500;
  color: #000;
}

.agent-list {
  max-height: 300px;
  overflow-y: auto;
  padding: 8px 0;
}

.agent-item {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.agent-item:hover {
  background-color: #f5f5f5;
}

.agent-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 12px;
  flex-shrink: 0;
}

.agent-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 14px;
  font-weight: 500;
  color: #1f1f1f;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-description {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.no-agents {
  text-align: center;
  padding: 16px;
  color: #999;
  font-size: 14px;
}
</style> 