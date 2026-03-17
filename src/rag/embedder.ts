import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY || process.env.EMBEDDING_API_KEY,
});

export interface EmbeddingResult {
  id: string;
  embedding: number[];
  text: string;
}

/**
 * Text Embedding Service
 * Converts text to vectors for similarity search
 */
export async function embedText(text: string, documentId: string): Promise<EmbeddingResult[]> {
  // Chunk text into smaller pieces
  const chunks = chunkText(text, 1000, 200);
  
  const results: EmbeddingResult[] = [];
  
  // Process chunks in batches to avoid rate limits
  const batchSize = 10;
  for (let i = 0; i < chunks.length; i += batchSize) {
    const batch = chunks.slice(i, i + batchSize);
    
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: batch,
    });
    
    batch.forEach((chunk, idx) => {
      results.push({
        id: `${documentId}_${i + idx}`,
        embedding: response.data[idx].embedding,
        text: chunk,
      });
    });
  }
  
  return results;
}

/**
 * Embed a query for similarity search
 */
export async function embedQuery(query: string): Promise<number[]> {
  const response = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: query,
  });
  
  return response.data[0].embedding;
}

/**
 * Split text into overlapping chunks
 */
export function chunkText(text: string, chunkSize: number = 1000, overlap: number = 200): string[] {
  const chunks: string[] = [];
  let start = 0;
  
  while (start < text.length) {
    const end = start + chunkSize;
    let chunk = text.slice(start, end);
    
    // Try to break at sentence boundary
    if (end < text.length) {
      const lastPeriod = chunk.lastIndexOf('.');
      const lastNewline = chunk.lastIndexOf('\n');
      const breakPoint = Math.max(lastPeriod, lastNewline);
      
      if (breakPoint > chunkSize * 0.5) {
        chunk = chunk.slice(0, breakPoint + 1);
        start = start + breakPoint + 1;
      } else {
        start = end;
      }
    } else {
      start = end;
    }
    
    if (chunk.trim()) {
      chunks.push(chunk.trim());
    }
    
    // Prevent infinite loop
    if (start <= chunks.length > 0 && chunks[chunks.length - 1] === chunk && start >= text.length) {
      break;
    }
  }
  
  return chunks;
}
