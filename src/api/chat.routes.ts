import express, { Request, Response } from 'express';
import { LLMClientFactory, ChatMessage, LLMProvider } from '../clients';
import { SSEManager } from '../utils/sse';
import { RedisCacheService } from '../cache/redis.cache';

const router = express.Router();
const cacheService = new RedisCacheService();

// POST /api/chat/stream - Streaming chat endpoint
router.post('/chat/stream', async (req: Request, res: Response) => {
  const {
    messages,
    model,
    provider,
    temperature,
    maxTokens,
  } = req.body;
  
  // Validate request
  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    return res.status(400).json({ error: 'Messages array is required' });
  }
  
  if (!provider) {
    return res.status(400).json({ error: 'Provider is required' });
  }
  
  // Initialize SSE
  const sse = new SSEManager(res);
  
  // Handle client disconnect
  sse.onAborted(() => {
    console.log('Client disconnected from stream');
  });
  
  try {
    // Get API key from header or environment
    const apiKey = getAPIKey(provider, req.headers['x-api-key'] as string);
    if (!apiKey) {
      return res.status(401).json({ error: 'API key not configured' });
    }
    
    // Get LLM client
    const client = LLMClientFactory.createClient(provider as LLMProvider, { apiKey });
    
    // Check cache first
    const cacheKey = cacheService.generateKey({
      messages,
      model,
      provider,
    });
    
    const cached = await cacheService.get(cacheKey);
    if (cached) {
      console.log('Returning cached response');
      for (const token of cached.tokens) {
        sse.sendToken(token);
        await delay(20);
      }
      sse.sendComplete(cached.usage);
      return;
    }
    
    // Stream response
    const tokens: string[] = [];
    let usage: any;
    
    for await (const chunk of client.chatStream(messages, {
      model,
      temperature,
      maxTokens,
    })) {
      tokens.push(chunk.delta);
      sse.sendToken(chunk.delta);
      
      if (chunk.finishReason) {
        sse.sendComplete(usage);
      }
    }
    
    // Cache the response
    await cacheService.set(cacheKey, { tokens, usage });
    
  } catch (error: any) {
    console.error('Chat error:', error);
    sse.sendError(error.message || 'Internal server error');
  }
});

// POST /api/chat - Non-streaming chat endpoint
router.post('/chat', async (req: Request, res: Response) => {
  const { messages, model, provider, temperature, maxTokens } = req.body;
  
  if (!messages || !provider) {
    return res.status(400).json({ error: 'Messages and provider are required' });
  }
  
  try {
    const apiKey = getAPIKey(provider, req.headers['x-api-key'] as string);
    if (!apiKey) {
      return res.status(401).json({ error: 'API key not configured' });
    }
    
    const client = LLMClientFactory.createClient(provider as LLMProvider, { apiKey });
    const response = await client.chat(messages, { model, temperature, maxTokens });
    
    res.json(response);
  } catch (error: any) {
    console.error('Chat error:', error);
    res.status(500).json({ error: error.message });
  }
});

function getAPIKey(provider: string, headerKey?: string): string | undefined {
  if (headerKey) return headerKey;
  
  const envVars: Record<string, string> = {
    openai: process.env.OPENAI_API_KEY || '',
    anthropic: process.env.ANTHROPIC_API_KEY || '',
    qwen: process.env.DASHSCOPE_API_KEY || '',
    kimi: process.env.KIMI_API_KEY || '',
    glm: process.env.ZHIPU_API_KEY || '',
    ernie: process.env.ERNIE_API_KEY || '',
  };
  
  return envVars[provider];
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export default router;
