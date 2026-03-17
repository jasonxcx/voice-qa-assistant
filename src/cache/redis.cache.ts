import Redis from 'ioredis';
import { createHash } from 'crypto';

export interface CacheOptions {
  ttl?: number;
}

export interface CacheEntry {
  value: any;
  expiresAt?: number;
}

/**
 * Redis Cache Service
 * Primary caching layer for API responses
 */
export class RedisCacheService {
  private redis: Redis;
  private defaultTTL: number = 3600; // 1 hour
  
  constructor() {
    this.redis = new Redis({
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
      password: process.env.REDIS_PASSWORD,
      lazyConnect: true,
    });
    
    this.redis.on('error', (err) => {
      console.error('Redis connection error:', err);
    });
  }
  
  /**
   * Get cached value by key
   */
  async get(key: string): Promise<any | null> {
    try {
      const data = await this.redis.get(this.normalizeKey(key));
      if (!data) return null;
      
      const entry: CacheEntry = JSON.parse(data);
      
      if (entry.expiresAt && entry.expiresAt < Date.now()) {
        await this.delete(key);
        return null;
      }
      
      return entry.value;
    } catch (error) {
      console.error('Redis get error:', error);
      return null;
    }
  }
  
  /**
   * Set cached value with TTL
   */
  async set(key: string, value: any, options: CacheOptions = {}): Promise<void> {
    try {
      const entry: CacheEntry = {
        value,
        expiresAt: options.ttl 
          ? Date.now() + options.ttl * 1000 
          : Date.now() + this.defaultTTL * 1000,
      };
      
      await this.redis.set(
        this.normalizeKey(key),
        JSON.stringify(entry),
        'EX',
        options.ttl || this.defaultTTL
      );
    } catch (error) {
      console.error('Redis set error:', error);
    }
  }
  
  /**
   * Delete cached value
   */
  async delete(key: string): Promise<void> {
    await this.redis.del(this.normalizeKey(key));
  }
  
  /**
   * Check if key exists
   */
  async exists(key: string): Promise<boolean> {
    const result = await this.redis.exists(this.normalizeKey(key));
    return result === 1;
  }
  
  /**
   * Clear all cache or by prefix
   */
  async clear(prefix?: string): Promise<void> {
    if (prefix) {
      const keys = await this.redis.keys(`${prefix}:*`);
      if (keys.length > 0) {
        await this.redis.del(...keys);
      }
    } else {
      await this.redis.flushdb();
    }
  }
  
  /**
   * Generate cache key from request parameters
   */
  generateKey(params: {
    messages: any[];
    model?: string;
    provider: string;
    systemPrompt?: string;
  }): string {
    const keyData = JSON.stringify({
      messages: params.messages,
      model: params.model,
      provider: params.provider,
      systemPrompt: params.systemPrompt,
    });
    
    const hash = createHash('sha256').update(keyData).digest('hex');
    return `chat:${params.provider}:${hash.slice(0, 16)}`;
  }
  
  private normalizeKey(key: string): string {
    return key.toLowerCase().replace(/[^a-z0-9:_-]/g, '_');
  }
}
