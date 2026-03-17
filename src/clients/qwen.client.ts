import OpenAI from 'openai';
import { BaseLLMClient, ChatMessage, ChatOptions, LLMResponse, StreamChunk } from './base.client';

export class QwenClient extends BaseLLMClient {
  private client: OpenAI;
  
  constructor(apiKey: string) {
    super(apiKey);
    // Qwen uses DashScope - OpenAI compatible endpoint
    this.client = new OpenAI({
      apiKey,
      baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
      maxRetries: 3,
      timeout: 120000,
    });
  }
  
  getProviderName(): string {
    return 'qwen';
  }
  
  async chat(messages: ChatMessage[], options: ChatOptions = {}): Promise<LLMResponse> {
    const response = await this.client.chat.completions.create({
      model: options.model || 'qwen-plus',
      messages: this.mapMessages(messages, options.systemPrompt),
      temperature: options.temperature ?? 0.7,
      max_tokens: options.maxTokens ?? 4096,
    });
    
    return this.mapResponse(response);
  }
  
  async *chatStream(messages: ChatMessage[], options: ChatOptions = {}): AsyncIterable<StreamChunk> {
    const stream = await this.client.chat.completions.create({
      model: options.model || 'qwen-plus',
      messages: this.mapMessages(messages, options.systemPrompt),
      temperature: options.temperature ?? 0.7,
      max_tokens: options.maxTokens ?? 4096,
      stream: true,
    });
    
    let index = 0;
    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content || '';
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
    const choice = response.choices[0];
    return {
      id: response.id,
      model: response.model,
      content: choice.message.content || '',
      usage: response.usage,
      finishReason: choice.finish_reason,
    };
  }
}
