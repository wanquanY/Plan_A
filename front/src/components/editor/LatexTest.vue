<template>
  <div class="latex-test-container">
    <h2>LaTeX 公式测试</h2>
    
    <div class="test-section">
      <h3>行内公式测试</h3>
      <div class="content" v-html="inlineLatexHTML"></div>
    </div>
    
    <div class="test-section">
      <h3>块级公式测试</h3>
      <div class="content" v-html="blockLatexHTML"></div>
    </div>
    
    <div class="test-section">
      <h3>混合公式测试</h3>
      <div class="content" v-html="mixedLatexHTML"></div>
    </div>
    
    <button @click="renderFormulas" class="render-btn">手动触发渲染</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { processLatexFormulas } from '../../services/markdownService';
import { renderLatexFormulas } from '../../services/renderService';

const inlineLatexHTML = ref('');
const blockLatexHTML = ref('');
const mixedLatexHTML = ref('');

const inlineLatexContent = '这是一个行内公式：$f(x) = ax^2 + bx + c$，其中 $a > 0$。';
const blockLatexContent = '这是一个块级公式：$$\\sum_{i=1}^{n} x_i = \\int_{0}^{1} f(x) dx$$';
const mixedLatexContent = `
已知二次函数 $f(x) = ax^2 + bx + c$ (其中 $a > 0$) 的图像经过点 $A(1, 0)$ 和 $B(3, 0)$，且函数的最小值为 $-2$。

求解：
$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$

不等式 $f(x) \\geq kx - 5$ 对所有 $x \\in [0, 4]$ 恒成立。
`;

const processContent = () => {
  console.log('开始处理LaTeX内容...');
  
  inlineLatexHTML.value = processLatexFormulas(inlineLatexContent);
  blockLatexHTML.value = processLatexFormulas(blockLatexContent);
  mixedLatexHTML.value = processLatexFormulas(mixedLatexContent);
  
  console.log('行内公式HTML:', inlineLatexHTML.value);
  console.log('块级公式HTML:', blockLatexHTML.value);
  console.log('混合公式HTML:', mixedLatexHTML.value);
};

const renderFormulas = async () => {
  console.log('手动触发LaTeX渲染...');
  await nextTick();
  renderLatexFormulas();
};

onMounted(async () => {
  processContent();
  await nextTick();
  setTimeout(() => {
    renderLatexFormulas();
  }, 100);
});
</script>

<style scoped>
.latex-test-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.test-section {
  margin: 20px 0;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.test-section h3 {
  margin-top: 0;
  color: #333;
}

.content {
  background-color: white;
  padding: 15px;
  border-radius: 4px;
  min-height: 50px;
  font-size: 16px;
  line-height: 1.6;
}

.render-btn {
  background-color: #1677ff;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  margin-top: 20px;
}

.render-btn:hover {
  background-color: #0958d9;
}
</style> 