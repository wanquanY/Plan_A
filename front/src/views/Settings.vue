<template>
  <div class="settings-page">
    <div class="settings-container">
      <!-- 设置菜单栏 -->
      <div class="settings-sidebar">
        <div class="settings-menu">
          <div 
            class="menu-item" 
            :class="{ active: activeTab === 'basic' }"
            @click="activeTab = 'basic'"
          >
            <SettingOutlined />
            <span>基础设置</span>
          </div>
          <div 
            class="menu-item" 
            :class="{ active: activeTab === 'mcp' }"
            @click="activeTab = 'mcp'"
          >
            <ApiOutlined />
            <span>MCP服务</span>
          </div>
        </div>
      </div>

      <!-- 设置内容区域 -->
      <div class="settings-content">
        <!-- 基础设置 -->
        <div v-if="activeTab === 'basic'" class="settings-section">
          <BasicSettings />
        </div>

        <!-- MCP设置 -->
        <div v-if="activeTab === 'mcp'" class="settings-section">
          <MCPSettings />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { SettingOutlined, ApiOutlined } from '@ant-design/icons-vue';
import BasicSettings from '@/components/Settings/BasicSettings.vue';
import MCPSettings from '@/components/Settings/MCPSettings.vue';

const activeTab = ref('basic');
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  background-color: #f5f5f5;
  padding: 20px;
}

.settings-container {
  display: flex;
  gap: 24px;
  height: calc(100vh - 40px);
}

.settings-sidebar {
  width: 240px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 16px 0;
}

.settings-menu {
  display: flex;
  flex-direction: column;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  cursor: pointer;
  transition: all 0.2s;
  color: #666;
  font-size: 14px;
}

.menu-item:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #333;
}

.menu-item.active {
  background-color: #e6f7ff;
  color: #1890ff;
  border-right: 3px solid #1890ff;
}

.menu-item span {
  font-weight: 500;
}

.settings-content {
  flex: 1;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.settings-section {
  height: 100%;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .settings-container {
    flex-direction: column;
    height: auto;
  }
  
  .settings-sidebar {
    width: 100%;
  }
  
  .settings-menu {
    flex-direction: row;
    overflow-x: auto;
  }
  
  .menu-item {
    white-space: nowrap;
    min-width: 120px;
    justify-content: center;
  }
  
  .menu-item.active {
    border-right: none;
    border-bottom: 3px solid #1890ff;
  }
}
</style> 