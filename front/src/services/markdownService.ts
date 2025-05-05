import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';

// 配置DOMPurify，允许代码块的语言类和样式
DOMPurify.addHook('afterSanitizeAttributes', function(node) {
  // 为代码块添加类属性
  if (node.nodeName === 'CODE' && node.parentNode && node.parentNode.nodeName === 'PRE') {
    // 保留language-*类，用于语法高亮
    node.className = node.className.replace(/language-\w+/, match => match);
  }
  
  // 保留pre标签的data-language属性
  if (node.nodeName === 'PRE' && node.hasAttribute('data-language')) {
    // 确保data-language属性被保留
    const lang = node.getAttribute('data-language');
    if (lang) {
      node.setAttribute('data-language', lang);
    }
  }
});

// 用于生成思维导图的正则表达式
const mindMapRegex = /^# .+(\n[#]+ .+)+$/m;

// 检查内容是否可能是思维导图
export const isMindMapContent = (content: string): boolean => {
  // 检查是否符合思维导图格式：以#开头的多行内容，至少有一个二级标题
  return mindMapRegex.test(content) || 
         // 至少包含一个一级标题和多个层级标题
         (!!content.match(/^#\s+.+/m) && !!content.match(/^#{2,}\s+.+/m));
};

// 检测代码块的语言
export const detectCodeLanguage = (code: string): string => {
  // HTML检测 - 优先检查和表单相关的标签和属性
  if (
    // 基础HTML标签
    code.includes('<html') || code.includes('<!DOCTYPE') || 
    code.includes('<head') || code.includes('<body') ||
    // 表单元素
    code.includes('<form') || code.includes('</form>') || 
    code.includes('<input') || code.includes('<button') || 
    code.includes('<select') || code.includes('<option') ||
    code.includes('<textarea') || code.includes('<label') ||
    // 表单属性
    code.includes('type="text"') || code.includes('type="password"') || 
    code.includes('type="submit"') || code.includes('name="') ||
    code.includes('method="post"') || code.includes('action="') || 
    code.includes('required') || code.includes('value="') ||
    // 常见HTML元素
    code.includes('<div') || code.includes('</div>') || 
    code.includes('<span') || code.includes('</span>') || 
    code.includes('<p>') || code.includes('</p>') ||
    code.includes('<h1>') || code.includes('<h2>') ||
    code.includes('<ul>') || code.includes('<li>') ||
    code.includes('<br>') || code.includes('<br/>')
  ) {
    return 'html';
  }
  
  // 使用正则表达式匹配HTML标签模式
  if (/<[a-z][a-z0-9]*(\s+[a-z0-9-]+(=["'][^"']*["'])?)*\s*>/i.test(code)) {
    return 'html';
  }
  
  // 登录和注册表单的专门检测
  if ((code.toLowerCase().includes('login') || 
       code.toLowerCase().includes('登录') || 
       code.toLowerCase().includes('注册') || 
       code.toLowerCase().includes('sign')) && 
       (code.includes('<') && code.includes('>'))) {
    return 'html';
  }
  
  // 检查是否是mermaid图表
  if (code.trim().startsWith('graph ') || 
      code.trim().startsWith('sequenceDiagram') || 
      code.trim().startsWith('classDiagram') || 
      code.trim().startsWith('flowchart') ||
      code.trim().match(/^flowchart\s+TD/) ||
      code.trim().match(/^flowchart\s+LR/)) {
    return 'mermaid';
  }
  
  // 其他语言检测
  if (code.includes('def ') || code.includes('import ') || code.includes('print(')) {
    return 'python';
  } else if (code.includes('function ') || code.includes('const ') || code.includes('var ') || code.includes('let ') || code.includes('=>')) {
    return 'javascript';
  } else if (code.match(/[{};]\s*$/m) && (code.includes('margin:') || code.includes('padding:') || code.includes('#') && code.includes('{'))) {
    return 'css';
  } else if (code.includes('class ') && code.includes('{')) {
    if (code.includes('public static void main')) {
      return 'java';
    } else {
      return 'java';
    }
  } else if (code.includes('#include')) {
    return 'cpp';
  } else if (code.includes('<template') || code.includes('export default') || code.includes('Vue.')) {
    return 'vue';
  }
  
  // 如果是Web相关内容，更偏向于使用HTML
  if (code.toLowerCase().includes('web') || code.includes('<') && code.includes('>')) {
    return 'html';
  }
  
  // 尝试使用highlight.js自动检测
  try {
    const result = hljs.highlightAuto(code);
    return result.language || 'text';
  } catch (error) {
    console.error('语言自动检测失败:', error);
  }
  
  return 'text';
};

// 检测代码块中是否包含mermaid图表，移动到服务中供全局使用
export const isMermaidContent = (code: string): boolean => {
  const trimmedCode = code.trim();
  
  // 检查常见的mermaid语法开头
  if (trimmedCode.startsWith('graph ') || 
      trimmedCode.startsWith('flowchart ') || 
      trimmedCode.startsWith('sequenceDiagram') || 
      trimmedCode.startsWith('classDiagram') || 
      trimmedCode.startsWith('stateDiagram') || 
      trimmedCode.startsWith('erDiagram') || 
      trimmedCode.startsWith('gantt') || 
      trimmedCode.startsWith('pie') ||
      trimmedCode.startsWith('gitGraph') ||
      trimmedCode.startsWith('journey')) {
    return true;
  }
  
  // 检查是否包含箭头语法，这是mermaid图表的常见特征
  if (trimmedCode.includes('-->') || 
      trimmedCode.includes('->') || 
      /[A-Z][0-9]*\s*-+>\s*[A-Z][0-9]*/i.test(trimmedCode)) {
    
    // 进一步验证：确保不仅仅是带有箭头的普通文本
    const lines = trimmedCode.split('\n');
    const nonEmptyLines = lines.filter(line => line.trim().length > 0);
    
    // 如果大多数非空行都包含箭头或节点定义，可能是mermaid
    const mermaidSyntaxLines = nonEmptyLines.filter(line => 
      line.includes('->') || 
      line.includes('-->') || 
      /[A-Z][0-9]*\s*\[.*\]/i.test(line) || 
      /[A-Z][0-9]*\s*\(.*\)/i.test(line) ||
      /[A-Z][0-9]*\s*{.*}/i.test(line)
    );
    
    return mermaidSyntaxLines.length > 0 && mermaidSyntaxLines.length >= nonEmptyLines.length * 0.3;
  }
  
  return false;
};

// 处理代码块内容检测，自动标识mermaid等特殊内容
export const processCodeBlocks = (content: string): string => {
  // 修改正则表达式，支持多种Markdown风格的代码块格式
  // 匹配两种类型的代码块：
  // 1. ```language code ```
  // 2. ```code``` (无语言指定)
  return content.replace(/```(?:(\w+)\n)?([\s\S]+?)```/g, (match, language, code) => {
    // 检测是否是Mermaid图表
    if (language === 'mermaid' || (!language && isMermaidContent(code))) {
      const mermaidId = `mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
      // 直接返回mermaid元素
      return `<div class="mermaid-block"><div id="${mermaidId}" class="mermaid">${code.trim()}</div></div>`;
    }
    
    // 检测是否是思维导图内容
    if ((language === 'markdown' || language === 'md') && isMindMapContent(code)) {
      // 对思维导图内容进行编码，以便后续处理
      const encodedContent = encodeURIComponent(code);
      return `<div class="markmap-content" data-content="${encodedContent}"></div>`;
    }
    
    // 对于普通代码块，如果没有指定语言，尝试检测
    if (!language) {
      // 简单语言检测
      language = detectCodeLanguage(code);
    }
    
    // 标准代码块渲染
    return `<pre><code class="language-${language || 'text'}">${code}</code></pre>`;
  });
};

// 创建一个自定义renderer
const renderer = new marked.Renderer();

// 使用任意类型临时解决类型问题
// @ts-ignore - 忽略类型检查以解决marked版本兼容性问题
renderer.code = function(code, lang, escaped) {
  // 获取语言显示名称
  const displayLang = lang || 'text';
  
  // 特殊处理mermaid图表
  if (lang === 'mermaid') {
    // 创建mermaid类的pre元素，让浏览器直接渲染
    const mermaidId = `mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    // 确保保存原始内容以便后续错误恢复
    return `<pre class="mermaid-block"><div id="${mermaidId}" class="mermaid" data-original-content="${encodeURIComponent(code)}">${code}</div></pre>`;
  }
  
  // 检查代码内容是否可能是mermaid图表，即使没有明确标记语言
  if ((!lang || lang === 'text') && isMermaidContent(code)) {
    // 如果内容特征符合mermaid图表，但没有标记为mermaid，也特殊处理
    const mermaidId = `mermaid-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
    return `<pre class="mermaid-block"><div id="${mermaidId}" class="mermaid" data-original-content="${encodeURIComponent(code)}">${code}</div></pre>`;
  }
  
  // 对于普通代码块，使用默认渲染
  return `<pre><code class="language-${displayLang}">${code}</code></pre>`;
};

// 配置marked选项
marked.use({
  renderer: renderer,
  breaks: true,      // 将换行符转换为<br>
  gfm: true,         // 启用GitHub风格Markdown
});

// 处理Markdown，转换为HTML
export const markdownToHtml = (markdown: string): string => {
  if (!markdown) return '';
  
  try {
    // 1. 处理代码块
    const processedMarkdown = processCodeBlocks(markdown);
    
    // 2. 移除多余的空行
    const cleanMarkdown = processedMarkdown.replace(/\n{3,}/g, '\n\n');
    
    // 3. 将Markdown转换为HTML
    const htmlContent = marked.parse(cleanMarkdown);
    
    // 确保内容是string类型
    if (typeof htmlContent !== 'string') {
      throw new Error('Markdown解析结果不是字符串');
    }
    
    // 4. 安全处理防止XSS攻击
    return DOMPurify.sanitize(htmlContent, {
      ADD_ATTR: ['class', 'data-language', 'id'], // 允许自定义属性
      ADD_TAGS: ['code', 'pre', 'div', 'svg'] // 确保代码标签和SVG元素保留
    });
  } catch (error) {
    console.error('Markdown渲染失败:', error);
    // 如果渲染失败，回退到简单的文本处理
    return markdown.replace(/\n/g, '<br>');
  }
};

// 格式化消息内容，处理Markdown和代码块
export const formatMessageContent = (content: string): string => {
  // 预处理内容
  let processedContent = content;
  
  // 处理@Web指令的特殊情况
  if (processedContent.includes('@Web')) {
    processedContent = processedContent.replace(/@Web\s+```(?:\w*\n)?([\s\S]+?)```/g, (_match, code) => {
      return `@Web \`\`\`html\n${code}\`\`\``;
    });
  }
  
  // 处理代码块前后的空行问题
  processedContent = processedContent.replace(/\n+```/g, '\n```'); // 代码块前的多余空行
  processedContent = processedContent.replace(/```\n+/g, '```\n'); // 代码块后的多余空行
  processedContent = processedContent.replace(/\n```\n/g, '\n```\n\n'); // 单独一行的代码块标记前后紧凑处理
  processedContent = processedContent.replace(/```\n\n\n```/g, '```\n\n```'); // 处理连续代码块间的多余空行
  processedContent = processedContent.replace(/```\n(?!\n)/g, '```\n\n'); // 代码块后如果没有空行，添加一个空行
  
  // 转换为HTML
  return markdownToHtml(processedContent);
};

// 定义消息类型接口
interface Message {
  role: string;
  content: string;
  [key: string]: any;
}

// 格式化消息列表为HTML
export const formatMessagesToHtml = (messages: Message[], title?: string): string => {
  if (!messages || messages.length === 0) return '<p>没有会话内容</p>';
  
  // 标题部分（如果需要）
  const titleHtml = title ? `<h1>${title}</h1>` : '';
  
  // 将每条消息转换为Markdown渲染后的HTML
  const messageParagraphs = messages.map(msg => {
    const isUserMessage = msg.role === 'user';
    
    // 对内容进行预处理 - 去除换行符和空格
    let cleanContent = msg.content.trim();
    
    // 格式化内容
    const formattedContent = formatMessageContent(cleanContent);
    
    // 用户消息使用普通段落，AI消息使用带样式的div
    if (isUserMessage) {
      return `<div class="history-user-message">${formattedContent}</div>`;
    } else {
      return `<div class="history-agent-message">${formattedContent}</div>`;
    }
  }).join('');
  
  // 连接标题和内容
  return `${titleHtml}<div class="history-messages">${messageParagraphs}</div>`;
}; 