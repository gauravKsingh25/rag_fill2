'use client';

import { useState, useRef, useEffect } from 'react';
import { chatApi, ApiError } from '@/lib/api';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string; // Changed from Date to string to avoid hydration issues
  sources?: Array<{
    filename: string;
    chunk_id: number;
    score: number;
    content_preview: string;
    document_number?: number;
    confidence_level?: string;
    document_id?: string;
  }>;
}

interface ChatInterfaceProps {
  deviceId: string;
}

export default function ChatInterface({ deviceId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (mounted) {
      scrollToBottom();
    }
  }, [messages, mounted]);

  useEffect(() => {
    // Clear messages when device changes
    setMessages([]);
    setError(null);
  }, [deviceId]);

  const renderFormattedText = (text: string) => {
    // Split text by lines and render with basic formatting
    const lines = text.split('\n');
    return lines.map((line, index) => {
      // Handle bold text
      if (line.includes('**')) {
        const parts = line.split('**');
        return (
          <div key={index} className="mb-1">
            {parts.map((part, partIndex) => 
              partIndex % 2 === 1 ? (
                <strong key={partIndex}>{part}</strong>
              ) : (
                <span key={partIndex}>{part}</span>
              )
            )}
          </div>
        );
      }
      
      // Handle bullet points
      if (line.startsWith('• ')) {
        return (
          <div key={index} className="ml-4 mb-1">
            <span className="text-blue-600">•</span> {line.substring(2)}
          </div>
        );
      }
      
      // Handle horizontal rules
      if (line.trim() === '---') {
        return <hr key={index} className="my-3 border-gray-300" />;
      }
      
      // Handle empty lines
      if (line.trim() === '') {
        return <div key={index} className="mb-2" />;
      }
      
      // Regular text
      return (
        <div key={index} className="mb-1">
          {line}
        </div>
      );
    });
  };

  const formatResponse = (content: string): string => {
    // Format the response to be more user-friendly
    let formatted = content;
    
    // Remove excessive technical formatting
    formatted = formatted.replace(/🎯 HIGH CONFIDENCE:/g, '✅ **High Confidence:**');
    formatted = formatted.replace(/✅ GOOD CONFIDENCE:/g, '✅ **Good Confidence:**');
    formatted = formatted.replace(/⚠️ MODERATE CONFIDENCE:/g, '⚠️ **Moderate Confidence:**');
    
    // Clean up document references to be more readable
    formatted = formatted.replace(/\[Document (\d+)\]/g, '**[Document $1]**');
    
    // Format bullet points better
    formatted = formatted.replace(/• /g, '\n• ');
    
    // Clean up analysis summary for better readability
    formatted = formatted.replace(/📊 ANALYSIS SUMMARY:/g, '\n---\n**📊 Analysis Summary:**');
    formatted = formatted.replace(/📊 COMPREHENSIVE ANALYSIS SUMMARY:/g, '\n---\n**📊 Comprehensive Analysis Summary:**');
    
    // Remove excessive newlines but preserve paragraph breaks
    formatted = formatted.replace(/\n{3,}/g, '\n\n');
    
    // Clean up confidence indicators
    formatted = formatted.replace(/CRITICAL|HIGH|GOOD|MODERATE/g, (match) => {
      switch(match) {
        case 'CRITICAL': return '🎯 Critical';
        case 'HIGH': return '✅ High';
        case 'GOOD': return '✅ Good';
        case 'MODERATE': return '⚠️ Moderate';
        default: return match;
      }
    });
    
    return formatted.trim();
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || loading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);
    setError(null);

    try {
      const data = await chatApi.send(deviceId, inputMessage, messages.slice(-10));

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: formatResponse(data.response),
        timestamp: new Date().toISOString(),
        sources: Array.isArray(data.sources) ? data.sources : []
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Chat error:', err);
      let errorMessage = 'Failed to send message';
      
      if (err instanceof ApiError) {
        errorMessage = err.message;
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      
      // Add error message to chat
      const errorChatMessage: ChatMessage = {
        role: 'assistant',
        content: `I'm sorry, but I encountered an error: ${errorMessage}. Please try again.`,
        timestamp: new Date().toISOString(),
        sources: []
      };
      setMessages(prev => [...prev, errorChatMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="card h-[600px] flex flex-col">
      <div className="border-b px-6 py-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Chat with Device {deviceId}
        </h3>
        <div className="text-sm text-muted mt-1">Ask specific questions about documents for best results.</div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-400 mb-2">
              <svg className="mx-auto h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-gray-600">Start a conversation by asking specific, fact-based questions about your documents</p>
            <div className="mt-4 text-sm text-muted">
              <p className="font-semibold mb-2">💡 Tips:</p>
              <ul className="space-y-1 text-left inline-block">
                <li>• Ask specific questions: &quot;What is the model number?&quot;</li>
                <li>• Use clear, direct phrasing</li>
                <li>• System will state when info is not available</li>
              </ul>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[72%] rounded-lg px-4 py-2 ${
                message.role === 'user' 
                  ? 'bg-[var(--primary)] text-white' 
                  : 'bg-gray-50 text-gray-900 border border-[var(--border)]'
              } shadow-sm`}>
                <div className="whitespace-pre-wrap text-sm">
                  {message.role === 'assistant' ? renderFormattedText(message.content) : message.content}
                </div>
                {message.sources && message.sources.length > 0 && (
                  <div className="mt-2 text-xs">
                    <div className="font-semibold mb-1">Sources ({message.sources.length}):</div>
                    {message.sources.map((source, idx) => (
                      <div key={idx} className="bg-white rounded p-2 mb-1 border border-[var(--border)]">
                        <div className="font-medium text-sm">
                          {source.document_number ? `[Doc ${source.document_number}] ` : ''}{source.filename || 'Unknown file'}
                        </div>
                        <div className="opacity-75 mb-1 text-xs">{source.content_preview || 'No preview available'}</div>
                        <div className="opacity-60 flex space-x-3 text-xs">
                          <span>Score: {typeof source.score === 'number' && !isNaN(source.score) ? source.score.toFixed(3) : 'N/A'}</span>
                          {source.confidence_level && <span>Confidence: {source.confidence_level}</span>}
                          {typeof source.chunk_id === 'number' && <span>Chunk: {source.chunk_id}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="text-xs opacity-60 mt-1 text-right">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-50 rounded-lg px-4 py-2 max-w-[70%] shadow-sm">
              <div className="flex items-center space-x-2 text-sm text-muted">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
                <span>Thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="border-t bg-red-50 px-6 py-3">
          <div className="text-red-700 text-sm">
            Error: {error}
          </div>
        </div>
      )}

      <div className="border-t p-4">
        <div className="flex space-x-4">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here..."
            rows={2}
            className="flex-1 resize-none border border-[var(--border)] rounded px-3 py-2 focus:outline-none"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || loading}
            className="btn-primary"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
