# LLM API Integration Design for Interview Helper

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an interview helper that analyzes resumes and answers interview questions using multiple LLM providers with streaming output and context-aware responses.

**Architecture:** 
- Multi-provider LLM client layer supporting OpenAI, Claude, Qwen, ERNIE, GLM, Kimi
- Resume context injection via system prompt and RAG approaches
- SSE-based streaming output for real-time response display
- Caching layer for latency optimization

**Tech Stack:** TypeScript/Node.js, FastAPI (Python backend option), FAISS for RAG

---
## 1. LLM API Client Architecture

### 1.1 API Client Interface

**Files:**
- Create: `src/api/client.ts`
- Create: `src/api/types.ts`

```typescript
// src/api/types.ts
export interface LLMMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface LLMResponse {
  content: string;
  model: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
  };
}

export interface LLMClient {
  generate(messages: LLMMessage[], options?: GenerateOptions): Promise<LLMResponse>;
  generateStream(messages: LLMMessage[], options?: GenerateOptions): AsyncGenerator<string>;
  getSupportedModels(): string[];
}
```

### 1.2 OpenAI Client Implementation

**Files:**
- Create: `src/api/openai.ts`

```typescript
import { OpenAI } from 'openai';
import { LLMClient, LLMMessage, LLMResponse } from './types';

export class OpenAIClient implements LLMClient {
  private client: OpenAI;
  private model: string;

  constructor(apiKey: string, model: string = 'gpt-4o-mini') {
    this.client = new OpenAI({ apiKey });
    this.model = model;
  }

  async generate(messages: LLMMessage[]): Promise<LLMResponse> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
    });
    return {
      content: response.choices[0].message.content || '',
      model: this.model,
      usage: {
        prompt_tokens: response.usage?.prompt_tokens || 0,
        completion_tokens: response.usage?.completion_tokens || 0,
      },
    };
  }

  async *generateStream(messages: LLMMessage[]): AsyncGenerator<string> {
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages,
      stream: true,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      if (content) {
        yield content;
      }
    }
  }

  getSupportedModels(): string[] {
    return ['gpt-5', 'o3', 'gpt-4o', 'gpt-4o-mini'];
  }
}
```

### 1.3 Claude Client Implementation

**Files:**
- Create: `src/api/claude.ts`

```typescript
import { Anthropic } from '@anthropic-ai/sdk';
import { LLMClient, LLMMessage, LLMResponse } from './types';

export class ClaudeClient implements LLMClient {
  private client: Anthropic;
  private model: string;

  constructor(apiKey: string, model: string = 'claude-3-5-sonnet-20240620') {
    this.client = new Anthropic({ apiKey });
    this.model = model;
  }

  async generate(messages: LLMMessage[]): Promise<LLMResponse> {
    const userMessages = messages.filter(m => m.role === 'user');
    const systemMessage = messages.find(m => m.role === 'system');

    const response = await this.client.messages.create({
      model: this.model,
      max_tokens: 1024,
      system: systemMessage?.content,
      messages: userMessages.map(m => ({ role: m.role, content: m.content })),
    });

    return {
      content: response.content[0].text,
      model: this.model,
      usage: {
        prompt_tokens: response.usage.input_tokens || 0,
        completion_tokens: response.usage.output_tokens || 0,
      },
    };
  }

  async *generateStream(messages: LLMMessage[]): AsyncGenerator<string> {
    const userMessages = messages.filter(m => m.role === 'user');
    const systemMessage = messages.find(m => m.role === 'system');

    const stream = await this.client.messages.stream({
      model: this.model,
      max_tokens: 1024,
      system: systemMessage?.content,
      messages: userMessages.map(m => ({ role: m.role, content: m.content })),
    });

    for await (const event of stream) {
      if (event.type === 'content_block_delta') {
        yield event.delta.text;
      }
    }
  }

  getSupportedModels(): string[] {
    return ['claude-3-5-sonnet-20240620', 'claude-3-haiku-20240307'];
  }
}
```

### 1.4 Qwen Client Implementation

**Files:**
- Create: `src/api/qwen.ts`

```typescript
import { OpenAI } from 'openai';
import { LLMClient, LLMMessage, LLMResponse } from './types';

export class QwenClient implements LLMClient {
  private client: OpenAI;
  private model: string;

  constructor(apiKey: string, model: string = 'qwen-max') {
    this.client = new OpenAI({
      apiKey,
      baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    });
    this.model = model;
  }

  async generate(messages: LLMMessage[]): Promise<LLMResponse> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
    });
    return {
      content: response.choices[0].message.content || '',
      model: this.model,
    };
  }

  async *generateStream(messages: LLMMessage[]): AsyncGenerator<string> {
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages,
      stream: true,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      if (content) {
        yield content;
      }
    }
  }

  getSupportedModels(): string[] {
    return ['qwen-max', 'qwen-plus', 'qwen-turbo'];
  }
}
```

### 1.5 ERNIE Client Implementation

**Files:**
- Create: `src/api/ernie.ts`

```typescript
import axios from 'axios';
import { LLMClient, LLMMessage, LLMResponse } from './types';

export class ErnieClient implements LLMClient {
  private apiKey: string;
  private secretKey: string;
  private model: string;
  private accessToken: string | null = null;

  constructor(apiKey: string, secretKey: string, model: string = 'ernie-4.5-turbo') {
    this.apiKey = apiKey;
    this.secretKey = secretKey;
    this.model = model;
  }

  private async getAccessToken(): Promise<string> {
    if (this.accessToken) return this.accessToken;
    
    const response = await axios.post(
      'https://aip.baidubce.com/oauth/2.0/token',
      null,
      {
        params: {
          grant_type: 'client_credentials',
          client_id: this.apiKey,
          client_secret: this.secretKey,
        },
      }
    );
    
    this.accessToken = response.data.access_token;
    return this.accessToken;
  }

  async generate(messages: LLMMessage[]): Promise<LLMResponse> {
    const accessToken = await this.getAccessToken();
    const userMessages = messages.filter(m => m.role !== 'system');
    
    const response = await axios.post(
      `https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token=${accessToken}`,
      {
        messages: userMessages,
        stream: false,
      }
    );

    return {
      content: response.data.result || '',
      model: this.model,
    };
  }

  async *generateStream(messages: LLMMessage[]): AsyncGenerator<string> {
    const accessToken = await this.getAccessToken();
    const userMessages = messages.filter(m => m.role !== 'system');

    const response = await axios.post(
      `https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token=${accessToken}`,
      {
        messages: userMessages,
        stream: true,
      },
      { responseType: 'stream' }
    );

    for await (const chunk of response.data) {
      const chunkStr = chunk.toString();
      if (chunkStr.startsWith('data: ')) {
        try {
          const data = JSON.parse(chunkStr.slice(6));
          yield data.result || '';
        } catch (e) {}
      }
    }
  }

  getSupportedModels(): string[] {
    return ['ernie-4.5-turbo', 'ernie-4.0', 'ernie-3.5'];
  }
}
```

### 1.6 GLM Client Implementation

**Files:**
- Create: `src/api/glm.ts`

```typescript
import { ZhipuAI } from 'zhipuai';
import { LLMClient, LLMMessage, LLMResponse } from './types';

export class GLMClient implements LLMClient {
  private client: ZhipuAI;
  private model: string;

  constructor(apiKey: string, model: string = 'glm-4') {
    this.client = new ZhipuAI({ apiKey });
    this.model = model;
  }

  async generate(messages: LLMMessage[]): Promise<LLMResponse> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
    });
    return {
      content: response.choices[0].message.content || '',
      model: this.model,
    };
  }

  async *generateStream(messages: LLMMessage[]): AsyncGenerator<string> {
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages,
      stream: true,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      if (content) {
        yield content;
      }
    }
  }

  getSupportedModels(): string[] {
    return ['glm-4', 'glm-4.7', 'glm-4.5', 'glm-3-turbo'];
  }
}
```

### 1.7 Kimi Client Implementation

**Files:**
- Create: `src/api/kimi.ts`

```typescript
import { OpenAI } from 'openai';
import { LLMClient, LLMMessage, LLMResponse } from './types';

export class KimiClient implements LLMClient {
  private client: OpenAI;
  private model: string;

  constructor(apiKey: string, model: string = 'kimi-k2-turbo-preview') {
    this.client = new OpenAI({
      apiKey,
      baseURL: 'https://api.moonshot.ai/v1',
    });
    this.model = model;
  }

  async generate(messages: LLMMessage[]): Promise<LLMResponse> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
    });
    return {
      content: response.choices[0].message.content || '',
      model: this.model,
    };
  }

  async *generateStream(messages: LLMMessage[]): AsyncGenerator<string> {
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages,
      stream: true,
    });

    for await (const chunk of stream) {
      const content = chunk.choices[0]?.delta?.content || '';
      if (content) {
        yield content;
      }
    }
  }

  getSupportedModels(): string[] {
    return ['kimi-k2-turbo-preview', 'kimi-k2-preview', 'kimi-k2.5'];
  }
}
```

---

## 2. Resume Context Injection

### 2.1 Direct Context Injection

**Files:**
- Create: `src/context/direct.ts`

```typescript
import { LLMMessage } from '../api/types';

export interface ResumeContext {
  name: string;
  email: string;
  phone: string;
  summary: string;
  experience: Array<{
    company: string;
    title: string;
    duration: string;
    responsibilities: string[];
    achievements: string[];
  }>;
  education: Array<{
    school: string;
    degree: string;
    duration: string;
    gpa?: string;
  }>;
  skills: string[];
  projects: Array<{
    name: string;
    description: string;
    technologies: string[];
    results: string[];
  }>;
}

export function buildResumeContext(resume: ResumeContext): string {
  let context = `# Resume Context\n\n`;
  
  context += `## Personal Information\n`;
  context += `- Name: ${resume.name}\n`;
  context += `- Email: ${resume.email}\n`;
  context += `- Phone: ${resume.phone}\n\n`;
  
  context += `## Professional Summary\n${resume.summary}\n\n`;
  
  context += `## Work Experience\n`;
  resume.experience.forEach((exp, index) => {
    context += `### ${index + 1}. ${exp.title} at ${exp.company} (${exp.duration})\n`;
    context += `**Responsibilities:**\n`;
    exp.responsibilities.forEach(r => context += `- ${r}\n`);
    context += `**Achievements:**\n`;
    exp.achievements.forEach(a => context += `- ${a}\n\n`);
  });
  
  context += `## Education\n`;
  resume.education.forEach((edu, index) => {
    context += `### ${index + 1}. ${edu.school} (${edu.duration})\n`;
    context += `- Degree: ${edu.degree}\n`;
    if (edu.gpa) context += `- GPA: ${edu.gpa}\n`;
    context += `\n`;
  });
  
  context += `## Skills\n${resume.skills.map(s => `- ${s}`).join('\n')}\n\n`;
  
  context += `## Projects\n`;
  resume.projects.forEach((proj, index) => {
    context += `### ${index + 1}. ${proj.name}\n`;
    context += `**Description:** ${proj.description}\n`;
    context += `**Technologies:** ${proj.technologies.join(', ')}\n`;
    context += `**Results:**\n`;
    proj.results.forEach(r => context += `- ${r}\n`);
    context += `\n`;
  });
  
  return context;
}

export function buildPromptWithDirectContext(
  resumeContext: string,
  question: string
): LLMMessage[] {
  return [
    {
      role: 'system',
      content: `You are a professional interview assistant AI.

## Your Role
You help candidates prepare for job interviews by analyzing their resume and providing thoughtful answers.

## Resume Context
<resume>
${resumeContext}
</resume>

## Instructions
1. Base your answers on the provided resume context
2. Generate concise, specific answers (50-150 words)
3. Use the STAR method (Situation, Task, Action, Result) for behavioral questions
4. Prioritize quantifiable achievements from the resume
5. If information is missing, ask for clarification

## Output Format
Structure your answers with:
1. Key point (first sentence)
2. Supporting details from resume
3. Concrete example or metric if available

Remember: Be concise and specific. Avoid generic answers.`,
    },
    {
      role: 'user',
      content: question,
    },
  ];
}
```

### 2.2 RAG-based Context Injection

**Files:**
- Create: `src/context/rag.ts`

```typescript
import { RecursiveCharacterTextSplitter } from 'langchain/text_splitter';
import { OpenAIEmbeddings } from '@langchain/openai';
import * as faiss from 'faiss-node';
import { ResumeContext, buildResumeContext } from './direct';
import { LLMMessage } from '../api/types';

export class ResumeRAG {
  private embeddings: OpenAIEmbeddings;
  private index: any;
  private chunks: string[];
  private chunkMap: Map<string, string>;

  constructor(resume: ResumeContext, openAIApiKey: string) {
    this.embeddings = new OpenAIEmbeddings({ apiKey: openAIApiKey });
    this.chunks = [];
    this.chunkMap = new Map();
    
    const resumeText = buildResumeContext(resume);
    this._indexResume(resumeText);
  }

  private async _indexResume(resumeText: string): Promise<void> {
    const splitter = new RecursiveCharacterTextSplitter({
      chunkSize: 500,
      chunkOverlap: 50,
    });
    
    this.chunks = await splitter.splitText(resumeText);
    
    // Create embeddings for all chunks
    const embeddedChunks = await this.embeddings.embedDocuments(this.chunks);
    
    // Build FAISS index
    const dimension = embeddedChunks[0].length;
    this.index = faiss.IndexFlatL2(dimension);
    this.index.add(embeddedChunks);
    
    // Map chunk to original text
    this.chunks.forEach((chunk, index) => {
      this.chunkMap.set(chunk, chunk);
    });
  }

  public async getRelevantContext(query: string, k: number = 3): Promise<string> {
    const queryEmbedding = await this.embeddings.embedQuery(query);
    const distances = new Float32Array(k);
    const ids = new Int64Array(k);
    
    this.index.search(queryEmbedding, k, distances, ids);
    
    const relevantChunks = [];
    for (let i = 0; i < k; i++) {
      const chunk = this.chunks[ids[i]];
      if (chunk) {
        relevantChunks.push(chunk);
      }
    }
    
    return relevantChunks.join('\n\n');
  }

  public buildPromptWithRAG(question: string, k: number = 3): LLMMessage[] {
    return [
      {
        role: 'system',
        content: `You are a professional interview assistant AI.

## Your Role
You help candidates prepare for job interviews by analyzing their resume and providing thoughtful answers.

## Relevant Resume Sections
<resume_context>
{REPLACE_WITH_RELEVANT_CONTEXT}
</resume_context>

## Instructions
1. Base your answers ONLY on the provided resume context
2. Generate concise, specific answers (50-150 words)
3. Use the STAR method for behavioral questions
4. If the context doesn't contain relevant information, say so

## Output Format
Structure your answers with:
1. Key point (first sentence)
2. Supporting details from resume
3. Concrete example or metric if available

Remember: Be concise and specific. Avoid generic answers.`,
      },
      {
        role: 'user',
        content: question,
      },
    ];
  }

  public async generateAnswerWithRAG(
    question: string,
    llmClient: any,
    k: number = 3
  ): Promise<string> {
    const context = await this.getRelevantContext(question, k);
    
    const prompt = this.buildPromptWithRAG(question, k);
    prompt[0].content = prompt[0].content.replace('{REPLACE_WITH_RELEVANT_CONTEXT}', context);
    
    const response = await llmClient.generate(prompt);
    return response.content;
  }
}
```

---

## 3. Streaming Output Implementation

### 3.1 SSE Server Implementation

**Files:**
- Create: `src/streaming/server.ts`

```typescript
import express, { Request, Response } from 'express';
import { LLMClient, LLMMessage } from '../api/types';
import { buildPromptWithDirectContext, ResumeContext } from '../context/direct';

export class StreamingServer {
  private app: express.Application;
  private llmClient: LLMClient;
  private resumeContext: ResumeContext | null = null;

  constructor(port: number = 3000) {
    this.app = express();
    this.app.use(express.json());
    this.app.use(this._cors);
    this._setupRoutes();
    this.port = port;
  }

  private _cors(req: Request, res: Response, next: () => void): void {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    
    if (req.method === 'OPTIONS') {
      res.status(200).end();
      return;
    }
    
    next();
  }

  private _setupRoutes(): void {
    this.app.post('/api/resume', (req: Request, res: Response) => {
      this.resumeContext = req.body;
      res.json({ success: true });
    });

    this.app.post('/api/chat', (req: Request, res: Response) => {
      const question = req.body.question;
      
      if (!this.resumeContext) {
        res.status(400).json({ error: 'Resume context not set' });
        return;
      }

      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      res.setHeader('X-Accel-Buffering', 'no');

      const messages = buildPromptWithDirectContext(
        buildResumeContext(this.resumeContext),
        question
      );

      this._streamResponse(res, messages);
    });

    this.app.post('/api/chat/rag', async (req: Request, res: Response) => {
      const { question, k = 3 } = req.body;
      
      if (!this.resumeContext) {
        res.status(400).json({ error: 'Resume context not set' });
        return;
      }

      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      res.setHeader('X-Accel-Buffering', 'no');

      // For RAG, we'll stream the context first, then the answer
      // This is a simplified version - implement full RAG streaming separately
      const messages = buildPromptWithDirectContext(
        buildResumeContext(this.resumeContext),
        question
      );

      this._streamResponse(res, messages);
    });

    this.app.get('/api/health', (req: Request, res: Response) => {
      res.json({ status: 'ok', timestamp: new Date().toISOString() });
    });
  }

  private async _streamResponse(
    res: Response,
    messages: LLMMessage[]
  ): Promise<void> {
    try {
      const stream = this.llmClient.generateStream(messages);
      
      for await (const chunk of stream) {
        res.write(`data: ${JSON.stringify({ content: chunk })}\n\n`);
      }
      
      res.write('data: [DONE]\n\n');
      res.end();
    } catch (error) {
      res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
      res.end();
    }
  }

  public setLLMClient(client: LLMClient): void {
    this.llmClient = client;
  }

  public start(): void {
    this.app.listen(this.port, () => {
      console.log(`Streaming server running on port ${this.port}`);
    });
  }

  private port: number;
}
```

### 3.2 Frontend Streaming Consumer

**Files:**
- Create: `src/frontend/streaming-client.ts`

```typescript
export class StreamingClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:3000') {
    this.baseUrl = baseUrl;
  }

  public async chat(question: string, onChunk: (chunk: string) => void): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is null');
    }

    const decoder = new TextDecoder();
    let answer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            return answer;
          }

          try {
            const parsed = JSON.parse(data);
            if (parsed.content) {
              answer += parsed.content;
              onChunk(parsed.content);
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }

    return answer;
  }

  public async setResume(resume: any): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/resume`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(resume),
    });

    if (!response.ok) {
      throw new Error(`Failed to set resume: ${response.statusText}`);
    }
  }
}
```

---

## 4. Caching Layer

### 4.1 Semantic Caching

**Files:**
- Create: `src/cache/semantic.ts`

```typescript
import { OpenAIEmbeddings } from '@langchain/openai';
import * as faiss from 'faiss-node';

export interface CacheEntry {
  question: string;
  answer: string;
  timestamp: number;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
  };
}

export class SemanticCache {
  private embeddings: OpenAIEmbeddings;
  private index: any;
  private cache: Map<string, CacheEntry>;
  private chunkSize: number = 128;

  constructor(openAIApiKey: string) {
    this.embeddings = new OpenAIEmbeddings({ apiKey: openAIApiKey });
    this.cache = new Map();
    this.index = faiss.IndexFlatL2(this.chunkSize);
  }

  public async getRelevantAnswer(question: string, threshold: number = 0.8): Promise<CacheEntry | null> {
    const questionEmbedding = await this.embeddings.embedQuery(question);
    const distances = new Float32Array(1);
    const ids = new Int64Array(1);

    this.index.search(questionEmbedding, 1, distances, ids);

    if (distances[0] < threshold) {
      const key = this._getCacheKey(question);
      return this.cache.get(key) || null;
    }

    return null;
  }

  public async cacheAnswer(question: string, answer: string, usage?: any): Promise<void> {
    const questionEmbedding = await this.embeddings.embedQuery(question);
    const key = this._getCacheKey(question);

    this.cache.set(key, {
      question,
      answer,
      timestamp: Date.now(),
      usage: {
        prompt_tokens: usage?.prompt_tokens || 0,
        completion_tokens: usage?.completion_tokens || 0,
      },
    });

    this.index.add([questionEmbedding]);
  }

  private _getCacheKey(question: string): string {
    return `question:${question}`;
  }

  public getStats(): { size: number; dimensions: number } {
    return {
      size: this.cache.size,
      dimensions: this.chunkSize,
    };
  }
}
```

### 4.2 Prompt Caching

**Files:**
- Create: `src/cache/prompt.ts`

```typescript
import { LLMMessage } from '../api/types';

export class PromptCache {
  private cache: Map<string, LLMMessage[]>;
  private maxSize: number;

  constructor(maxSize: number = 1000) {
    this.cache = new Map();
    this.maxSize = maxSize;
  }

  public get(promptHash: string): LLMMessage[] | null {
    return this.cache.get(promptHash) || null;
  }

  public set(promptHash: string, messages: LLMMessage[]): void {
    if (this.cache.size >= this.maxSize) {
      // Remove oldest entry
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }

    this.cache.set(promptHash, messages);
  }

  public clear(): void {
    this.cache.clear();
  }

  public getStats(): { size: number; maxSize: number } {
    return {
      size: this.cache.size,
      maxSize: this.maxSize,
    };
  }
}
```

---

## 5. Model Selection Router

### 5.1 Smart Model Router

**Files:**
- Create: `src/router/model-router.ts`

```typescript
import { LLMClient } from '../api/types';
import { OpenAIClient } from '../api/openai';
import { ClaudeClient } from '../api/claude';
import { QwenClient } from '../api/qwen';
import { ErnieClient } from '../api/ernie';
import { GLMClient } from '../api/glm';
import { KimiClient } from '../api/kimi';

export interface ModelConfig {
  provider: 'openai' | 'claude' | 'qwen' | 'ernie' | 'glm' | 'kimi';
  model: string;
  apiKey: string;
  secretKey?: string; // For ERNIE
  priority: number; // Lower = higher priority
}

export class ModelRouter {
  private clients: Map<string, LLMClient>;
  private configs: Map<string, ModelConfig>;
  private defaultModel: string;

  constructor(configs: ModelConfig[], defaultModel: string = 'openai:gpt-4o-mini') {
    this.clients = new Map();
    this.configs = new Map();
    this.defaultModel = defaultModel;

    configs.forEach(config => {
      const client = this._createClient(config);
      const key = `${config.provider}:${config.model}`;
      this.clients.set(key, client);
      this.configs.set(key, config);
    });
  }

  private _createClient(config: ModelConfig): LLMClient {
    switch (config.provider) {
      case 'openai':
        return new OpenAIClient(config.apiKey, config.model);
      case 'claude':
        return new ClaudeClient(config.apiKey, config.model);
      case 'qwen':
        return new QwenClient(config.apiKey, config.model);
      case 'ernie':
        if (!config.secretKey) {
          throw new Error('ERNIE requires secretKey');
        }
        return new ErnieClient(config.apiKey, config.secretKey, config.model);
      case 'glm':
        return new GLMClient(config.apiKey, config.model);
      case 'kimi':
        return new KimiClient(config.apiKey, config.model);
      default:
        throw new Error(`Unknown provider: ${config.provider}`);
    }
  }

  public getClient(modelKey?: string): LLMClient {
    const key = modelKey || this.defaultModel;
    const client = this.clients.get(key);

    if (!client) {
      throw new Error(`Client not found for model: ${key}`);
    }

    return client;
  }

  public getAvailableModels(): string[] {
    return Array.from(this.clients.keys());
  }

  public getModelConfig(modelKey: string): ModelConfig | null {
    return this.configs.get(modelKey) || null;
  }

  public getPriorityModels(): ModelConfig[] {
    return Array.from(this.configs.values())
      .sort((a, b) => a.priority - b.priority);
  }
}
```

---

## 6. Main Server Setup

**Files:**
- Create: `src/server.ts`

```typescript
import { StreamingServer } from './streaming/server';
import { ModelRouter, ModelConfig } from './router/model-router';
import { SemanticCache } from './cache/semantic';
import { ResumeContext } from './context/direct';

// Configuration
const modelConfigs: ModelConfig[] = [
  {
    provider: 'openai',
    model: 'gpt-4o-mini',
    apiKey: process.env.OPENAI_API_KEY || '',
    priority: 2,
  },
  {
    provider: 'qwen',
    model: 'qwen-max',
    apiKey: process.env.QWEN_API_KEY || '',
    priority: 1,
  },
  {
    provider: 'glm',
    model: 'glm-4',
    apiKey: process.env.ZHIPU_API_KEY || '',
    priority: 3,
  },
  {
    provider: 'kimi',
    model: 'kimi-k2-turbo-preview',
    apiKey: process.env.MOONSHOT_API_KEY || '',
    priority: 4,
  },
];

const DEFAULT_MODEL = 'openai:gpt-4o-mini';

async function main(): Promise<void> {
  // Initialize model router
  const router = new ModelRouter(modelConfigs, DEFAULT_MODEL);

  // Initialize semantic cache
  const semanticCache = new SemanticCache(
    process.env.OPENAI_API_KEY || ''
  );

  // Initialize streaming server
  const server = new StreamingServer(3000);
  server.setLLMClient(router.getClient(DEFAULT_MODEL));

  // Set default resume context (can be updated via API)
  const defaultResume: ResumeContext = {
    name: 'Candidate',
    email: 'candidate@example.com',
    phone: '+1234567890',
    summary: 'Experienced software engineer with 5+ years of experience.',
    experience: [],
    education: [],
    skills: [],
    projects: [],
  };

  // Start server
  server.start();
  console.log('Interview Helper Server started on port 3000');
}

main().catch(console.error);
```

---

## 7. Testing

**Files:**
- Create: `tests/api.test.ts`

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { OpenAIClient } from '../src/api/openai';
import { QwenClient } from '../src/api/qwen';
import { buildPromptWithDirectContext, ResumeContext } from '../src/context/direct';

describe('LLM API Clients', () => {
  let openaiClient: OpenAIClient;
  let qwenClient: QwenClient;

  beforeEach(() => {
    const apiKey = process.env.OPENAI_API_KEY || 'test-key';
    openaiClient = new OpenAIClient(apiKey);
    
    const qwenKey = process.env.QWEN_API_KEY || 'test-key';
    qwenClient = new QwenClient(qwenKey);
  });

  it('should generate response from OpenAI', async () => {
    const messages = [
      { role: 'system', content: 'You are a helpful assistant.' },
      { role: 'user', content: 'Say hello!' },
    ];

    const response = await openaiClient.generate(messages);
    
    expect(response.content).toBeDefined();
    expect(response.content.length).toBeGreaterThan(0);
  }, 10000);

  it('should generate response from Qwen', async () => {
    const messages = [
      { role: 'system', content: 'You are a helpful assistant.' },
      { role: 'user', content: '你好！' },
    ];

    const response = await qwenClient.generate(messages);
    
    expect(response.content).toBeDefined();
    expect(response.content.length).toBeGreaterThan(0);
  }, 10000);

  it('should build prompt with direct context', () => {
    const resume: ResumeContext = {
      name: 'Test Candidate',
      email: 'test@example.com',
      phone: '1234567890',
      summary: 'Software engineer with 5 years experience.',
      experience: [
        {
          company: 'Tech Corp',
          title: 'Senior Engineer',
          duration: '2020-2024',
          responsibilities: ['Led a team of 5', 'Built scalable systems'],
          achievements: ['Improved performance by 50%'],
        },
      ],
      education: [
        {
          school: 'University',
          degree: 'B.S. Computer Science',
          duration: '2016-2020',
        },
      ],
      skills: ['JavaScript', 'Python', 'React'],
      projects: [],
    };

    const prompt = buildPromptWithDirectContext(
      'Test resume context',
      'Tell me about your experience'
    );

    expect(prompt).toHaveLength(2);
    expect(prompt[0].role).toBe('system');
    expect(prompt[1].role).toBe('user');
  });
});
```

---

## 8. Usage Examples

### 8.1 Basic Usage

```typescript
import { ModelRouter, ModelConfig } from './src/router/model-router';
import { buildPromptWithDirectContext, ResumeContext } from './src/context/direct';

async function basicUsage() {
  const modelConfigs: ModelConfig[] = [
    {
      provider: 'openai',
      model: 'gpt-4o-mini',
      apiKey: process.env.OPENAI_API_KEY || '',
      priority: 1,
    },
  ];

  const router = new ModelRouter(modelConfigs);
  const client = router.getClient();

  const resume: ResumeContext = {
    name: 'John Doe',
    email: 'john@example.com',
    phone: '1234567890',
    summary: 'Software engineer with 5 years experience.',
    experience: [],
    education: [],
    skills: ['JavaScript', 'Python'],
    projects: [],
  };

  const question = 'Tell me about your experience';
  const messages = buildPromptWithDirectContext(
    'Resume context here',
    question
  );

  const response = await client.generate(messages);
  console.log(response.content);
}
```

### 8.2 Streaming Usage

```typescript
import { StreamingClient } from './src/frontend/streaming-client';

async function streamingUsage() {
  const client = new StreamingClient('http://localhost:3000');

  const resume = {
    name: 'John Doe',
    email: 'john@example.com',
    phone: '1234567890',
    summary: 'Software engineer with 5 years experience.',
    experience: [],
    education: [],
    skills: ['JavaScript', 'Python'],
    projects: [],
  };

  await client.setResume(resume);

  const answer = await client.chat('Tell me about your experience', (chunk) => {
    process.stdout.write(chunk); // Stream output
  });

  console.log('\nFull answer:', answer);
}
```

---

## 9. Deployment

### 9.1 Dockerfile

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
```

### 9.2 docker-compose.yml

```yaml
version: '3.8'

services:
  interview-helper:
    build: .
    ports:
      - '3000:3000'
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - QWEN_API_KEY=${QWEN_API_KEY}
      - ZHIPU_API_KEY=${ZHIPU_API_KEY}
      - MOONSHOT_API_KEY=${MOONSHOT_API_KEY}
    volumes:
      - .:/app
```

---

## 10. Environment Variables

Create a `.env` file:

```env
# LLM API Keys
OPENAI_API_KEY=sk-...
QWEN_API_KEY=sk-...
ZHIPU_API_KEY=...
MOONSHOT_API_KEY=...
CLAUDE_API_KEY=sk-ant-...
ERNIE_API_KEY=...
ERNIE_SECRET_KEY=...

# Server Configuration
PORT=3000
NODE_ENV=development
```

---

## Summary

This design provides:

1. **Multi-provider LLM support** - OpenAI, Claude, Qwen, ERNIE, GLM, Kimi
2. **Resume context injection** - Direct and RAG-based approaches
3. **Streaming output** - SSE-based real-time response display
4. **Caching layer** - Semantic and prompt caching for optimization
5. **Model router** - Smart model selection based on priority

**Next steps:** Implement each component, write tests, and deploy to production.
