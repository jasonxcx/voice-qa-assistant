import { Response } from 'express';

export interface SSEManagerOptions {
  retry?: number;
}

/**
 * Server-Sent Events Manager
 * Handles streaming responses to clients
 */
export class SSEManager {
  private res: Response;
  private eventId: number = 0;
  private aborted: boolean = false;
  
  constructor(response: Response) {
    this.res = response;
    this.setupHeaders();
  }
  
  private setupHeaders(): void {
    this.res.setHeader('Content-Type', 'text/event-stream');
    this.res.setHeader('Cache-Control', 'no-cache');
    this.res.setHeader('Connection', 'keep-alive');
    this.res.setHeader('X-Accel-Buffering', 'no'); // Disable nginx buffering
    this.res.flushHeaders();
  }
  
  /**
   * Send a named event with data
   */
  sendEvent(eventType: string, data: any): void {
    if (this.aborted) return;
    
    this.eventId++;
    
    let eventString = `id: ${this.eventId}\n`;
    eventString += `event: ${eventType}\n`;
    eventString += `data: ${JSON.stringify(data)}\n\n`;
    
    this.res.write(eventString);
  }
  
  /**
   * Send a token delta (most common use case)
   */
  sendToken(token: string): void {
    this.sendEvent('token', { text: token });
  }
  
  /**
   * Send an error event
   */
  sendError(error: string): void {
    this.sendEvent('error', { message: error });
    this.end();
  }
  
  /**
   * Send completion event with usage stats
   */
  sendComplete(usage?: any): void {
    this.sendEvent('complete', { usage });
    this.end();
  }
  
  /**
   * End the stream
   */
  end(): void {
    this.aborted = true;
    this.res.end();
  }
  
  /**
   * Register callback for when client disconnects
   */
  onAborted(callback: () => void): void {
    this.res.on('close', callback);
  }
  
  /**
   * Check if stream is still active
   */
  isAborted(): boolean {
    return this.aborted;
  }
}

/**
 * Format SSE data string
 */
export function formatSSE(data: any): string {
  return `data: ${JSON.stringify(data)}\n\n`;
}
