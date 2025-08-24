'use client';

import { useState, useEffect } from 'react';
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

	// Load file history when component mounts
	useEffect(() => {
		const loadFileHistory = async () => {
			try {
				const response = await fetch('http://localhost:8000/api/file-history/');
				if (response.ok) {
					const history = await response.json();
					setFileHistory(history);
					console.log('Loaded file history:', history);
				} else {
					console.error('Failed to load file history:', response.statusText);
				}
			} catch (error) {
				console.error('Error loading file history:', error);
			}
		};
		loadFileHistory();
	}, []);

	// Endpoint management state
	const [endpointInput, setEndpointInput] = useState('');
	const [savedEndpoints, setSavedEndpoints] = useState<string[]>([]);

	// Postman-like GET request builder state
	const [getUrl, setGetUrl] = useState('');
	const [headers, setHeaders] = useState<{ key: string; value: string }[]>([]);
	const [body, setBody] = useState('');
	const [getResponse, setGetResponse] = useState<string>('');

	// NEW: UI collapse states (closed by default)
	const [endpointsOpen, setEndpointsOpen] = useState(false);
	const [getBuilderOpen, setGetBuilderOpen] = useState(false);

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

	// Add small helpers for tab button styling
	// const tabBtnBase = 'py-2 px-3 text-sm rounded-md transition inline-flex items-center gap-2';
	// const tabBtnActive = 'bg-gradient-to-r from-indigo-50 to-white text-indigo-700 shadow-sm ring-1 ring-indigo-100';
	// const tabBtnInactive = 'text-gray-500 hover:bg-gray-50 hover:text-gray-700';

	return (
		<div className="min-h-screen bg-gradient-to-b from-gray-50 via-white to-gray-50">
			{/* Header */}
			<header className="bg-white shadow-sm border-b">
				<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
					<div className="flex justify-between items-center py-6">
						<div>
							<h1 className="text-2xl font-semibold text-gray-900">Multi-Device RAG System</h1>
							<p className="text-sm text-muted mt-1">Intelligent document processing and chat for isolated devices</p>
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
						<div className="tab-nav">
							<nav className="flex items-center w-full">
								<button
									onClick={() => setActiveTab('chat')}
									className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
								>
									Chat Interface
								</button>

								<button
									onClick={() => setActiveTab('upload')}
									className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
								>
									Document Upload
								</button>

								<button
									onClick={() => setActiveTab('template')}
									className={`tab-btn ${activeTab === 'template' ? 'active' : ''}`}
								>
									Template Processor
								</button>

								{/* spacer pushes history to the far right */}
								<div className="tab-spacer" />

								<button
									onClick={() => setActiveTab('history')}
									className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
								>
									File History
								</button>
							</nav>
						</div>

						<div className="mt-6">
							{activeTab === 'chat' && <ChatInterface deviceId={selectedDevice} />}

							{activeTab === 'upload' && (
								<div className="space-y-8">
									{/* Save Endpoint UI (collapsible) */}
									<div className="card p-6">
										<div className="flex items-start justify-between">
											<div>
												<h2 className="section-title">Save Endpoint</h2>
												<div className="text-sm text-muted">Keep frequently used service endpoints here for quick access.</div>
											</div>
											<button
												onClick={() => setEndpointsOpen(!endpointsOpen)}
												aria-expanded={endpointsOpen}
												className="btn-ghost text-sm"
											>
												{endpointsOpen ? 'Collapse' : 'Expand'}
											</button>
										</div>

										{endpointsOpen && (
											<div className="mt-4">
												<div className="mt-4 flex gap-3 items-center">
													<input
														type="text"
														className="input flex-1"
														placeholder="Enter endpoint URL..."
														value={endpointInput}
														onChange={e => setEndpointInput(e.target.value)}
													/>
													<button
														className="btn-primary"
														onClick={handleSaveEndpoint}
													>
														Save
													</button>
												</div>

												{savedEndpoints.length > 0 && (
													<div className="mt-4">
														<h3 className="font-semibold mb-2 text-gray-900">Saved Endpoints</h3>
														<ul className="space-y-1 text-sm">
															{savedEndpoints.map((ep, idx) => (
																<li key={idx} className="text-gray-700 truncate">{ep}</li>
															))}
														</ul>
													</div>
												)}
											</div>
										)}
									</div>

									{/* GET Request Builder (collapsible) */}
									<div className="card p-6">
										<div className="flex items-start justify-between">
											<div>
												<h2 className="section-title">GET Request Builder</h2>
												<div className="text-sm text-muted">Build and preview a GET request (headers and body are illustrative).</div>
											</div>
											<button
												onClick={() => setGetBuilderOpen(!getBuilderOpen)}
												aria-expanded={getBuilderOpen}
												className="btn-ghost text-sm"
											>
												{getBuilderOpen ? 'Collapse' : 'Expand'}
											</button>
										</div>

										{getBuilderOpen && (
											<div className="mt-4">
												<div>
													<input
														type="text"
														className="input"
														placeholder="Enter GET endpoint URL..."
														value={getUrl}
														onChange={e => setGetUrl(e.target.value)}
													/>
												</div>

												<div className="mt-4">
													<div className="flex items-center justify-between mb-2">
														<span className="font-semibold text-gray-900">Headers</span>
														<button className="btn-small" onClick={handleAddHeader}>Add Header</button>
													</div>
													{headers.map((h, idx) => (
														<div key={idx} className="flex gap-2 mb-2">
															<input
																type="text"
																className="input flex-1"
																placeholder="Key"
																value={h.key}
																onChange={e => handleHeaderChange(idx, 'key', e.target.value)}
															/>
															<input
																type="text"
																className="input flex-1"
																placeholder="Value"
																value={h.value}
																onChange={e => handleHeaderChange(idx, 'value', e.target.value)}
															/>
															<button
																className="text-red-500 text-xs hover:underline self-center"
																onClick={() => handleRemoveHeader(idx)}
															>
																Remove
															</button>
														</div>
													))}
												</div>

												<div className="mt-3">
													<label className="text-sm font-semibold text-gray-900">Body (JSON)</label>
													<textarea
														className="input mt-2"
														rows={4}
														placeholder="Enter JSON body (for GET, usually empty)"
														value={body}
														onChange={e => setBody(e.target.value)}
													/>
												</div>

												<div className="mt-4 flex items-center gap-3">
													<button className="btn-primary" onClick={handleSendGet}>Send GET</button>
													{getResponse && (
														<div className="ml-2 bg-gray-100 p-3 rounded text-sm flex-1">
															<span className="font-semibold text-gray-900">Simulated Response:</span>
															<pre className="mt-1 whitespace-pre-wrap text-gray-700">{getResponse}</pre>
														</div>
													)}
												</div>
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
											onFileHistoryUpdate={(item: FileHistoryItem) => {
												console.log('Received file history update in page:', item);
												setFileHistory(prev => [item, ...prev]);
												console.log('Updated file history state');
											}}
										/>
									</div>
									<div className="w-72">
										<FavoritesSidebar />
									</div>
								</div>
							)}

							{activeTab === 'history' && <FileHistory history={fileHistory} />}
						</div>
					</div>
				)}
			</main>
		</div>
	);
}

