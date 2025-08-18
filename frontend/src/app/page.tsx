'use client';

import { useState } from 'react';
import DeviceSelector from '@/components/DeviceSelector';
import ChatInterface from '@/components/ChatInterface';
import DocumentUpload from '@/components/DocumentUpload';
import TemplateProcessor from '@/components/TemplateProcessor';
import FavoritesSidebar from '@/components/FavoritesSidebar';
import FileHistory, { FileHistoryItem } from '@/components/FileHistory';

export default function Home() {
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'template' | 'history'>('chat');
  const [fileHistory, setFileHistory] = useState<FileHistoryItem[]>([]);

  // Endpoint management state
  const [endpointInput, setEndpointInput] = useState('');
  const [savedEndpoints, setSavedEndpoints] = useState<string[]>([]);

  // Postman-like GET request builder state
  const [getUrl, setGetUrl] = useState('');
  const [headers, setHeaders] = useState<{ key: string; value: string }[]>([]);
  const [body, setBody] = useState('');
  const [getResponse, setGetResponse] = useState<string>('');

  // Add endpoint to list
  const handleSaveEndpoint = () => {
    if (endpointInput && !savedEndpoints.includes(endpointInput)) {
      setSavedEndpoints([endpointInput, ...savedEndpoints]);
      setEndpointInput('');
    }
  };

  // Add header row
  const handleAddHeader = () => {
    setHeaders([...headers, { key: '', value: '' }]);
  };

  // Update header value
  const handleHeaderChange = (idx: number, field: 'key' | 'value', value: string) => {
    setHeaders(headers.map((h, i) => i === idx ? { ...h, [field]: value } : h));
  };

  // Remove header row
  const handleRemoveHeader = (idx: number) => {
    setHeaders(headers.filter((_, i) => i !== idx));
  };

  // Simulate GET request (dummy)
  const handleSendGet = () => {
    // Just show what would be sent
    setGetResponse(
      `GET ${getUrl}\nHeaders: ${JSON.stringify(headers.filter(h => h.key), null, 2)}\nBody: ${body}`
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Multi-Device RAG System</h1>
              <p className="text-gray-600 mt-1">Intelligent document processing and chat for isolated devices</p>
            </div>
            <DeviceSelector 
              selectedDevice={selectedDevice}
              onDeviceSelect={setSelectedDevice}
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!selectedDevice ? (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Device</h3>
            <p className="text-gray-600">Choose a device from the dropdown above to get started</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Tab Navigation */}
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8" aria-label="Tabs">
                <button
                  onClick={() => setActiveTab('chat')}
                  className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'chat'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Chat Interface
                </button>
                <button
                  onClick={() => setActiveTab('upload')}
                  className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'upload'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Document Upload
                </button>
                <button
                  onClick={() => setActiveTab('template')}
                  className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'template'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Template Processor
                </button>
                <button
                  onClick={() => setActiveTab('history')}
                  className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'history'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                  style={{marginLeft: 0}}
                >
                  File History
                </button>
              </nav>
            </div>

            {/* Tab Content */}
            <div className="mt-6">
              {activeTab === 'chat' && (
                <ChatInterface deviceId={selectedDevice} />
              )}
              {activeTab === 'upload' && (
                <div className="space-y-8">
                  {/* Endpoint Save UI */}
                  <div className="bg-gray-50 p-6 rounded shadow border">
                    <h2 className="text-2xl font-bold mb-2 text-gray-900">Save Endpoint</h2>
                    <div className="flex gap-2 mb-2">
                      <input
                        type="text"
                        className="border border-gray-300 rounded px-2 py-1 flex-1 text-gray-900 bg-white focus:border-blue-500 focus:outline-none"
                        placeholder="Enter endpoint URL..."
                        value={endpointInput}
                        onChange={e => setEndpointInput(e.target.value)}
                      />
                      <button
                        className="bg-blue-500 text-white px-4 py-1 rounded shadow hover:bg-blue-600 transition"
                        onClick={handleSaveEndpoint}
                      >Save</button>
                    </div>
                    {savedEndpoints.length > 0 && (
                      <div className="mt-2">
                        <h3 className="font-semibold mb-1 text-gray-900">Saved Endpoints:</h3>
                        <ul className="list-disc pl-5 text-sm text-gray-700">
                          {savedEndpoints.map((ep, idx) => (
                            <li key={idx}>{ep}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* GET Request Builder */}
                  <div className="bg-gray-50 p-6 rounded shadow border">
                    <h2 className="text-2xl font-bold mb-2 text-gray-900">GET Request Builder</h2>
                    <div className="mb-2">
                      <input
                        type="text"
                        className="border border-gray-300 rounded px-2 py-1 w-full text-gray-900 bg-white focus:border-blue-500 focus:outline-none"
                        placeholder="Enter GET endpoint URL..."
                        value={getUrl}
                        onChange={e => setGetUrl(e.target.value)}
                      />
                    </div>
                    <div className="mb-2">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-semibold text-gray-900">Headers</span>
                        <button
                          className="bg-gray-200 px-2 py-1 rounded text-xs text-gray-900 hover:bg-gray-300 transition"
                          onClick={handleAddHeader}
                        >Add Header</button>
                      </div>
                      {headers.map((h, idx) => (
                        <div key={idx} className="flex gap-2 mb-1">
                          <input
                            type="text"
                            className="border border-gray-300 rounded px-2 py-1 flex-1 text-gray-900 bg-white focus:border-blue-500 focus:outline-none"
                            placeholder="Key"
                            value={h.key}
                            onChange={e => handleHeaderChange(idx, 'key', e.target.value)}
                          />
                          <input
                            type="text"
                            className="border border-gray-300 rounded px-2 py-1 flex-1 text-gray-900 bg-white focus:border-blue-500 focus:outline-none"
                            placeholder="Value"
                            value={h.value}
                            onChange={e => handleHeaderChange(idx, 'value', e.target.value)}
                          />
                          <button
                            className="text-red-500 text-xs hover:underline"
                            onClick={() => handleRemoveHeader(idx)}
                          >Remove</button>
                        </div>
                      ))}
                    </div>
                    <div className="mb-2">
                      <span className="font-semibold text-gray-900">Body (JSON)</span>
                      <textarea
                        className="border border-gray-300 rounded px-2 py-1 w-full mt-1 text-gray-900 bg-white focus:border-blue-500 focus:outline-none"
                        rows={3}
                        placeholder="Enter JSON body (for GET, usually empty)"
                        value={body}
                        onChange={e => setBody(e.target.value)}
                      />
                    </div>
                    <button
                      className="bg-green-500 text-white px-4 py-1 rounded shadow hover:bg-green-600 transition"
                      onClick={handleSendGet}
                    >Send GET</button>
                    {getResponse && (
                      <div className="mt-4 bg-gray-100 p-3 rounded text-sm">
                        <span className="font-semibold text-gray-900">Simulated Response:</span>
                        <pre className="mt-1 whitespace-pre-wrap text-gray-700">{getResponse}</pre>
                      </div>
                    )}
                  </div>

                  {/* Existing Document Upload UI */}
                  <DocumentUpload deviceId={selectedDevice} />
                </div>
              )}
              {activeTab === 'template' && (
                <div className="flex gap-6">
                  <div className="flex-1">
                    <TemplateProcessor 
                      deviceId={selectedDevice}
                      onFileHistoryUpdate={(item: FileHistoryItem) => setFileHistory(prev => [item, ...prev])}
                    />
                  </div>
                  <div className="w-72">
                    <FavoritesSidebar />
                  </div>
                </div>
              )}
              {activeTab === 'history' && (
                <FileHistory history={fileHistory} />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
