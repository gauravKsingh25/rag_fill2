'use client';

import { useState, useRef, useEffect } from 'react';

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
      // Add timeout to prevent endless waiting
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

      const response = await fetch('https://rag-fill2-1.onrender.com/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          device_id: deviceId,
          message: inputMessage,
          conversation_history: messages.slice(-10) // Last 10 messages for context
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const data = await response.json();

      // Validate response structure
      if (!data || typeof data.response !== 'string') {
        throw new Error('Invalid response format from server');
      }

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
      
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          errorMessage = 'Request timed out. The system is taking too long to respond. Please try a simpler question or check if documents are uploaded.';
        } else {
          errorMessage = err.message;
        }
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
    <div className="bg-white rounded-lg shadow-sm border h-[600px] flex flex-col">
      {/* Chat Header */}
      <div className="border-b px-6 py-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Chat with Device {deviceId} 
        </h3>
       
        
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-400 mb-2">
              <svg className="mx-auto h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-gray-600">Start a conversation by asking specific, fact-based questions about your documents</p>
            <div className="mt-4 text-sm text-gray-500">
              <p className="font-semibold mb-2">💡 Tips for Best Results:</p>
              <ul className="space-y-1">
                <li>• Ask specific questions: &quot;What is the model number?&quot; instead of &quot;Tell me about the device&quot;</li>
                <li>• Use clear, direct questions for better results</li>
                <li>• System will explicitly state when information is not available</li>
                <li>• Responses are based on your uploaded documents</li>
              </ul>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[70%] rounded-lg px-4 py-2 ${
                message.role === 'user' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 text-gray-900'
              }`}>
                <div className="whitespace-pre-wrap">
                  {message.role === 'assistant' ? renderFormattedText(message.content) : message.content}
                </div>
                {message.sources && message.sources.length > 0 && (
                  <div className="mt-2 text-xs">
                    <div className="font-semibold mb-1">Sources ({message.sources.length}):</div>
                    {message.sources.map((source, idx) => (
                      <div key={idx} className="bg-white bg-opacity-20 rounded p-2 mb-1">
                        <div className="font-medium">
                          {source.document_number ? `[Doc ${source.document_number}] ` : ''}{source.filename || 'Unknown file'}
                        </div>
                        <div className="opacity-75 mb-1">{source.content_preview || 'No preview available'}</div>
                        <div className="opacity-50 flex space-x-3">
                          <span>Score: {typeof source.score === 'number' && !isNaN(source.score) ? source.score.toFixed(3) : 'N/A'}</span>
                          {source.confidence_level && <span>Confidence: {source.confidence_level}</span>}
                          {typeof source.chunk_id === 'number' && <span>Chunk: {source.chunk_id}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="text-xs opacity-75 mt-1">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}
        
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2 max-w-[70%]">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600"></div>
                <span>Thinking...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Error Display */}
      {error && (
        <div className="border-t bg-red-50 px-6 py-3">
          <div className="text-red-700 text-sm">
            Error: {error}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="flex space-x-4">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here..."
            rows={2}
            className="flex-1 resize-none border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
