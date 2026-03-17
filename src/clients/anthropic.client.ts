import Anthropic from '@anthropic-ai/sdk';
import { BaseLLMClient, ChatMessage, ChatOptions, LLMResponse, StreamChunk } from './base.client';

export class AnthropicClient extends BaseLLMClient {
  private client: Anthropic;
  
  constructor(apiKey: string) {
    super(apiKey);
    this.client = new Anthropic({
      apiKey,
      maxRetries: 3,
      timeout: 120000,
    });
  }
  
  getProviderName(): string {
    return 'anthropic';
  }
  
  async chat(messages: ChatMessage[], options: ChatOptions = {}): Promise<LLMResponse> {
    const systemPrompt = options.systemPrompt || '';
    const filteredMessages = messages.filter(m => m.role !== 'system');
    
    const response = await this.client.messages.create({
      model: options.model || 'claude-sonnet-4-20250514',
      max_tokens: options.maxTokens ?? 4096,
      temperature: options.temperature ?? 0.7,
      system: systemPrompt,
      messages: filteredMessages.map(m => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      })),
    });
    
    const content = response.content[0];
    return {
      id: response.id,
      model: response.model,
      content: content.type === 'text' ? content.text : '',
      usage: {
        promptTokens: response.usage.input_tokens,
        completionTokens: response.usage.output_tokens,
        totalTokens: response.usage.input_tokens + response.usage.output_tokens,
      },
      finishReason: response.stop_reason || undefined,
    };
  }
  
  async *chatStream(messages: ChatMessage[], options: ChatOptions = {}): AsyncIterable<StreamChunk> {
    const systemPrompt = options.systemPrompt || '';
    const filteredMessages = messages.filter(m => m.role !== 'system');
    
    const stream = await this.client.messages.stream({
      model: options.model || 'claude-sonnet-4-20250514',
      max_tokens: options.maxTokens ?? 4096,
      temperature: options.temperature ?? 0.7,
      system: systemPrompt,
      messages: filteredMessages.map(m => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      })),
    });
    
    let index = 0;
    for await (const chunk of stream) {
      if (chunk.type === 'content_block_delta' && chunk.delta.type === 'text_delta') {
        yield {
          delta: chunk.delta.text,
          index: index++,
        };
      } else if (chunk.type === 'message_stop') {
        yield {
          delta: '',
          index: index,
          finishReason: 'stop',
        };
      }
    }
  }
}
