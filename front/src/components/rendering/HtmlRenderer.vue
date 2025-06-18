<template>
  <div class="html-renderer-wrapper">
    <iframe
      ref="iframeRef"
      :style="{ width: '100%', height: height, border: '1px solid #ddd', 'border-radius': '8px' }"
      @load="renderContent"
      sandbox="allow-scripts allow-same-origin"
    ></iframe>
    <div class="toolbar">
      <button @click="copyHtml" :class="{ 'copied': isCopied }">
        {{ isCopied ? '已复制!' : '复制HTML' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';

const props = defineProps({
  htmlContent: {
    type: String,
    required: true,
  },
  height: {
    type: String,
    default: '400px',
  },
});

const iframeRef = ref<HTMLIFrameElement | null>(null);
const isCopied = ref(false);

const scrollbarStyle = `
  /* 美化滚动条-适用于Chrome、Edge和Safari */
  ::-webkit-scrollbar {
    width: 8px; /* 垂直滚动条宽度 */
    height: 8px; /* 水平滚动条高度 */
  }

  ::-webkit-scrollbar-track {
    background: #f1f1f1; /* 轨道背景色 */
    border-radius: 10px;
  }

  ::-webkit-scrollbar-thumb {
    background: #888; /* 滚动条滑块颜色 */
    border-radius: 10px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: #555; /* 鼠标悬停时滑块颜色 */
  }

  /* 美化滚动条-适用于Firefox */
  * {
    scrollbar-width: thin; /* "auto" or "thin" */
    scrollbar-color: #888 #f1f1f1; /* thumb and track color */
  }
`;

const renderContent = () => {
  if (iframeRef.value && iframeRef.value.contentWindow) {
    const doc = iframeRef.value.contentWindow.document;
    doc.open();
    doc.write(`
      <html>
        <head>
          <style>${scrollbarStyle}</style>
        </head>
        <body>
          ${props.htmlContent}
        </body>
      </html>
    `);
    doc.close();
  }
};

const copyHtml = () => {
  navigator.clipboard.writeText(props.htmlContent).then(() => {
    isCopied.value = true;
    setTimeout(() => {
      isCopied.value = false;
    }, 2000);
  });
};

onMounted(() => {
  renderContent();
});

watch(() => props.htmlContent, () => {
  renderContent();
});
</script>

<style scoped>
.html-renderer-wrapper {
  position: relative;
  margin: 1em 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e0e0e0;
  background-color: #f9f9f9;
}

iframe {
  display: block;
}

.toolbar {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  gap: 8px;
}

button {
  background-color: rgba(255, 255, 255, 0.8);
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.3s, color 0.3s;
}

button:hover {
  background-color: #f0f0f0;
}

button.copied {
  background-color: #d4edda;
  color: #155724;
}
</style> 