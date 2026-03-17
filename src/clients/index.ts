import { BaseLLMClient, ChatMessage, ChatOptions, LLMResponse, StreamChunk } from './base.client';
import { OpenAIClient } from './openai.client';
import { AnthropicClient } from './anthropic.client';
import { QwenClient } from './qwen.client';
import { KimiClient } from './kimi.client';
import { GLMClient } from './glm.client';
import { ERNIEClient } from './ernie.client';

export type LLMProvider = 'openai' | 'anthropic' | 'qwen' | 'kimi' | 'glm' | 'ernie';

export interface ProviderConfig {
  apiKey: string;
  baseUrl?: string;
}

/**
 * Factory for creating LLM clients
 */
export class LLMClientFactory {
  private static clients: Map<LLMProvider, BaseLLMClient> = new Map();
  
  static createClient(provider: LLMProvider, config: ProviderConfig): BaseLLMClient {
    // Return cached client if available
    if (this.clients.has(provider)) {
      return this.clients.get(provider)!;
    }
    
    let client: BaseLLMClient;
    
    switch (provider) {
      case 'openai':
        client = new OpenAIClient(config.apiKey, config.baseUrl);
        break;
      case 'anthropic':
        client = new AnthropicClient(config.apiKey);
        break;
      case 'qwen':
        client = new QwenClient(config.apiKey);
        break;
      case 'kimi':
        client = new KimiClient(config.apiKey);
        break;
      case 'glm':
        client = new GLMClient(config.apiKey);
        break;
      case 'ernie':
        client = new ERNIEClient(config.apiKey);
        break;
      default:
        throw new Error(`Unsupported provider: ${provider}`);
    }
    
    this.clients.set(provider, client);
    return client;
  }
  
  static getClient(provider: LLMProvider): BaseLLMClient | undefined {
    return this.clients.get(provider);
  }
  
  static clearCache(): void {
    this.clients.clear();
  }
}

// Re-export types
export { BaseLLMClient } from './base.client';
export { ChatMessage, ChatOptions, LLMResponse, StreamChunk } from './base.client';
