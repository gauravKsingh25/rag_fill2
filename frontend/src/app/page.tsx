'use client';

import { useState, useEffect } from 'react';
import DeviceSelector from '@/components/DeviceSelector';
import InterpretedForm from '@/components/InterpretedForm';
import DocumentUpload from '@/components/DocumentUpload';
import TemplateProcessor from '@/components/TemplateProcessor';
import FavoritesSidebar from '@/components/FavoritesSidebar';
import FileHistory, { FileHistoryItem } from '@/components/FileHistory';
import { API_BASE_URL } from '@/config/api';

export default function Home() {
	const [selectedDevice, setSelectedDevice] = useState<string>('');
	const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'template' | 'history'>('chat');
	const [fileHistory, setFileHistory] = useState<FileHistoryItem[]>([]);

	// Load file history when component mounts
	useEffect(() => {
		const loadFileHistory = async () => {
			try {
				const response = await fetch(`${API_BASE_URL}/api/file-history/`);
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
		<div className="min-h-screen">
			{/* Header */}
			<header className="bg-white/90 backdrop-blur-lg shadow-sm border-b border-gray-200 sticky top-16 z-40">
				<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
					<div className="flex flex-col sm:flex-row sm:justify-between sm:items-center py-6 gap-4">
						<div className="animate-in slide-in-from-left duration-500">
							<h1 className="text-3xl font-bold text-gray-900 leading-tight">
								Multi-Device RAG System
							</h1>
							<p className="text-gray-600 mt-2 max-w-2xl">
								Intelligent document processing and chat for isolated devices with advanced AI capabilities
							</p>
						</div>
						<div className="animate-in slide-in-from-right duration-500 flex-shrink-0">
							<DeviceSelector 
								selectedDevice={selectedDevice}
								onDeviceSelect={setSelectedDevice}
							/>
						</div>
					</div>
				</div>
			</header>

			{/* Main Content */}
			<main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
				{!selectedDevice ? (
					<div className="text-center py-16 animate-in fade-in duration-500">
						<div className="max-w-md mx-auto">
							<div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-br from-blue-100 to-blue-200 rounded-2xl flex items-center justify-center animate-float">
								<svg className="w-12 h-12 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
									<path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
								</svg>
							</div>
							<h3 className="text-xl font-semibold text-gray-900 mb-3">Select a Device to Begin</h3>
							<p className="text-gray-600 leading-relaxed">
								Choose a device from the dropdown above to access intelligent document processing, 
								template filling, and advanced AI-powered chat capabilities.
							</p>
							<div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
								<p className="text-sm text-blue-700 font-medium">
									💡 Each device maintains isolated knowledge bases for enhanced security and organization
								</p>
							</div>
						</div>
					</div>
				) : (
					<div className="space-y-8 animate-in fade-in duration-500">
						{/* Enhanced Tab Navigation */}
						<div className="bg-white/80 backdrop-blur-lg rounded-2xl p-2 shadow-lg border border-gray-200/50">
							<nav className="flex items-center w-full gap-2">
								<button
									onClick={() => setActiveTab('chat')}
									className={`
										flex items-center gap-3 px-5 py-3 rounded-xl font-medium text-sm transition-all duration-200 flex-1 min-w-0 relative
										${activeTab === 'chat' 
											? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg shadow-blue-500/25 transform scale-[1.02]' 
											: 'text-gray-600 hover:text-gray-900 hover:bg-white/70'
										}
									`}
								>
									<svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
										<path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
									</svg>
									<span className="truncate">Intelligent Forms</span>
									{activeTab === 'chat' && (
										<div className="absolute inset-0 bg-gradient-to-r from-blue-400/20 to-blue-600/20 rounded-xl" />
									)}
								</button>

								<button
									onClick={() => setActiveTab('upload')}
									className={`
										flex items-center gap-3 px-5 py-3 rounded-xl font-medium text-sm transition-all duration-200 flex-1 min-w-0 relative
										${activeTab === 'upload' 
											? 'bg-gradient-to-r from-green-500 to-green-600 text-white shadow-lg shadow-green-500/25 transform scale-[1.02]' 
											: 'text-gray-600 hover:text-gray-900 hover:bg-white/70'
										}
									`}
								>
									<svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
										<path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
									</svg>
									<span className="truncate">Document Upload</span>
									{activeTab === 'upload' && (
										<div className="absolute inset-0 bg-gradient-to-r from-green-400/20 to-green-600/20 rounded-xl" />
									)}
								</button>

								<button
									onClick={() => setActiveTab('template')}
									className={`
										flex items-center gap-3 px-5 py-3 rounded-xl font-medium text-sm transition-all duration-200 flex-1 min-w-0 relative
										${activeTab === 'template' 
											? 'bg-gradient-to-r from-purple-500 to-purple-600 text-white shadow-lg shadow-purple-500/25 transform scale-[1.02]' 
											: 'text-gray-600 hover:text-gray-900 hover:bg-white/70'
										}
									`}
								>
									<svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
										<path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
									</svg>
									<span className="truncate">Template Processor</span>
									{activeTab === 'template' && (
										<div className="absolute inset-0 bg-gradient-to-r from-purple-400/20 to-purple-600/20 rounded-xl" />
									)}
								</button>

								{/* Spacer */}
								<div className="flex-1" />

								<button
									onClick={() => setActiveTab('history')}
									className={`
										flex items-center gap-3 px-5 py-3 rounded-xl font-medium text-sm transition-all duration-200 min-w-0 relative
										${activeTab === 'history' 
											? 'bg-gradient-to-r from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/25 transform scale-[1.02]' 
											: 'text-gray-600 hover:text-gray-900 hover:bg-white/70'
										}
									`}
								>
									<svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
										<path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
									<span className="truncate">File History</span>
									{activeTab === 'history' && (
										<div className="absolute inset-0 bg-gradient-to-r from-orange-400/20 to-orange-600/20 rounded-xl" />
									)}
								</button>
							</nav>
						</div>

						<div className="mt-6">
							{activeTab === 'chat' && <InterpretedForm deviceId={selectedDevice} />}

							{activeTab === 'upload' && (
								<div className="space-y-8">

									<DocumentUpload deviceId={selectedDevice} />
									{/* Save Endpoint UI (collapsible) */}
									<div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
										<div className="flex items-start justify-between">
											<div>
												<h2 className="text-xl font-semibold text-gray-900">Save Endpoint</h2>
												<div className="text-sm text-gray-600 mt-1">Keep frequently used service endpoints here for quick access.</div>
											</div>
											<button
												onClick={() => setEndpointsOpen(!endpointsOpen)}
												aria-expanded={endpointsOpen}
												className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200"
											>
												{endpointsOpen ? 'Collapse' : 'Expand'}
											</button>
										</div>

										{endpointsOpen && (
											<div className="mt-4">
												<div className="mt-4 flex gap-3 items-center">
													<input
														type="text"
														className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
														placeholder="Enter endpoint URL..."
														value={endpointInput}
														onChange={e => setEndpointInput(e.target.value)}
													/>
													<button
														className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200"
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
									<div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
										<div className="flex items-start justify-between">
											<div>
												<h2 className="text-xl font-semibold text-gray-900">GET Request Builder</h2>
												<div className="text-sm text-gray-600 mt-1">Build and preview a GET request (headers and body are illustrative).</div>
											</div>
											<button
												onClick={() => setGetBuilderOpen(!getBuilderOpen)}
												aria-expanded={getBuilderOpen}
												className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors duration-200"
											>
												{getBuilderOpen ? 'Collapse' : 'Expand'}
											</button>
										</div>

										{getBuilderOpen && (
											<div className="mt-4">
												<div>
													<input
														type="text"
														className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
														placeholder="Enter GET endpoint URL..."
														value={getUrl}
														onChange={e => setGetUrl(e.target.value)}
													/>
												</div>

												<div className="mt-4">
													<div className="flex items-center justify-between mb-2">
														<span className="font-semibold text-gray-900">Headers</span>
														<button className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors" onClick={handleAddHeader}>Add Header</button>
													</div>
													{headers.map((h, idx) => (
														<div key={idx} className="flex gap-2 mb-2">
															<input
																type="text"
																className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
																placeholder="Key"
																value={h.key}
																onChange={e => handleHeaderChange(idx, 'key', e.target.value)}
															/>
															<input
																type="text"
																className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
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
														className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors mt-2"
														rows={4}
														placeholder="Enter JSON body (for GET, usually empty)"
														value={body}
														onChange={e => setBody(e.target.value)}
													/>
												</div>

												<div className="mt-4 flex items-center gap-3">
													<button className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200" onClick={handleSendGet}>Send GET</button>
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

