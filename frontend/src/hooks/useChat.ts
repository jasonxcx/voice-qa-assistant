import { useState, useCallback, useRef } from 'react';
import { apiClient, ChatMessage, ChatRequest } from '../services/api.client';

interface UseChatOptions {
  provider?: ChatRequest['provider'];
  model?: string;
}

export function useChat(options: UseChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  
  const sendMessage = useCallback(async (content: string) => {
    const userMessage: ChatMessage = { role: 'user', content };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setIsLoading(true);
    setError(null);
    
    // Add empty assistant message placeholder
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);
    
    abortControllerRef.current = new AbortController();
    
    try {
      const request: ChatRequest = {
        messages: newMessages,
        provider: options.provider || 'openai',
        model: options.model,
      };
      
      // Use streaming
      const generator = apiClient.streamChat(request);
      
      let fullResponse = '';
      
      for await (const token of generator) {
        fullResponse += token;
        
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: 'assistant',
            content: fullResponse,
          };
          return updated;
        });
      }
      
    } catch (err: any) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      
      // Remove empty assistant message on error
      setMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [messages, options]);
  
  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);
  
  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsLoading(false);
  }, []);
  
  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    abort,
  };
}
