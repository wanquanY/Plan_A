import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import 'highlight.js/styles/github.css'

import App from './App.vue'
import router from './router'
import './assets/main.css'
import './assets/styles/global.css'

// 导入画板组件
import EmbeddedCanvas from './components/Canvas/EmbeddedCanvas.vue'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Antd)

// 注册全局组件
app.component('embedded-canvas', EmbeddedCanvas)

// 将router暴露到window对象，供动态挂载的组件使用
window.__VUE_APP_ROUTER__ = router;

// 添加全局清理函数
const cleanupTempMarkers = () => {
  try {
    const markers = document.querySelectorAll('[data-temp-marker="true"]');
    markers.forEach(marker => {
      if (marker.parentNode) {
        marker.parentNode.removeChild(marker);
      }
    });
    console.log(`[App] 清理了 ${markers.length} 个临时标记`);
  } catch (error) {
    console.error('[App] 清理临时标记失败:', error);
  }
};

// 页面卸载时清理临时标记
window.addEventListener('beforeunload', cleanupTempMarkers);

// 初始化应用
app.mount('#app')
