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
  if (
    selectorRef.value &&
    !selectorRef.value.contains(event.target as Node)
  ) {
    emit('close');
  }
};

// 选择AI助手
const selectAgent = (agent) => {
  if (!props.currentRange) return;
  
  // 创建一个新的用户提及元素
  const mention = document.createElement('span');
  mention.className = 'user-mention';
  mention.setAttribute('data-agent-id', agent.id);
  mention.setAttribute('data-processed', 'false');
  
  // 创建头像元素
  const avatar = document.createElement('img');
  avatar.src = agent.avatar_url;
  avatar.alt = agent.name;
  avatar.className = 'mention-avatar';
  avatar.style.width = '16px';
  avatar.style.height = '16px';
  avatar.style.borderRadius = '50%';
  avatar.style.marginRight = '4px';
  avatar.style.verticalAlign = 'middle';
  
  // 创建名称文本
  const nameText = document.createTextNode(agent.name);
  
  // 将头像和名称添加到提及元素中
  mention.appendChild(avatar);
  mention.appendChild(nameText);
  
  // 设置提及元素的样式
  mention.contentEditable = 'false';
  mention.style.backgroundColor = '#e6f7ff';
  mention.style.color = '#1890ff';
  mention.style.borderRadius = '3px';
  mention.style.padding = '0 4px';
  mention.style.margin = '0 2px';
  mention.style.display = 'inline-flex';
  mention.style.alignItems = 'center';
  
  // 创建一个新的Range，用于插入用户提及
  const range = props.currentRange.cloneRange();
  
  // 删除@符号，注意这里要注意是否有更多字符
  range.setStart(range.startContainer, range.startOffset - 1);
  range.deleteContents();
  
  // 插入用户提及并关闭选择器
  range.insertNode(mention);
  
  // 将光标移动到提及元素之后
  const selection = window.getSelection();
  if (selection) {
    // 创建一个新的文本节点作为光标定位点
    const textNode = document.createTextNode('\u200B'); // 使用零宽空格作为光标定位点
    const newRange = document.createRange();
    newRange.setStartAfter(mention);
    newRange.collapse(true);
    newRange.insertNode(textNode);
    
    // 将光标定位在零宽空格之后
    newRange.setStartAfter(textNode);
    newRange.collapse(true);
    selection.removeAllRanges();
    selection.addRange(newRange);
  }
  
  // 通知父组件AI助手被选择
  emit('agent-selected', agent);
  emit('close');
};

// 初始化时只添加事件监听，不加载数据
onMounted(() => {
  document.addEventListener('click', handleClickOutside);
  console.log('[MentionHandler] 组件已挂载，但不会自动加载数据');
});

// 监听选择器显示状态变化，只在首次显示时加载数据
watch(() => props.showSelector, (isVisible) => {
  if (isVisible) {
    console.log('[MentionHandler] 选择器显示，加载Agent列表');
    // 每次显示选择器时都重新请求一次数据
    fetchAgents().catch(err => {
      console.error('[MentionHandler] 加载Agent列表失败:', err);
    });
  }
}, { immediate: false });

// 移除点击事件监听
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.agent-selector {
  position: absolute;
  width: 300px;
  max-height: 300px;
  height: auto;
  background-color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border-radius: 4px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.agent-selector-header {
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  background-color: #fafafa;
  border-radius: 4px 4px 0 0;
}

.header-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.agent-list {
  overflow-y: auto;
  max-height: 250px;
}

.no-agents {
  padding: 20px;
  text-align: center;
  color: #666;
}

.agent-item {
  display: flex;
  padding: 10px 12px;
  cursor: pointer;
  transition: background-color 0.2s;
  align-items: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
}

.agent-item:last-child {
  border-bottom: none;
}

.agent-item:hover {
  background-color: #f5f5f5;
}

.agent-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  margin-right: 12px;
}

.agent-avatar img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.agent-info {
  flex: 1;
  overflow: hidden;
}

.agent-name {
  font-weight: 500;
  margin-bottom: 4px;
  color: #333;
}

.agent-description {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style> 