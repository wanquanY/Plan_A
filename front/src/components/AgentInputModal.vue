<template>
  <div v-if="visible" class="agent-input-modal-wrapper" :style="modalStyle">
    <div class="agent-input-modal" ref="modalRef">
      <div class="input-area">
        <textarea
          ref="inputRef"
          class="agent-input"
          placeholder="告诉我你想写点什么"
          v-model="inputValue"
          @keydown="handleKeydown"
          @click.stop
          @input="autoResize"
          rows="1"
        ></textarea>
      </div>
      
      <div class="bottom-controls">
        <div class="model-selector-container">
          <div 
            class="model-selector"
            @click.stop="showAgentSelector = !showAgentSelector"
          >
            <div class="model-avatar" v-if="selectedAgent">
              <img 
                :src="selectedAgent.avatar_url || 'https://placehold.co/40x40?text=AI'" 
                :alt="selectedAgent.name" 
                onerror="this.src='https://placehold.co/40x40?text=AI'"
              />
            </div>
            <span class="model-name">{{ selectedAgent ? selectedAgent.name : 'claude3.7 (我的副本)' }}</span>
            <svg class="dropdown-icon" viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor" d="M7 10l5 5 5-5z"></path>
            </svg>
          </div>
          
          <div v-if="showAgentSelector" class="model-dropdown">
            <div class="model-list">
              <div
                v-for="agent in agents"
                :key="agent.id"
                class="model-item"
                @click.stop="selectAgent(agent)"
              >
                <div class="model-item-avatar">
                  <img 
                    :src="agent.avatar_url || 'https://placehold.co/40x40?text=AI'" 
                    :alt="agent.name" 
                    onerror="this.src='https://placehold.co/40x40?text=AI'"
                  />
                </div>
                <span class="model-item-name">{{ agent.name }}</span>
              </div>
              <div v-if="loading" class="model-loading">加载中...</div>
              <div v-if="!loading && agents.length === 0" class="model-empty">暂无可用AI助手</div>
            </div>
          </div>
        </div>
        
        <div class="right-buttons">
          <button 
            class="attach-button"
            @click.stop
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"></path>
            </svg>
          </button>
          
          <button 
            class="send-button" 
            @click.stop="handleSendMessage"
            :disabled="!selectedAgent || !inputValue.trim()"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.agent-input-modal-wrapper {
  position: fixed;
  z-index: 9999;
}

.agent-input-modal {
  width: 100%;
  background-color: white;
  border-radius: 14px;
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.input-area {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  max-height: 250px;
  overflow: hidden;
  position: relative;
}

.agent-input {
  width: 100%;
  box-sizing: border-box;
  border: none;
  outline: none;
  font-size: 16px;
  line-height: 1.5;
  color: #333;
  background: transparent;
  resize: none;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 24px;
  max-height: 220px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  padding: 0;
  margin: 0;
  word-wrap: break-word;
  display: block;
}

.agent-input::placeholder {
  color: #929292;
  font-weight: 400;
}

.bottom-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px;
  background-color: #fafafa;
  position: relative;
  box-sizing: border-box;
  max-width: 100%;
}

.model-selector-container {
  display: flex;
  align-items: center;
  position: static;
  box-sizing: border-box;
  max-width: 100%;
}

.model-selector {
  display: flex;
  align-items: center;
  background-color: #f1f1f1;
  border-radius: 20px;
  padding: 4px 12px 4px 4px;
  cursor: pointer;
  transition: background-color 0.15s;
  user-select: none;
  box-sizing: border-box;
  max-width: 100%;
  min-width: 0;
}

.model-selector:hover {
  background-color: #e9e9e9;
}

.model-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 8px;
  flex-shrink: 0;
}

.model-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.model-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  padding-right: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 130px;
}

.dropdown-icon {
  opacity: 0.5;
}

.model-dropdown {
  position: absolute;
  top: 100%;
  left: 20px;
  min-width: 200px;
  max-width: 300px;
  background-color: white;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  z-index: 10000;
  overflow: hidden;
  margin-top: 5px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  animation: fadeIn 0.2s ease;
}

.model-list {
  max-height: 280px;
  overflow-y: auto;
}

.model-item {
  padding: 10px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.15s;
  display: flex;
  align-items: center;
}

.model-item:hover {
  background-color: #f5f8ff;
}

.model-item-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 10px;
  flex-shrink: 0;
}

.model-item-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.model-item-name {
  color: #333;
  font-weight: 400;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-loading,
.model-empty {
  padding: 12px 16px;
  font-size: 13px;
  color: #888;
  text-align: center;
}

.right-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
  box-sizing: border-box;
  max-width: 100%;
}

.attach-button, 
.send-button {
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  cursor: pointer;
  transition: all 0.2s;
  outline: none;
  padding: 0;
}

.attach-button {
  width: 24px;
  height: 24px;
  color: rgba(0, 0, 0, 0.55);
}

.attach-button:hover {
  color: rgba(0, 0, 0, 0.8);
}

.send-button {
  width: 36px;
  height: 36px;
  background-color: #d6e5ff;
  border-radius: 50%;
  color: #0066ff;
}

.send-button:hover:not(:disabled) {
  background-color: #c5dcff;
  transform: scale(1.05);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
import agentService from '../services/agent';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  position: {
    type: Object,
    default: () => ({ y: 0, x: 0 })
  },
  editorInfo: {
    type: Object,
    default: () => ({ left: 0, right: 0, width: 0, editorOffsetLeft: 0 })
  }
});

const emit = defineEmits(['close', 'send', 'select-agent']);

// 状态变量
const modalRef = ref(null);
const inputRef = ref(null);
const inputValue = ref('');
const showAgentSelector = ref(false);
const agents = ref([]);
const loading = ref(false);
const selectedAgent = ref(null);

// 计算弹窗位置样式
const modalStyle = computed(() => {
  // 计算合适的位置，确保显示在编辑区域内
  console.log('计算输入框位置，当前信息:', {
    position: props.position,
    editorInfo: props.editorInfo
  });
  
  // 获取编辑器内容区域
  const editorContent = document.querySelector('.editor-content');
  // 获取编辑器主区域
  const editorMain = document.querySelector('.editor-main');
  // 获取大纲是否显示
  const outlineVisible = !!document.querySelector('.document-outline');
  
  console.log('大纲是否可见:', outlineVisible);
  
  let leftPos = props.editorInfo.left; // 默认位置
  let contentWidth = props.editorInfo.width; // 默认宽度
  
  if (editorContent) {
    // 获取编辑内容区域的信息
    const contentRect = editorContent.getBoundingClientRect();
    
    // 尝试找到第一个文本字符
    const paragraphs = editorContent.querySelectorAll('p, h1, h2, h3, h4, h5, h6, div:not(.bottom-placeholder)');
    
    // 遍历段落，寻找有实际文本内容的第一个元素
    for (const para of paragraphs) {
      // 排除空段落或仅含空白字符的段落
      if (para.textContent && para.textContent.trim()) {
        // 创建一个range定位到段落的第一个字符
        const range = document.createRange();
        range.setStart(para, 0);
        
        // 尝试找到第一个文本节点中的第一个字符
        let firstTextNode = null;
        for (const node of para.childNodes) {
          if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
            firstTextNode = node;
            break;
          }
        }
        
        if (firstTextNode) {
          range.setStart(firstTextNode, 0);
          const rect = range.getBoundingClientRect();
          if (rect && rect.left) {
            leftPos = rect.left;
            console.log('找到第一个文本字符位置:', leftPos);
            break;
          }
        } else {
          // 如果没有文本节点，至少使用段落的左边界
          const rect = para.getBoundingClientRect();
          leftPos = rect.left;
          console.log('使用段落左边界:', leftPos);
          break;
        }
      }
    }
    
    // 如果找不到，使用内容区域左边界
    if (leftPos === props.editorInfo.left) {
      leftPos = contentRect.left;
      console.log('未找到文本，使用编辑区域左边界:', leftPos);
    }
    
    // 宽度计算根据是否有大纲而调整
    if (editorMain) {
      const mainRect = editorMain.getBoundingClientRect();
      // 获取实际文本内容区域宽度
      contentWidth = mainRect.width;
      
      // 测量实际文本宽度 - 使用第一个段落
      let textWidth = mainRect.width - 40; // 减去默认边距
      if (paragraphs.length > 0) {
        const firstPara = paragraphs[0];
        const paraRect = firstPara.getBoundingClientRect();
        // 计算段落宽度
        const paraWidth = paraRect.width;
        // 计算段落左右边距
        const leftMargin = paraRect.left - mainRect.left;
        textWidth = paraWidth;
        console.log('段落宽度:', paraWidth, '左边距:', leftMargin);
      }
      
      // 计算弹窗实际宽度 - 与文本内容区域一致
      const rightBoundary = leftPos + textWidth;
      contentWidth = rightBoundary - leftPos;
      
      console.log('编辑器主区域宽度:', mainRect.width, '计算得到内容宽度:', contentWidth);
    }
  }
  
  // 设置弹窗宽度，考虑编辑区域大小
  let modalWidth = contentWidth;
  
  // 确保有最小宽度
  modalWidth = Math.max(modalWidth, 400);
  
  // 确保不超过最大宽度
  modalWidth = Math.min(modalWidth, 800);
  
  console.log('最终使用的弹窗宽度:', modalWidth);
  
  // 处理垂直位置
  let topPos = props.position.y;
  const initialModalHeight = 100; // 初始弹窗高度估计值
  const windowHeight = window.innerHeight;
  
  // 检查是否会超出窗口底部
  if (topPos + initialModalHeight > windowHeight) {
    // 如果会超出底部，则显示在光标上方
    topPos = props.position.y - initialModalHeight - 10;
    
    // 如果上方空间不足，则尽量贴近窗口底部，避免被截断
    if (topPos < 50) { // 50px是顶部安全边距
      topPos = Math.max(windowHeight - initialModalHeight - 20, 50);
    }
  }
  
  return {
    position: 'fixed', // 使用fixed定位，相对于视口
    left: `${leftPos}px`, 
    top: `${topPos}px`,
    width: `${modalWidth}px`, // 设置宽度为文本区域实际宽度
    zIndex: 9999
  };
});

// 加载Agent列表
const fetchAgents = async () => {
  loading.value = true;
  try {
    const agentList = await agentService.getAllAgents();
    agents.value = agentList;
    console.log(`已加载${agentList.length}个AI助手`);
    
    // 默认选择第一个Agent
    if (agentList.length > 0 && !selectedAgent.value) {
      selectAgent(agentList[0]);
    }
  } catch (error) {
    console.error('加载AI助手列表失败:', error);
  } finally {
    loading.value = false;
  }
};

// 选择Agent
const selectAgent = (agent) => {
  selectedAgent.value = agent;
  showAgentSelector.value = false;
  emit('select-agent', agent);
  
  // 聚焦到输入框
  nextTick(() => {
    inputRef.value?.focus();
  });
};

// 发送消息 - 修改为处理selection问题的安全版本
const handleSendMessage = () => {
  if (!selectedAgent.value || !inputValue.value.trim()) return;
  
  // 准备发送消息所需的数据
  const messageData = {
    agentId: selectedAgent.value.id,
    content: inputValue.value.trim(),
    agent: selectedAgent.value
  };
  
  // 清空输入框
  inputValue.value = '';
  
  // 发送消息前关闭弹窗
  close();
  
  // 确保DOM更新后再发送事件
  nextTick(() => {
    emit('send', messageData);
  });
};

// 处理键盘按键事件
const handleKeydown = (event) => {
  // 处理Escape键
  if (event.key === 'Escape') {
    close();
    return;
  }
  
  // 处理Enter键
  if (event.key === 'Enter') {
    // 如果按下Shift+Enter，不阻止默认行为（允许换行）
    if (event.shiftKey) {
      console.log('按下Shift+Enter, 插入换行');
      return;
    }
    
    // 如果是单独的Enter键，阻止默认行为并发送消息
    event.preventDefault();
    handleSendMessage();
  }
};

// 关闭弹窗
const close = () => {
  emit('close');
};

// 监听ESC键按下
const handleKeyDown = (event) => {
  if (event.key === 'Escape' && props.visible) {
    close();
  }
};

// 处理点击事件，点击输入框外部区域关闭
const handleClickOutside = (event) => {
  if (props.visible && modalRef.value && !modalRef.value.contains(event.target)) {
    close();
    event.stopPropagation(); // 阻止事件冒泡
  } else if (props.visible && showAgentSelector.value) {
    // 如果点击的不是选择器区域，则关闭选择器
    const dropdown = modalRef.value?.querySelector('.model-dropdown');
    const selector = modalRef.value?.querySelector('.model-selector');
    if (dropdown && !dropdown.contains(event.target) && !selector.contains(event.target)) {
      showAgentSelector.value = false;
    }
  }
};

// 添加自动调整输入框高度的方法
const autoResize = () => {
  if (!inputRef.value) return;
  
  // 首先重置高度，以便正确计算新高度
  inputRef.value.style.height = 'auto';
  
  // 计算新高度，但不超过最大高度
  const scrollHeight = inputRef.value.scrollHeight;
  const maxHeight = 220; // 最大高度220px，与CSS中定义一致
  
  if (scrollHeight <= maxHeight) {
    // 如果内容高度未超过最大高度，设置为实际高度并隐藏滚动条
    inputRef.value.style.height = `${scrollHeight}px`;
    inputRef.value.style.overflowY = 'hidden';
  } else {
    // 如果内容高度超过最大高度，设置为最大高度并显示滚动条
    inputRef.value.style.height = `${maxHeight}px`;
    inputRef.value.style.overflowY = 'auto';
  }
  
  console.log(`输入框高度: ${inputRef.value.style.height}, 内容高度: ${scrollHeight}px, 是否显示滚动条: ${scrollHeight > maxHeight}`);
};

// 当弹窗显示时，加载Agent列表并聚焦输入框，同时调整输入框高度
watch(() => props.visible, async (newValue) => {
  if (newValue) {
    // 加载Agent列表
    if (agents.value.length === 0) {
      await fetchAgents();
    } else if (agents.value.length > 0 && !selectedAgent.value) {
      // 如果已有Agent列表但尚未选择，默认选择第一个
      selectAgent(agents.value[0]);
    }
    
    // 重置并聚焦到输入框
    nextTick(() => {
      if (inputRef.value) {
        // 重置文本框高度
        inputRef.value.style.height = 'auto';
        inputRef.value.style.overflowY = 'hidden'; // 初始状态隐藏滚动条
        
        // 应用自动调整高度
        autoResize();
        
        // 聚焦到输入框
        inputRef.value.focus();
      }
    });
  } else {
    // 重置一些状态
    showAgentSelector.value = false;
  }
}, { immediate: true });

// 监听inputValue变化，自动调整输入框高度
watch(() => inputValue.value, () => {
  nextTick(() => {
    autoResize();
  });
});

// 组件挂载时添加键盘事件监听
onMounted(() => {
  document.addEventListener('keydown', handleKeyDown);
  // 确保全局点击监听是在捕获阶段添加，优先处理点击事件
  document.addEventListener('click', handleClickOutside, true);
});

// 组件卸载时移除事件监听
onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown);
  document.removeEventListener('click', handleClickOutside, true);
});
</script> 