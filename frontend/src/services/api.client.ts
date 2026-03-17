import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  model?: string;
  provider: 'openai' | 'anthropic' | 'qwen' | 'kimi' | 'glm' | 'ernie';
  temperature?: number;
  maxTokens?: number;
}

class APIClient {
  private client = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  });
  
  // Non-streaming chat
  async sendChat(request: ChatRequest): Promise<{ content: string; id: string }> {
    const response = await this.client.post('/api/chat', request);
    return response.data;
  }
  
  // Streaming chat with SSE using fetch
  async *streamChat(request: ChatRequest): AsyncGenerator<string> {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Request failed');
    }
    
    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');
    
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          
          if (data === '[DONE]') {
            return;
          }
          
          try {
            const event = JSON.parse(data);
            
            if (event.event === 'token') {
              yield event.data.text;
            } else if (event.event === 'error') {
              throw new Error(event.data.message);
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
  }
  
  // Get available models
  async getModels() {
    const response = await this.client.get('/api/models');
    return response.data;
  }
}

export const apiClient = new APIClient();
