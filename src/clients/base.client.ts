/**
 * Base LLM Client Interface
 * All provider clients implement this interface
 */

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatOptions {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  systemPrompt?: string;
}

export interface LLMResponse {
  id: string;
  model: string;
  content: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  finishReason?: string;
}

export interface StreamChunk {
  delta: string;
  index: number;
  finishReason?: string;
}

/**
 * Abstract base class for all LLM providers
 */
export abstract class BaseLLMClient {
  protected apiKey: string;
  protected baseUrl?: string;
  
  constructor(apiKey: string, baseUrl?: string) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }
  
  /** Send chat request and get full response */
  abstract chat(messages: ChatMessage[], options?: ChatOptions): Promise<LLMResponse>;
  
  /** Stream chat response as async iterable */
  abstract chatStream(messages: ChatMessage[], options?: ChatOptions): AsyncIterable<StreamChunk>;
  
  /** Get the provider name */
  abstract getProviderName(): string;
}
