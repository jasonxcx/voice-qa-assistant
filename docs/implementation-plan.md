# Interview Helper - Implementation Plan

## Project Overview

Multi-LLM interview preparation app with:
- OpenAI, Claude, Qwen, ERNIE, GLM, Kimi support
- Resume context injection (direct + RAG)
- SSE streaming
- Caching layer

## Directory Structure

```
src/
├── api/              # Express routes
│   ├── chat.routes.ts
│   └── model.routes.ts
├── clients/         # LLM clients
│   ├── base.client.ts
│   ├── openai.client.ts
│   ├── anthropic.client.ts
│   ├── qwen.client.ts
│   ├── glm.client.ts
│   ├── kimi.client.ts
│   ├── ernie.client.ts
│   └── index.ts
├── cache/           # Caching
│   ├── redis.cache.ts
│   └── memory.cache.ts
├── rag/             # RAG implementation
│   ├── embedder.ts
│   └── retriever.ts
├── services/        # Business logic
│   ├── context.service.ts
│   └── model.selector.ts
├── config/          # Configuration
│   └── index.ts
├── types/           # TypeScript types
├── utils/           # Utilities
│   └── sse.ts
├── app.ts
└── server.ts
```

## Key Implementation Details

### 1. LLM Client Interface
All clients implement BaseLLMClient with:
- chat() - non-streaming
- chatStream() - async iterable for SSE

### 2. Streaming (SSE)
- Content-Type: text/event-stream
- X-Accel-Buffering: no (nginx)
- Events: token, error, complete

### 3. Caching
- Redis primary with memory fallback
- Cache key from message hash
- TTL: 1 hour default

### 4. Resume Context
- Direct: system prompt injection
- RAG: vector similarity search
- Hybrid: combine both approaches

## Implementation Order

1. Project setup + Express server
2. Base client + OpenAI client
3. Other LLM clients (Qwen, Kimi, GLM, ERNIE)
4. SSE streaming endpoint
5. Caching layer
6. Resume context service (RAG)
7. Frontend React app
8. Testing & deployment
