<template>
  <div class="loading-animation" :class="{ 'inline': inline }">
    <div v-if="type === 'dots'" class="loading-dots">
      <span></span>
      <span></span>
      <span></span>
    </div>
    <div v-else-if="type === 'typing'" class="loading-typing">
      <span></span>
      <span></span>
      <span></span>
    </div>
    <div v-else-if="type === 'pulse'" class="loading-pulse">
      <span></span>
    </div>
    <div v-else class="loading-spinner" :style="{ width: size + 'px', height: size + 'px' }">
      <svg viewBox="0 0 50 50">
        <circle cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps({
  // 动画类型：spinner（默认旋转环）, dots（三点）, typing（打字）, pulse（脉冲）
  type: {
    type: String,
    default: 'dots'
  },
  // 是否内联显示（适合文本中使用）
  inline: {
    type: Boolean,
    default: true
  },
  // 动画大小（针对spinner类型）
  size: {
    type: Number,
    default: 16
  }
});
</script>

<style scoped>
.loading-animation {
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-animation.inline {
  display: inline-flex;
  vertical-align: middle;
  margin: 0 4px;
}

/* 旋转环动画 */
.loading-spinner {
  width: 16px;
  height: 16px;
  position: relative;
}

.loading-spinner svg {
  animation: rotate 2s linear infinite;
  transform-origin: center center;
}

.loading-spinner circle {
  stroke: currentColor;
  stroke-dasharray: 126;
  stroke-dashoffset: 126;
  animation: dash 1.5s ease-in-out infinite;
  stroke-linecap: round;
}

@keyframes rotate {
  100% {
    transform: rotate(360deg);
  }
}

@keyframes dash {
  0% {
    stroke-dashoffset: 126;
  }
  50% {
    stroke-dashoffset: 31.5;
  }
  100% {
    stroke-dashoffset: 126;
  }
}

/* 三点动画 */
.loading-dots {
  display: inline-flex;
  align-items: center;
}

.loading-dots span {
  width: 5px;
  height: 5px;
  margin: 0 2px;
  background-color: currentColor;
  border-radius: 50%;
  display: inline-block;
  animation: dots 1.4s infinite ease-in-out both;
  opacity: 0.6;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes dots {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.2;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* 打字动画 */
.loading-typing {
  display: inline-flex;
  align-items: flex-end;
  height: 1em;
}

.loading-typing span {
  width: 5px;
  height: 5px;
  margin: 0 1px;
  background-color: currentColor;
  border-radius: 50%;
  display: inline-block;
  animation: typing 1s infinite ease-in-out both;
}

.loading-typing span:nth-child(1) {
  animation-delay: 0.2s;
}

.loading-typing span:nth-child(2) {
  animation-delay: 0.4s;
}

.loading-typing span:nth-child(3) {
  animation-delay: 0.6s;
}

@keyframes typing {
  0% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
  100% {
    transform: translateY(0);
  }
}

/* 脉冲动画 */
.loading-pulse {
  display: inline-flex;
}

.loading-pulse span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: currentColor;
  animation: pulse 1.5s infinite ease-in-out;
}

@keyframes pulse {
  0% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  50% {
    transform: scale(1);
    opacity: 1;
  }
  100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
}
</style> 