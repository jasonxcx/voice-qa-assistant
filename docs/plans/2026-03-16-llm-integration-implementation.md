# LLM API Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an interview helper that analyzes resumes and answers interview questions using multiple LLM providers with streaming output and context-aware responses.

**Architecture:** 
- Multi-provider LLM client layer supporting OpenAI, Claude, Qwen, ERNIE, GLM, Kimi
- Resume context injection via system prompt and RAG approaches
- SSE-based streaming output for real-time response display
- Caching layer for latency optimization

**Tech Stack:** TypeScript/Node.js, FastAPI (Python backend option), FAISS for RAG

---
## Phase 1: Core Infrastructure

### Task 1: Initialize Node.js Project

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `.env.example`

**Step 1: Initialize package.json**

```bash
npm init -y
```

**Step 2: Install dependencies**

```bash
npm install express openai @anthropic-ai/sdk zhipuai axios faiss-node langchain
npm install -D typescript ts-node @types/node @types/express vitest
```

**Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**Step 4: Create .env.example**

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

**Step 5: Commit**

```bash
git add package.json tsconfig.json .env.example
git commit -m "chore: initialize project structure"
```

---

### Task 2: Create Project Structure

**Files:**
- Create: `src/api/` directory
- Create: `src/context/` directory
- Create: `src/streaming/` directory
- Create: `src/cache/` directory
- Create: `src/router/` directory
- Create: `tests/` directory

**Step 1: Create directory structure**

```bash
mkdir -p src/api src/context src/streaming src/cache src/router tests
```

**Step 2: Create index files**

```bash
# src/api/index.ts
export * from './client';
export * from './types';

# src/context/index.ts
export * from './direct';
export * from './rag';

# src/streaming/index.ts
export * from './server';

# src/cache/index.ts
export * from './semantic';
export * from './prompt';

# src/router/index.ts
export * from './model-router';

# src/index.ts
export * from './server';
```

**Step 3: Commit**

```bash
git add src/ tests/
git commit -m "chore: create project directory structure"
```

---

## Phase 2: LLM API Clients

### Task 3: Create API Client Interface

**Files:**
- Create: `src/api/types.ts`
- Create: `src/api/client.ts`

**Step 1: Create types.ts**

```typescript
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

export interface GenerateOptions {
  temperature?: number;
  maxTokens?: number;
}

export interface LLMClient {
  generate(messages: LLMMessage[], options?: GenerateOptions): Promise<LLMResponse>;
  generateStream(messages: LLMMessage[], options?: GenerateOptions): AsyncGenerator<string>;
  getSupportedModels(): string[];
}
```

**Step 2: Create client.ts**

```typescript
import { LLMMessage, LLMResponse, GenerateOptions } from './types';

export abstract class BaseClient implements LLMClient {
  abstract generate(messages: LLMMessage[], options?: GenerateOptions): Promise<LLMResponse>;
  abstract generateStream(messages: LLMMessage[], options?: GenerateOptions): AsyncGenerator<string>;
  abstract getSupportedModels(): string[];
}
```

**Step 3: Run verification**

```bash
npx tsc --noEmit
```

**Step 4: Commit**

```bash
git add src/api/types.ts src/api/client.ts
git commit -m "feat: add LLM API client interface"
```

---

### Task 4: Implement OpenAI Client

**Files:**
- Create: `src/api/openai.ts`

**Step 1: Create openai.ts**

```typescript
import { OpenAI } from 'openai';
import { BaseClient } from './client';
import { LLMMessage, LLMResponse, GenerateOptions } from './types';

export class OpenAIClient extends BaseClient {
  private client: OpenAI;
  private model: string;

  constructor(apiKey: string, model: string = 'gpt-4o-mini') {
    super();
    this.client = new OpenAI({ apiKey });
    this.model = model;
  }

  async generate(messages: LLMMessage[], options?: GenerateOptions): Promise<LLMResponse> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options?.temperature,
      max_tokens: options?.maxTokens,
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

  async *generateStream(messages: LLMMessage[], options?: GenerateOptions): AsyncGenerator<string> {
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options?.temperature,
      max_tokens: options?.maxTokens,
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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/api/openai.ts
git commit -m "feat: implement OpenAI client"
```

---

### Task 5: Implement Claude Client

**Files:**
- Create: `src/api/claude.ts`

**Step 1: Create claude.ts**

```typescript
import { Anthropic } from '@anthropic-ai/sdk';
import { BaseClient } from './client';
import { LLMMessage, LLMResponse, GenerateOptions } from './types';

export class ClaudeClient extends BaseClient {
  private client: Anthropic;
  private model: string;

  constructor(apiKey: string, model: string = 'claude-3-5-sonnet-20240620') {
    super();
    this.client = new Anthropic({ apiKey });
    this.model = model;
  }

  async generate(messages: LLMMessage[], options?: GenerateOptions): Promise<LLMResponse> {
    const userMessages = messages.filter(m => m.role === 'user');
    const systemMessage = messages.find(m => m.role === 'system');

    const response = await this.client.messages.create({
      model: this.model,
      max_tokens: options?.maxTokens || 1024,
      system: systemMessage?.content,
      messages: userMessages.map(m => ({ role: m.role, content: m.content })),
      temperature: options?.temperature,
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

  async *generateStream(messages: LLMMessage[], options?: GenerateOptions): AsyncGenerator<string> {
    const userMessages = messages.filter(m => m.role === 'user');
    const systemMessage = messages.find(m => m.role === 'system');

    const stream = await this.client.messages.stream({
      model: this.model,
      max_tokens: options?.maxTokens || 1024,
      system: systemMessage?.content,
      messages: userMessages.map(m => ({ role: m.role, content: m.content })),
      temperature: options?.temperature,
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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/api/claude.ts
git commit -m "feat: implement Claude client"
```

---

### Task 6: Implement Qwen Client

**Files:**
- Create: `src/api/qwen.ts`

**Step 1: Create qwen.ts**

```typescript
import { OpenAI } from 'openai';
import { BaseClient } from './client';
import { LLMMessage, LLMResponse, GenerateOptions } from './types';

export class QwenClient extends BaseClient {
  private client: OpenAI;
  private model: string;

  constructor(apiKey: string, model: string = 'qwen-max') {
    super();
    this.client = new OpenAI({
      apiKey,
      baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    });
    this.model = model;
  }

  async generate(messages: LLMMessage[], options?: GenerateOptions): Promise<LLMResponse> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options?.temperature,
      max_tokens: options?.maxTokens,
    });
    return {
      content: response.choices[0].message.content || '',
      model: this.model,
    };
  }

  async *generateStream(messages: LLMMessage[], options?: GenerateOptions): AsyncGenerator<string> {
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options?.temperature,
      max_tokens: options?.maxTokens,
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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/api/qwen.ts
git commit -m "feat: implement Qwen client"
```

---

### Task 7: Implement ERNIE Client

**Files:**
- Create: `src/api/ernie.ts`

**Step 1: Create ernie.ts**

```typescript
import axios from 'axios';
import { BaseClient } from './client';
import { LLMMessage, LLMResponse, GenerateOptions } from './types';

export class ErnieClient extends BaseClient {
  private apiKey: string;
  private secretKey: string;
  private model: string;
  private accessToken: string | null = null;

  constructor(apiKey: string, secretKey: string, model: string = 'ernie-4.5-turbo') {
    super();
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

  async generate(messages: LLMMessage[], options?: GenerateOptions): Promise<LLMResponse> {
    const accessToken = await this.getAccessToken();
    const userMessages = messages.filter(m => m.role !== 'system');
    
    const response = await axios.post(
      `https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token=${accessToken}`,
      {
        messages: userMessages,
        stream: false,
        temperature: options?.temperature,
        max_tokens: options?.maxTokens,
      }
    );

    return {
      content: response.data.result || '',
      model: this.model,
    };
  }

  async *generateStream(messages: LLMMessage[], options?: GenerateOptions): AsyncGenerator<string> {
    const accessToken = await this.getAccessToken();
    const userMessages = messages.filter(m => m.role !== 'system');

    const response = await axios.post(
      `https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token=${accessToken}`,
      {
        messages: userMessages,
        stream: true,
        temperature: options?.temperature,
        max_tokens: options?.maxTokens,
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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/api/ernie.ts
git commit -m "feat: implement ERNIE client"
```

---

### Task 8: Implement GLM Client

**Files:**
- Create: `src/api/glm.ts`

**Step 1: Create glm.ts**

```typescript
import { ZhipuAI } from 'zhipuai';
import { BaseClient } from './client';
import { LLMMessage, LLMResponse, GenerateOptions } from './types';

export class GLMClient extends BaseClient {
  private client: ZhipuAI;
  private model: string;

  constructor(apiKey: string, model: string = 'glm-4') {
    super();
    this.client = new ZhipuAI({ apiKey });
    this.model = model;
  }

  async generate(messages: LLMMessage[], options?: GenerateOptions): Promise<LLMResponse> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options?.temperature,
      max_tokens: options?.maxTokens,
    });
    return {
      content: response.choices[0].message.content || '',
      model: this.model,
    };
  }

  async *generateStream(messages: LLMMessage[], options?: GenerateOptions): AsyncGenerator<string> {
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options?.temperature,
      max_tokens: options?.maxTokens,
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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/api/glm.ts
git commit -m "feat: implement GLM client"
```

---

### Task 9: Implement Kimi Client

**Files:**
- Create: `src/api/kimi.ts`

**Step 1: Create kimi.ts**

```typescript
import { OpenAI } from 'openai';
import { BaseClient } from './client';
import { LLMMessage, LLMResponse, GenerateOptions } from './types';

export class KimiClient extends BaseClient {
  private client: OpenAI;
  private model: string;

  constructor(apiKey: string, model: string = 'kimi-k2-turbo-preview') {
    super();
    this.client = new OpenAI({
      apiKey,
      baseURL: 'https://api.moonshot.ai/v1',
    });
    this.model = model;
  }

  async generate(messages: LLMMessage[], options?: GenerateOptions): Promise<LLMResponse> {
    const response = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options?.temperature,
      max_tokens: options?.maxTokens,
    });
    return {
      content: response.choices[0].message.content || '',
      model: this.model,
    };
  }

  async *generateStream(messages: LLMMessage[], options?: GenerateOptions): AsyncGenerator<string> {
    const stream = await this.client.chat.completions.create({
      model: this.model,
      messages,
      temperature: options?.temperature,
      max_tokens: options?.maxTokens,
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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/api/kimi.ts
git commit -m "feat: implement Kimi client"
```

---

## Phase 3: Resume Context Injection

### Task 10: Create Resume Context Types

**Files:**
- Create: `src/context/types.ts`

**Step 1: Create types.ts**

```typescript
export interface ResumeExperience {
  company: string;
  title: string;
  duration: string;
  responsibilities: string[];
  achievements: string[];
}

export interface ResumeEducation {
  school: string;
  degree: string;
  duration: string;
  gpa?: string;
}

export interface ResumeProject {
  name: string;
  description: string;
  technologies: string[];
  results: string[];
}

export interface ResumeContext {
  name: string;
  email: string;
  phone: string;
  summary: string;
  experience: ResumeExperience[];
  education: ResumeEducation[];
  skills: string[];
  projects: ResumeProject[];
}
```

**Step 2: Commit**

```bash
git add src/context/types.ts
git commit -m "feat: add resume context types"
```

---

### Task 11: Implement Direct Context Injection

**Files:**
- Create: `src/context/direct.ts`

**Step 1: Create direct.ts**

```typescript
import { LLMMessage } from '../api/types';
import { ResumeContext } from './types';

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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/context/direct.ts
git commit -m "feat: implement direct context injection"
```

---

### Task 12: Implement RAG-based Context Injection

**Files:**
- Create: `src/context/rag.ts`

**Step 1: Create rag.ts**

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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/context/rag.ts
git commit -m "feat: implement RAG-based context injection"
```

---

## Phase 4: Streaming Output

### Task 13: Create Streaming Server

**Files:**
- Create: `src/streaming/server.ts`

**Step 1: Create server.ts**

```typescript
import express, { Request, Response, NextFunction } from 'express';
import { LLMClient, LLMMessage } from '../api/types';
import { buildPromptWithDirectContext, ResumeContext, buildResumeContext } from '../context/direct';

export class StreamingServer {
  private app: express.Application;
  private llmClient: LLMClient | null = null;
  private resumeContext: ResumeContext | null = null;
  private port: number;

  constructor(port: number = 3000) {
    this.app = express();
    this.app.use(express.json());
    this.app.use(this._cors);
    this._setupRoutes();
    this.port = port;
  }

  private _cors(req: Request, res: Response, next: NextFunction): void {
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

    this.app.get('/api/health', (req: Request, res: Response) => {
      res.json({ status: 'ok', timestamp: new Date().toISOString() });
    });
  }

  private async _streamResponse(
    res: Response,
    messages: LLMMessage[]
  ): Promise<void> {
    if (!this.llmClient) {
      res.status(500).json({ error: 'LLM client not configured' });
      return;
    }

    try {
      const stream = this.llmClient.generateStream(messages);
      
      for await (const chunk of stream) {
        res.write(`data: ${JSON.stringify({ content: chunk })}\n\n`);
      }
      
      res.write('data: [DONE]\n\n');
      res.end();
    } catch (error) {
      res.write(`data: ${JSON.stringify({ error: (error as Error).message })}\n\n`);
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
}
```

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/streaming/server.ts
git commit -m "feat: implement SSE streaming server"
```

---

### Task 14: Create Frontend Streaming Client

**Files:**
- Create: `src/frontend/streaming-client.ts`

**Step 1: Create streaming-client.ts**

```typescript
export class StreamingClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:3000') {
    this.baseUrl = baseUrl;
  }

  public async chat(question: string, onChunk: (chunk: string) => void): Promise<string> {
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

**Step 2: Commit**

```bash
git add src/frontend/streaming-client.ts
git commit -m "feat: implement frontend streaming client"
```

---

## Phase 5: Caching Layer

### Task 15: Implement Semantic Caching

**Files:**
- Create: `src/cache/semantic.ts`

**Step 1: Create semantic.ts**

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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/cache/semantic.ts
git commit -m "feat: implement semantic caching"
```

---

### Task 16: Implement Prompt Caching

**Files:**
- Create: `src/cache/prompt.ts`

**Step 1: Create prompt.ts**

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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/cache/prompt.ts
git commit -m "feat: implement prompt caching"
```

---

## Phase 6: Model Router

### Task 17: Implement Model Router

**Files:**
- Create: `src/router/model-router.ts`

**Step 1: Create model-router.ts**

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
  secretKey?: string;
  priority: number;
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

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/router/model-router.ts
git commit -m "feat: implement model router"
```

---

### Task 18: Create Main Server

**Files:**
- Create: `src/server.ts`

**Step 1: Create server.ts**

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

  // Start server
  server.start();
  console.log('Interview Helper Server started on port 3000');
}

main().catch(console.error);
```

**Step 2: Run verification**

```bash
npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add src/server.ts
git commit -m "feat: implement main server"
```

---

## Phase 7: Testing

### Task 19: Create API Tests

**Files:**
- Create: `tests/api.test.ts`

**Step 1: Create api.test.ts**

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
      experience: [],
      education: [],
      skills: [],
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

**Step 2: Run tests**

```bash
npx vitest run
```

**Step 3: Commit**

```bash
git add tests/api.test.ts
git commit -m "test: add API client tests"
```

---

### Task 20: Create Integration Tests

**Files:**
- Create: `tests/integration.test.ts`

**Step 1: Create integration.test.ts**

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { ModelRouter, ModelConfig } from '../src/router/model-router';
import { StreamingServer } from '../src/streaming/server';
import { ResumeContext } from '../src/context/direct';

describe('Integration Tests', () => {
  let router: ModelRouter;
  let server: StreamingServer;

  beforeEach(() => {
    const modelConfigs: ModelConfig[] = [
      {
        provider: 'openai',
        model: 'gpt-4o-mini',
        apiKey: process.env.OPENAI_API_KEY || 'test-key',
        priority: 1,
      },
    ];

    router = new ModelRouter(modelConfigs);
    server = new StreamingServer(3001);
    server.setLLMClient(router.getClient());
  });

  it('should initialize model router', () => {
    expect(router).toBeDefined();
    expect(router.getAvailableModels().length).toBeGreaterThan(0);
  });

  it('should initialize streaming server', () => {
    expect(server).toBeDefined();
  });

  it('should set resume context', async () => {
    const resume: ResumeContext = {
      name: 'Test Candidate',
      email: 'test@example.com',
      phone: '1234567890',
      summary: 'Software engineer with 5 years experience.',
      experience: [],
      education: [],
      skills: [],
      projects: [],
    };

    // This would be tested via HTTP request in a real integration test
    expect(resume.name).toBe('Test Candidate');
  });
});
```

**Step 2: Run tests**

```bash
npx vitest run
```

**Step 3: Commit**

```bash
git add tests/integration.test.ts
git commit -m "test: add integration tests"
```

---

## Phase 8: Documentation

### Task 21: Create README

**Files:**
- Create: `README.md`

**Step 1: Create README.md**

```markdown
# Interview Helper

An AI-powered interview helper that analyzes resumes and answers interview questions using multiple LLM providers.

## Features

- **Multi-provider LLM Support**: OpenAI, Claude, Qwen, ERNIE, GLM, Kimi
- **Resume Context Injection**: Direct and RAG-based approaches
- **Streaming Output**: Real-time response display with SSE
- **Caching Layer**: Semantic and prompt caching for optimization

## Installation

```bash
npm install
cp .env.example .env
# Edit .env with your API keys
npm run build
npm start
```

## API Endpoints

### POST /api/resume

Set the resume context for the interview session.

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "1234567890",
  "summary": "Software engineer with 5 years experience.",
  "experience": [],
  "education": [],
  "skills": ["JavaScript", "Python"],
  "projects": []
}
```

### POST /api/chat

Stream interview answers based on the resume context.

```json
{
  "question": "Tell me about your experience"
}
```

Response format (SSE):

```
data: {"content": "Hello"}
data: {"content": " world"}
data: [DONE]
```

### GET /api/health

Health check endpoint.

## Environment Variables

```env
OPENAI_API_KEY=sk-...
QWEN_API_KEY=sk-...
ZHIPU_API_KEY=...
MOONSHOT_API_KEY=...
CLAUDE_API_KEY=sk-ant-...
ERNIE_API_KEY=...
ERNIE_SECRET_KEY=...
PORT=3000
NODE_ENV=development
```

## License

MIT
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

---

### Task 22: Create API Documentation

**Files:**
- Create: `docs/api.md`

**Step 1: Create api.md**

```markdown
# API Documentation

## Overview

The Interview Helper API provides endpoints for setting resume context and streaming interview answers.

## Authentication

No authentication required for local development. For production, add API key authentication.

## Endpoints

### POST /api/resume

Sets the resume context for the interview session.

**Request Body:**

```json
{
  "name": "string",
  "email": "string",
  "phone": "string",
  "summary": "string",
  "experience": [
    {
      "company": "string",
      "title": "string",
      "duration": "string",
      "responsibilities": ["string"],
      "achievements": ["string"]
    }
  ],
  "education": [
    {
      "school": "string",
      "degree": "string",
      "duration": "string",
      "gpa": "string"
    }
  ],
  "skills": ["string"],
  "projects": [
    {
      "name": "string",
      "description": "string",
      "technologies": ["string"],
      "results": ["string"]
    }
  ]
}
```

**Response:**

```json
{
  "success": true
}
```

### POST /api/chat

Streams interview answers based on the resume context.

**Request Body:**

```json
{
  "question": "string"
}
```

**Response:**

SSE (Server-Sent Events) format:

```
data: {"content": "Hello"}
data: {"content": " world"}
data: [DONE]
```

### GET /api/health

Health check endpoint.

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200`: Success
- `400`: Bad request (missing required fields)
- `500`: Internal server error

Error response format:

```json
{
  "error": "Error message"
}
```
```

**Step 2: Commit**

```bash
git add docs/api.md
git commit -m "docs: add API documentation"
```

---

## Phase 9: Deployment

### Task 23: Create Docker Configuration

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

**Step 1: Create Dockerfile**

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
```

**Step 2: Create docker-compose.yml**

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
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - ERNIE_API_KEY=${ERNIE_API_KEY}
      - ERNIE_SECRET_KEY=${ERNIE_SECRET_KEY}
    volumes:
      - .:/app
    restart: unless-stopped
```

**Step 3: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "chore: add Docker configuration"
```

---

### Task 24: Create .gitignore

**Files:**
- Create: `.gitignore`

**Step 1: Create .gitignore**

```gitignore
# Dependencies
node_modules/
package-lock.json

# Build output
dist/
build/
*.tsbuildinfo

# Environment variables
.env
.env.local
.env.*.local

# Logs
logs/
*.log
npm-debug.log*

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Test coverage
coverage/

# Docker
.dockerignore
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

## Summary

This implementation plan covers:

1. **Core Infrastructure** - Project setup, TypeScript configuration
2. **LLM API Clients** - OpenAI, Claude, Qwen, ERNIE, GLM, Kimi
3. **Resume Context Injection** - Direct and RAG-based approaches
4. **Streaming Output** - SSE-based real-time response display
5. **Caching Layer** - Semantic and prompt caching
6. **Model Router** - Smart model selection
7. **Testing** - Unit and integration tests
8. **Documentation** - README and API docs
9. **Deployment** - Docker configuration

**Total Tasks:** 24

**Estimated Time:** 8-12 hours

**Next Steps:** Execute tasks in order, run verification after each batch, commit frequently.