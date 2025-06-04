<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { 
  UserOutlined, 
  RobotOutlined, 
  LogoutOutlined 
} from '@ant-design/icons-vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  position: {
    type: Object,
    default: () => ({ x: 0, y: 0 })
  }
});

const emit = defineEmits(['close', 'navigate', 'logout']);

// 菜单引用
const menuRef = ref<HTMLElement | null>(null);

// 关闭菜单
const closeMenu = () => {
  emit('close');
};

// 导航到指定页面
const navigateTo = (path) => {
  emit('navigate', path);
  closeMenu();
};

// 注销
const logout = () => {
  emit('logout');
  closeMenu();
};

// 点击外部区域关闭菜单
const handleClickOutside = (event: Event) => {
  if (props.visible && menuRef.value) {
    const target = event.target as HTMLElement;
    // 检查点击的元素是否在菜单内部
    if (!menuRef.value.contains(target)) {
      emit('close');
    }
  }
};

// 监听全局点击事件，用于关闭菜单
onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<template>
  <div class="dropdown-menu-wrapper" v-if="visible">
    <div class="dropdown-menu" ref="menuRef" :style="{ left: `${position.x}px`, top: `${position.y}px` }">
      <div class="menu-item" @click="navigateTo('/user-profile')">
        <UserOutlined />
        <span>用户信息</span>
      </div>
      
      <div class="menu-item" @click="navigateTo('/agent/edit')">
        <RobotOutlined />
        <span>设置</span>
      </div>
      
      <div class="menu-divider"></div>
      
      <div class="menu-item logout" @click="logout">
        <LogoutOutlined />
        <span>退出登录</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dropdown-menu-wrapper {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2000;
}

.dropdown-menu {
  position: absolute;
  background-color: white;
  border-radius: 8px;
  width: 160px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 2001;
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.menu-item:hover {
  background-color: #f5f5f5;
}

.menu-item.logout {
  color: #ff4d4f;
}

.menu-divider {
  height: 1px;
  background-color: #f0f0f0;
  margin: 4px 0;
}
</style> 