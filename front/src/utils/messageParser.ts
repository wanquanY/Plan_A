// 消息解析工具
export interface TextSegment {
  type: 'text';
  content: string;
  timestamp: string;
}

export interface ReasoningSegment {
  type: 'reasoning';
  content: string;
  timestamp: string;
}

export interface ToolCallSegment {
  type: 'tool_call';
  id: string;
  name: string;
  arguments: any;
  status: 'executing' | 'completed' | 'error';
  result?: any;
  error?: string;
  started_at: string;
  completed_at?: string;
}

export type InteractionSegment = TextSegment | ReasoningSegment | ToolCallSegment;

export interface AgentResponseData {
  type: 'agent_response';
  interaction_flow: InteractionSegment[];
}

/**
 * 解析agent消息内容
 * @param content 消息内容，可能是JSON字符串或普通文本
 * @returns 解析后的数据或原始文本
 */
export function parseAgentMessage(content: string): AgentResponseData | string {
  if (!content) return '';
  
  // 尝试解析JSON
  try {
    const parsed = JSON.parse(content);
    
    // 检查是否是新的agent响应格式
    if (parsed.type === 'agent_response' && parsed.interaction_flow) {
      return parsed as AgentResponseData;
    }
    
    // 如果不是预期格式，返回原始内容
    return content;
  } catch (error) {
    // 如果不是JSON，返回原始文本
    return content;
  }
}

/**
 * 从交互流程中提取纯文本内容
 * @param interactionFlow 交互流程数组
 * @returns 拼接的纯文本内容
 */
export function extractTextFromInteractionFlow(interactionFlow: InteractionSegment[]): string {
  return interactionFlow
    .filter(segment => segment.type === 'text')
    .map(segment => (segment as TextSegment).content)
    .join('');
}

/**
 * 从交互流程中提取思考内容
 * @param interactionFlow 交互流程数组
 * @returns 拼接的思考内容
 */
export function extractReasoningFromInteractionFlow(interactionFlow: InteractionSegment[]): string {
  return interactionFlow
    .filter(segment => segment.type === 'reasoning')
    .map(segment => (segment as ReasoningSegment).content)
    .join('');
}

/**
 * 检查消息是否包含工具调用
 * @param data 解析后的agent响应数据
 * @returns 是否包含工具调用
 */
export function hasToolCalls(data: AgentResponseData): boolean {
  return data.interaction_flow.some(segment => segment.type === 'tool_call');
}

/**
 * 检查消息是否包含思考内容
 * @param data 解析后的agent响应数据
 * @returns 是否包含思考内容
 */
export function hasReasoningContent(data: AgentResponseData): boolean {
  return data.interaction_flow.some(segment => segment.type === 'reasoning');
}

/**
 * 获取工具调用列表
 * @param data 解析后的agent响应数据
 * @returns 工具调用列表
 */
export function getToolCalls(data: AgentResponseData): ToolCallSegment[] {
  return data.interaction_flow.filter(segment => segment.type === 'tool_call') as ToolCallSegment[];
}

/**
 * 获取文本片段列表
 * @param data 解析后的agent响应数据
 * @returns 文本片段列表
 */
export function getTextSegments(data: AgentResponseData): TextSegment[] {
  return data.interaction_flow.filter(segment => segment.type === 'text') as TextSegment[];
}

/**
 * 获取思考片段列表
 * @param data 解析后的agent响应数据
 * @returns 思考片段列表
 */
export function getReasoningSegments(data: AgentResponseData): ReasoningSegment[] {
  return data.interaction_flow.filter(segment => segment.type === 'reasoning') as ReasoningSegment[];
} 