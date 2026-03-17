import React, { useState } from 'react';
import { useChat } from './hooks/useChat';

const PROVIDERS = [
  { id: 'openai', name: 'OpenAI', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'] },
  { id: 'anthropic', name: 'Claude', models: ['claude-sonnet-4', 'claude-3-5-sonnet'] },
  { id: 'qwen', name: 'Qwen', models: ['qwen-plus', 'qwen-max', 'qwq-32b'] },
  { id: 'kimi', name: 'Kimi', models: ['kimi-k2-turbo-preview'] },
  { id: 'glm', name: 'GLM', models: ['glm-4', 'glm-4-flash'] },
  { id: 'ernie', name: 'ERNIE', models: ['ernie-4.0-8k'] },
];

export default function App() {
  const [input, setInput] = useState('');
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [selectedModel, setSelectedModel] = useState('gpt-4o');
  
  const { messages, isLoading, error, sendMessage, clearMessages } = useChat({
    provider: selectedProvider as any,
    model: selectedModel,
  });
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    
    const message = input;
    setInput('');
    await sendMessage(message);
  };
  
  const currentProvider = PROVIDERS.find(p => p.id === selectedProvider);
  
  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <header style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Interview Helper</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <select
            value={selectedProvider}
            onChange={(e) => {
              setSelectedProvider(e.target.value);
              const provider = PROVIDERS.find(p => p.id === e.target.value);
              setSelectedModel(provider?.models[0] || '');
            }}
            style={{ padding: '8px' }}
          >
            {PROVIDERS.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            style={{ padding: '8px' }}
          >
            {currentProvider?.models.map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <button onClick={clearMessages} style={{ padding: '8px 16px' }}>
            Clear
          </button>
        </div>
      </header>
      
      <div style={{ 
        border: '1px solid #ddd', 
        borderRadius: '8px', 
        height: '400px', 
        overflowY: 'auto',
        padding: '20px',
        marginBottom: '20px',
        backgroundColor: '#fafafa'
      }}>
        {messages.length === 0 && (
          <p style={{ color: '#666', textAlign: 'center' }}>
            Ask me anything about interview preparation!
          </p>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} style={{ 
            marginBottom: '16px',
            textAlign: msg.role === 'user' ? 'right' : 'left'
          }}>
            <div style={{ 
              display: 'inline-block',
              maxWidth: '70%',
              padding: '12px 16px',
              borderRadius: '12px',
              backgroundColor: msg.role === 'user' ? '#007bff' : '#fff',
              color: msg.role === 'user' ? '#fff' : '#333',
              border: msg.role === 'assistant' ? '1px solid #ddd' : 'none',
              whiteSpace: 'pre-wrap'
            }}>
              {msg.content}
              {msg.role === 'assistant' && idx === messages.length - 1 && isLoading && (
                <span style={{ animation: 'blink 1s infinite' }}>▊</span>
              )}
            </div>
          </div>
        ))}
        
        {error && (
          <div style={{ 
            padding: '12px', 
            backgroundColor: '#fee', 
            borderRadius: '8px',
            color: '#c00'
          }}>
            Error: {error.message}
          </div>
        )}
      </div>
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px' }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about interview questions, resume tips, or practice..."
          disabled={isLoading}
          style={{
            flex: 1,
            padding: '12px',
            borderRadius: '8px',
            border: '1px solid #ddd',
            resize: 'none',
            height: '60px',
            fontSize: '14px'
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
        />
        <button 
          type="submit" 
          disabled={isLoading || !input.trim()}
          style={{
            padding: '12px 24px',
            borderRadius: '8px',
            border: 'none',
            backgroundColor: isLoading ? '#ccc' : '#007bff',
            color: '#fff',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
      
      <style>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}
