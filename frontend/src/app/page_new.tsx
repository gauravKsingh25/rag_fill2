'use client';

import { useState } from 'react';
import DeviceSelector from '@/components/DeviceSelector';
import ChatInterface from '@/components/ChatInterface';
import DocumentUpload from '@/components/DocumentUpload';
import TemplateProcessor from '@/components/TemplateProcessor';

export default function Home() {
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'template'>('chat');

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
            <div className="tab-nav" role="tablist" aria-label="Main tabs">
              <nav className="flex items-center w-full">
                <button onClick={() => setActiveTab('chat')} className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}>Chat Interface</button>
                <button onClick={() => setActiveTab('upload')} className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}>Document Upload</button>
                <button onClick={() => setActiveTab('template')} className={`tab-btn ${activeTab === 'template' ? 'active' : ''}`}>Template Processor</button>
              </nav>
            </div>

            {/* Tab Content */}
            <div className="mt-6">
              {activeTab === 'chat' && (
                <ChatInterface deviceId={selectedDevice} />
              )}
              {activeTab === 'upload' && (
                <DocumentUpload deviceId={selectedDevice} />
              )}
              {activeTab === 'template' && (
                <TemplateProcessor deviceId={selectedDevice} />
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
                