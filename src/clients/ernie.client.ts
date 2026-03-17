import erniebot from 'erniebot';
import { BaseLLMClient, ChatMessage, ChatOptions, LLMResponse, StreamChunk } from './base.client';

export class ERNIEClient extends BaseLLMClient {
  constructor(apiKey: string) {
    super(apiKey);
    // Configure ERNIE Bot
    erniebot.apiType = 'aip';
    (erniebot as any)._config = {
      ...(erniebot as any)._config,
      api_key: apiKey,
    };
  }
  
  getProviderName(): string {
    return 'ernie';
  }
  
  async chat(messages: ChatMessage[], options: ChatOptions = {}): Promise<LLMResponse> {
    const systemPrompt = options.systemPrompt || '';
    const filteredMessages = messages.filter(m => m.role !== 'system');
    
    const response = await (erniebot as any).ChatCompletion.create({
      model: options.model || 'ernie-4.0-8k',
      messages: [
        { role: 'system', content: systemPrompt },
        ...filteredMessages.map(m => ({ role: m.role, content: m.content })),
      ],
      temperature: options.temperature ?? 0.7,
      max_output_tokens: options.maxTokens ?? 4096,
    });
    
    return this.mapResponse(response);
  }
  
  async *chatStream(messages: ChatMessage[], options: ChatOptions = {}): AsyncIterable<StreamChunk> {
    const systemPrompt = options.systemPrompt || '';
    const filteredMessages = messages.filter(m => m.role !== 'system');
    
    const stream = await (erniebot as any).ChatCompletion.create({
      model: options.model || 'ernie-4.0-8k',
      messages: [
        { role: 'system', content: systemPrompt },
        ...filteredMessages.map(m => ({ role: m.role, content: m.content })),
      ],
      temperature: options.temperature ?? 0.7,
      max_output_tokens: options.maxTokens ?? 4096,
      stream: true,
    });
    
    let index = 0;
    for await (const chunk of stream) {
      const delta = chunk.result || '';
      if (delta) {
        yield { delta, index: index++ };
      }
    }
  }
  
  private mapResponse(response: any): LLMResponse {
    return {
      id: response.id || '',
      model: response.model || 'ernie',
      content: response.result || '',
      finishReason: 'stop',
    };
  }
}
