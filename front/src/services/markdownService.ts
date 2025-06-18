import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import katex from 'katex';

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

/**
 * 判断是否为LaTeX数学公式
 */
export const isLatexContent = (content: string): boolean => {
  if (!content || typeof content !== 'string') return false;
  
  // 检查是否包含LaTeX数学公式标记
  const latexPatterns = [
    /\$\$[\S\s]*?\$\$/,  // 块级公式
    /\$[^$\n]+\$/,       // 行内公式
    /\\begin\{.*?\}[\S\s]*?\\end\{.*?\}/,  // LaTeX环境
    /\\[a-zA-Z]+/        // LaTeX命令
  ];
  
  return latexPatterns.some(pattern => pattern.test(content));
};

/**
 * 处理LaTeX数学公式
 */
export const processLatexFormulas = (content: string): string => {
  let processedContent = content;
  
  console.log('LaTeX处理前的内容:', content);
  
  // 处理块级公式 $$...$$
  processedContent = processedContent.replace(/\$\$([\s\S]*?)\$\$/g, (match, formula) => {
    const cleanFormula = formula.trim();
    if (cleanFormula) {
      const result = `<div class="latex-block" data-latex="${encodeURIComponent(cleanFormula)}" data-display="true"></div>`;
      console.log('处理块级公式:', cleanFormula, '→', result);
      return result;
    }
    return match;
  });
  
  // 处理行内公式 $...$（简化版本，更宽泛的匹配）
  processedContent = processedContent.replace(/\$([^$\r\n]+?)\$/g, (match, formula) => {
    const cleanFormula = formula.trim();
    if (cleanFormula && !cleanFormula.includes('$$')) {
      const result = `<span class="latex-inline" data-latex="${encodeURIComponent(cleanFormula)}" data-display="false"></span>`;
      console.log('处理行内公式:', cleanFormula, '→', result);
      return result;
    }
    return match;
  });
  
  console.log('LaTeX处理后的内容:', processedContent);
  return processedContent;
};

/**
 * 判断文本内容是否是思维导图格式
 * 思维导图格式通常是# 开头，带有缩进层级的markdown
 * 优化版本：更高效地识别，减少不必要的计算
 */
export const isMindMapContent = (content: string): boolean => {
  if (!content || typeof content !== 'string') return false;
  
  // 清理内容，去除前后空白
  const text = content.trim();
  
  // 快速检查：必须以"# "开头
  if (!text.startsWith('# ')) return false;
  
  // 快速检查：检查是否有多级标题
  if (!text.includes('\n##')) return false;
  
  // 计算标题行的数量
  const headingLines = text.match(/^#+\s/gm);
  if (!headingLines || headingLines.length < 3) return false;  // 至少需要3个标题
  
  // 判断是否有至少两个不同级别的标题
  let hasFirstLevel = false;
  let hasSecondLevel = false;
  
  for (let i = 0; i < headingLines.length; i++) {
    if (headingLines[i].startsWith('# ')) {
      hasFirstLevel = true;
    } else if (headingLines[i].startsWith('## ')) {
      hasSecondLevel = true;
    }
    
    // 如果同时有一级和二级标题，提前返回true
    if (hasFirstLevel && hasSecondLevel) {
      return true;
    }
  }
  
  return false;
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
      // 在历史会话中保持与新建会话相同的格式：保留代码块格式
      return `<pre data-mermaid-processed="true"><code class="language-mermaid">${code.trim()}</code></pre>`;
    }
    
    // 检测是否是思维导图内容
    if ((language === 'markdown' || language === 'md' || language === 'markmap') && (language === 'markmap' || isMindMapContent(code))) {
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
    // 使用与新建会话相同的格式：保留pre和code标签
    return `<pre data-mermaid-processed="true"><code class="language-mermaid">${code}</code></pre>`;
  }
  
  // 特殊处理markmap思维导图
  if (lang === 'markmap') {
    // 对于markmap，直接创建pre和code标签，后续由渲染服务处理
    return `<pre data-markmap-processed="true"><code class="language-markmap">${code}</code></pre>`;
  }
  
  // 检查代码内容是否可能是mermaid图表，即使没有明确标记语言
  if ((!lang || lang === 'text') && isMermaidContent(code)) {
    // 如果内容特征符合mermaid图表，但没有标记为mermaid，也使用统一格式
    return `<pre data-mermaid-processed="true"><code class="language-mermaid">${code}</code></pre>`;
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
    // 1. 处理LaTeX数学公式
    const latexProcessed = processLatexFormulas(markdown);
    
    // 2. 处理代码块
    const processedMarkdown = processCodeBlocks(latexProcessed);
    
    // 3. 移除多余的空行
    const cleanMarkdown = processedMarkdown.replace(/\n{3,}/g, '\n\n');
    
    // 4. 将Markdown转换为HTML
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

// 实时流式渲染优化的markdown处理器
export const renderRealtimeMarkdown = (markdown: string, isTyping = false): string => {
  if (!markdown) return '';
  
  try {
    // 如果正在流式输出且内容较短，进行快速渲染
    if (isTyping && markdown.length < 1000) {
      return renderQuickMarkdown(markdown);
    }
    
    // 对于较长内容或完成的内容，使用完整渲染
    return markdownToHtml(markdown);
  } catch (error) {
    console.error('实时Markdown渲染失败:', error);
    return markdown.replace(/\n/g, '<br>');
  }
};

// 快速markdown渲染器，专门用于流式输出
const renderQuickMarkdown = (markdown: string): string => {
  if (!markdown) return '';
  
  let processed = markdown;
  
  // 1. 处理标题 (只处理完整的行)
  processed = processed.replace(/^(#{1,6})\s+(.+)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    return `<h${level}>${content.trim()}</h${level}>`;
  });
  
  // 2. 处理粗体（只处理完整的**文本**）
  processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // 3. 处理斜体（只处理完整的*文本*）
  processed = processed.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>');
  
  // 4. 处理行内代码（只处理完整的`代码`）
  processed = processed.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // 5. 处理链接（只处理完整的[文本](链接)）
  processed = processed.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  
  // 6. 处理列表项（只处理完整的行）
  processed = processed.replace(/^[-*+]\s+(.+)$/gm, '<li>$1</li>');
  
  // 7. 处理有序列表（只处理完整的行）
  processed = processed.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');
  
  // 8. 包装连续的列表项
  processed = processed.replace(/(<li>.*<\/li>[\s]*)+/g, (match) => {
    // 检查是否已经在ul标签内
    if (match.includes('<ul>') || match.includes('</ul>')) {
      return match; // 已经包装了，不再处理
    }
    return `<ul>${match}</ul>`;
  });
  
  // 9. 处理段落（将连续的非HTML行包装在p标签中）
  const lines = processed.split('\n');
  const processedLines: string[] = [];
  let currentParagraph: string[] = [];
  
  lines.forEach(line => {
    const trimmedLine = line.trim();
    
    // 如果是HTML标签开头或空行
    if (trimmedLine.startsWith('<') || trimmedLine === '') {
      // 如果有累积的段落，先处理
      if (currentParagraph.length > 0) {
        const paragraphContent = currentParagraph.join(' ').trim();
        if (paragraphContent) {
          processedLines.push(`<p>${paragraphContent}</p>`);
        }
        currentParagraph = [];
      }
      
      // 添加当前行（如果不是空行）
      if (trimmedLine) {
        processedLines.push(trimmedLine);
      }
    } else {
      // 累积段落内容
      currentParagraph.push(trimmedLine);
    }
  });
  
  // 处理最后的段落
  if (currentParagraph.length > 0) {
    const paragraphContent = currentParagraph.join(' ').trim();
    if (paragraphContent) {
      processedLines.push(`<p>${paragraphContent}</p>`);
    }
  }
  
  // 10. 处理换行
  const finalResult = processedLines.join('\n').replace(/\n/g, '<br>');
  
  // 清理多余的br标签
  return finalResult
    .replace(/<\/p><br>/g, '</p>')
    .replace(/<br><p>/g, '<p>')
    .replace(/<\/h[1-6]><br>/g, (match) => match.replace('<br>', ''))
    .replace(/<br><h[1-6]>/g, (match) => match.replace('<br>', ''));
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
    
    // 如果是agent消息，尝试解析JSON结构
    if (!isUserMessage) {
      try {
        const parsed = JSON.parse(cleanContent);
        
        // 检查是否是新的agent响应格式
        if (parsed.type === 'agent_response' && parsed.interaction_flow) {
          // 提取纯文本内容用于显示
          cleanContent = parsed.interaction_flow
            .filter((segment: any) => segment.type === 'text')
            .map((segment: any) => segment.content)
            .join('');
        }
      } catch (error) {
        // 如果不是JSON，使用原始内容
      }
    }
    
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