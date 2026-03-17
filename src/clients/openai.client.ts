import OpenAI from 'openai';
import { BaseLLMClient, ChatMessage, ChatOptions, LLMResponse, StreamChunk } from './base.client';

export class OpenAIClient extends BaseLLMClient {
  private client: OpenAI;
  
  constructor(apiKey: string, baseUrl?: string) {
    super(apiKey, baseUrl);
    this.client = new OpenAI({
      apiKey,
      baseURL: baseUrl,
      maxRetries: 3,
      timeout: 120000,
    });
  }
  
  getProviderName(): string {
    return 'openai';
  }
  
  async chat(messages: ChatMessage[], options: ChatOptions = {}): Promise<LLMResponse> {
    const response = await this.client.chat.completions.create({
      model: options.model || 'gpt-4o',
      messages: this.mapMessages(messages, options.systemPrompt),
      temperature: options.temperature ?? 0.7,
      max_tokens: options.maxTokens ?? 4096,
      top_p: options.topP,
    });
    
    const choice = response.choices[0];
    return {
      id: response.id,
      model: response.model,
      content: choice.message.content || '',
      usage: {
        promptTokens: response.usage?.prompt_tokens || 0,
        completionTokens: response.usage?.completion_tokens || 0,
        totalTokens: response.usage?.total_tokens || 0,
      },
      finishReason: choice.finish_reason,
    };
  }
  
  async *chatStream(messages: ChatMessage[], options: ChatOptions = {}): AsyncIterable<StreamChunk> {
    const stream = await this.client.chat.completions.create({
      model: options.model || 'gpt-4o',
      messages: this.mapMessages(messages, options.systemPrompt),
      temperature: options.temperature ?? 0.7,
      max_tokens: options.maxTokens ?? 4096,
      top_p: options.topP,
      stream: true,
    });
    
    let index = 0;
    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content || '';
      if (delta) {
        yield { delta, index: index++, finishReason: chunk.choices[0]?.finish_reason };
      }
    }
  }
  
  private mapMessages(messages: ChatMessage[], systemPrompt?: string): OpenAI.Chat.ChatMessage[] {
    const mapped: OpenAI.Chat.ChatMessage[] = messages.map(m => ({
      role: m.role,
      content: m.content,
    }));
    
    if (systemPrompt && mapped[0]?.role !== 'system') {
      mapped.unshift({ role: 'system', content: systemPrompt });
    }
    
    return mapped;
  }
}
