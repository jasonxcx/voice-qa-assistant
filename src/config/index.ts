import dotenv from 'dotenv';

dotenv.config();

export const config = {
  // Server
  port: parseInt(process.env.PORT || '3000'),
  nodeEnv: process.env.NODE_ENV || 'development',
  
  // API Keys
  openaiApiKey: process.env.OPENAI_API_KEY,
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  qwenApiKey: process.env.DASHSCOPE_API_KEY,
  kimiApiKey: process.env.KIMI_API_KEY,
  glmApiKey: process.env.ZHIPU_API_KEY,
  ernieApiKey: process.env.ERNIE_API_KEY,
  
  // Redis
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    password: process.env.REDIS_PASSWORD,
  },
  
  // Cache
  cache: {
    defaultTTL: parseInt(process.env.CACHE_TTL || '3600'),
    enabled: process.env.CACHE_ENABLED !== 'false',
  },
  
  // RAG
  rag: {
    embeddingModel: process.env.EMBEDDING_MODEL || 'text-embedding-3-small',
    chunkSize: parseInt(process.env.CHUNK_SIZE || '1000'),
    chunkOverlap: parseInt(process.env.CHUNK_OVERLAP || '200'),
    topK: parseInt(process.env.RAG_TOP_K || '5'),
  },
  
  // Models
  models: {
    openai: {
      default: 'gpt-4o',
      alternatives: ['gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    },
    anthropic: {
      default: 'claude-sonnet-4-20250514',
      alternatives: ['claude-opus-4-20250514', 'claude-3-5-sonnet-20241022'],
    },
    qwen: {
      default: 'qwen-plus',
      alternatives: ['qwen-max', 'qwen-turbo', 'qwq-32b'],
    },
    kimi: {
      default: 'kimi-k2-turbo-preview',
      alternatives: ['kimi-flash'],
    },
    glm: {
      default: 'glm-4',
      alternatives: ['glm-4-flash', 'glm-4-plus'],
    },
    ernie: {
      default: 'ernie-4.0-8k',
      alternatives: ['ernie-3.5-8k', 'ernie-speed-8k'],
    },
  },
};
