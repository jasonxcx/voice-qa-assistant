import { embedQuery, EmbeddingResult } from './embedder';

export interface RetrievedChunk {
  content: string;
  score: number;
  index: number;
}

// In production, replace with actual vector DB (Pinecone, Qdrant, Weaviate)
// For now, use in-memory storage
const vectorStore: Map<string, EmbeddingResult[]> = new Map();

/**
 * Retrieve relevant context chunks for a query
 */
export async function retrieveContext(
  documentId: string,
  query: string,
  topK: number = 5
): Promise<RetrievedChunk[]> {
  const queryEmbedding = await embedQuery(query);
  const documentChunks = vectorStore.get(documentId) || [];
  
  if (documentChunks.length === 0) {
    return [];
  }
  
  // Calculate cosine similarity for each chunk
  const scored = documentChunks.map(chunk => ({
    ...chunk,
    score: cosineSimilarity(queryEmbedding, chunk.embedding),
  }));
  
  // Sort by score (highest first) and take top K
  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, topK)
    .map((c, idx) => ({
      content: c.text,
      score: c.score,
      index: idx,
    }));
}

/**
 * Store embeddings for a document
 */
export function storeEmbeddings(documentId: string, embeddings: EmbeddingResult[]): void {
  vectorStore.set(documentId, embeddings);
}

/**
 * Remove embeddings for a document
 */
export function deleteEmbeddings(documentId: string): void {
  vectorStore.delete(documentId);
}

/**
 * Get all stored documents
 */
export function getStoredDocuments(): string[] {
  return Array.from(vectorStore.keys());
}

/**
 * Cosine similarity between two vectors
 */
function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) {
    throw new Error('Vectors must have same dimension');
  }
  
  const dotProduct = a.reduce((sum, val, i) => sum + val * b[i], 0);
  const magnitudeA = Math.sqrt(a.reduce((sum, val) => sum + val * val, 0));
  const magnitudeB = Math.sqrt(b.reduce((sum, val) => sum + val * val, 0));
  
  if (magnitudeA === 0 || magnitudeB === 0) return 0;
  
  return dotProduct / (magnitudeA * magnitudeB);
}
