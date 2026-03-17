import { ZhipuAI } from 'zhipuai-sdk-nodejs-v4';
import { BaseLLMClient, ChatMessage, ChatOptions, LLMResponse, StreamChunk } from './base.client';

export class GLMClient extends BaseLLMClient {
  private client: ZhipuAI;
  
  constructor(apiKey: string) {
    super(apiKey);
    this.client = new ZhipuAI({ apiKey });
  }
  
  getProviderName(): string {
    return 'glm';
  }
  
  async chat(messages: ChatMessage[], options: ChatOptions = {}): Promise<LLMResponse> {
    const response = await this.client.chatCompletions({
      model: options.model || 'glm-4',
      messages: this.mapMessages(messages, options.systemPrompt),
      temperature: options.temperature ?? 0.7,
      max_tokens: options.maxTokens ?? 4096,
    });
    
    return this.mapResponse(response);
  }
  
  async *chatStream(messages: ChatMessage[], options: ChatOptions = {}): AsyncIterable<StreamChunk> {
    const stream = await this.client.createCompletions({
      model: options.model || 'glm-4',
      messages: this.mapMessages(messages, options.systemPrompt),
      temperature: options.temperature ?? 0.7,
      max_tokens: options.maxTokens ?? 4096,
      stream: true,
    });
    
    let index = 0;
    for await (const chunk of stream) {
      const delta = chunk.choices?.[0]?.delta?.content || '';
      if (delta) {
        yield { delta, index: index++ };
      }
    }
  }
  
  private mapMessages(messages: ChatMessage[], systemPrompt?: string) {
    const mapped = messages.map(m => ({ role: m.role, content: m.content }));
    if (systemPrompt && mapped[0]?.role !== 'system') {
      mapped.unshift({ role: 'system', content: systemPrompt });
    }
    return mapped;
  }
  
  private mapResponse(response: any): LLMResponse {
    const choice = response.choices?.[0];
    return {
      id: response.id || '',
      model: response.model,
      content: choice?.message?.content || '',
      usage: response.usage,
      finishReason: choice?.finish_reason,
    };
  }
}
