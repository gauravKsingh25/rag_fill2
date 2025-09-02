'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FiUpload, 
  FiCheck, 
  FiX, 
  FiLoader, 
  FiFile, 
  FiDownload, 
  FiRefreshCw,
  FiChevronDown,
  FiChevronRight,
  FiZap,
  FiDatabase,
  FiFileText,
  FiPackage,
  FiCheckCircle,
  FiAlertCircle,
  FiInfo
} from 'react-icons/fi';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface InterpretedFormProps {
  deviceId: string;
}

interface PersonData {
  person_id: string;
  filename: string;
  status: 'uploading' | 'uploaded' | 'error';
}

interface TemplateAnalysis {
  template_info: {
    filename: string;
    estimated_fields: number;
    template_type: string;
  };
  identified_fields: Array<{
    field_id: string;
    field_type: string;
    context: string;
    description: string;
    required: boolean;
    suggestions: string[];
  }>;
}

interface Template {
  filename: string;
  status: 'analyzing' | 'analyzed' | 'error';
  analysis?: TemplateAnalysis;
}

interface GeneratedDocument {
  success: boolean;
  template_index: number;
  filename: string;
  download_url: string;
  filled_fields: Record<string, unknown>;
  fields_found: number;
  total_fields: number;
}

const containerVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.4 }
  }
};

export default function InterpretedForm({ deviceId }: InterpretedFormProps) {
  const [personData, setPersonData] = useState<PersonData | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [generatedDocs, setGeneratedDocs] = useState<GeneratedDocument[]>([]);
  const [batchDownloadUrl, setBatchDownloadUrl] = useState<string>('');
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [expandedTemplate, setExpandedTemplate] = useState<number | null>(null);

  const handlePersonDataUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('device_id', deviceId);
      formData.append('data_file', file);

      const response = await fetch('http://localhost:8000/api/interpreted-forms/upload-person-data/', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        setPersonData({
          person_id: result.person_id,
          filename: file.name,
          status: 'uploaded'
        });
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error('Error uploading person data:', error);
      setPersonData({
        person_id: '',
        filename: file.name,
        status: 'error'
      });
    } finally {
      setUploading(false);
    }
  };

  const handleTemplateUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    if (files.length > 5) {
      alert('Maximum 5 templates allowed');
      return;
    }

    setAnalyzing(true);
    const newTemplates: Template[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const template: Template = {
        filename: file.name,
        status: 'analyzing'
      };
      newTemplates.push(template);

      try {
        const formData = new FormData();
        formData.append('device_id', deviceId);
        formData.append('template_file', file);

        const response = await fetch('http://localhost:8000/api/interpreted-forms/analyze-template/', {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const result = await response.json();
          template.status = 'analyzed';
          template.analysis = result.template_analysis;
        } else {
          template.status = 'error';
        }
      } catch (error) {
        console.error(`Error analyzing template ${file.name}:`, error);
        template.status = 'error';
      }
    }

    setTemplates(newTemplates);
    setAnalyzing(false);
  };

  const handleGenerateForms = async () => {
    if (!personData || !templates.length) return;

    setGenerating(true);
    try {
      const templatesData = templates
        .filter(t => t.status === 'analyzed' && t.analysis)
        .map(t => ({ template_analysis: t.analysis }));

      const formData = new FormData();
      formData.append('device_id', deviceId);
      formData.append('person_id', personData.person_id);
      formData.append('templates_data', JSON.stringify(templatesData));

      const response = await fetch('http://localhost:8000/api/interpreted-forms/generate-forms/', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        setGeneratedDocs(result.filled_documents);
        if (result.download_links.length > 1) {
          setBatchDownloadUrl(result.download_links[result.download_links.length - 1]);
        }
      } else {
        throw new Error('Form generation failed');
      }
    } catch (error) {
      console.error('Error generating forms:', error);
    } finally {
      setGenerating(false);
    }
  };

  const canGenerate = personData?.status === 'uploaded' && 
                     templates.some(t => t.status === 'analyzed') && 
                     !generating;

  const clearAll = () => {
    setPersonData(null);
    setTemplates([]);
    setGeneratedDocs([]);
    setBatchDownloadUrl('');
    setExpandedTemplate(null);
  };

  const toggleTemplateExpansion = (index: number) => {
    setExpandedTemplate(expandedTemplate === index ? null : index);
  };

  // Progress steps data
  const progressSteps = [
    { step: 1, title: 'Upload Data', icon: FiUpload, completed: personData?.status === 'uploaded' },
    { step: 2, title: 'Analyze Templates', icon: FiFileText, completed: templates.some(t => t.status === 'analyzed') },
    { step: 3, title: 'Generate Forms', icon: FiZap, completed: generatedDocs.length > 0 }
  ];

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="w-full space-y-6"
    >
      {/* Progress Steps Card */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className="p-2 bg-gradient-to-br from-blue-100 to-purple-100 rounded-lg">
                <FiZap className="h-5 w-5 text-blue-600" />
              </div>
              <span>AI Form Intelligence</span>
            </CardTitle>
            <CardDescription>
              Upload person data to Pinecone vector database, analyze form templates with AI, 
              and automatically generate filled documents. Supports up to 5 templates per batch.
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            {/* Progress Steps */}
            <div className="flex items-center justify-between">
              {progressSteps.map((item, index) => (
                <React.Fragment key={item.step}>
                  <div className="flex items-center gap-3">
                    <div className={`flex items-center gap-3 transition-all duration-500 ${
                      item.completed ? 'text-green-600' : 'text-gray-400'
                    }`}>
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-500 ${
                        item.completed 
                          ? 'bg-green-100 text-green-600 shadow-lg shadow-green-200/50' 
                          : 'bg-gray-100 text-gray-400'
                      }`}>
                        {item.completed ? <FiCheck className="w-6 h-6" /> : React.createElement(item.icon, { className: "w-6 h-6" })}
                      </div>
                      <div>
                        <div className="font-semibold">{item.title}</div>
                        <div className="text-sm opacity-60">Step {item.step}</div>
                      </div>
                    </div>
                  </div>
                  {index < progressSteps.length - 1 && (
                    <div className={`flex-1 h-0.5 mx-4 transition-all duration-500 ${
                      item.completed ? 'bg-green-200' : 'bg-gray-200'
                    }`}></div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Step 1: Upload Person Data */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <FiDatabase className="h-5 w-5 text-blue-600" />
              </div>
              <span>Upload Person Data</span>
              {personData?.status === 'uploaded' && (
                <Badge variant="success">Uploaded to Pinecone</Badge>
              )}
            </CardTitle>
            <CardDescription>
              Select person data file (JSON, CSV, TXT, PDF, DOCX) to upload to Pinecone vector database
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            <div className="space-y-6">
              {/* File Upload Area */}
              <div className="relative group">
                <input
                  type="file"
                  accept=".json,.csv,.txt,.pdf,.docx"
                  onChange={handlePersonDataUpload}
                  disabled={uploading}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed z-10"
                />
                <motion.div 
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
                    uploading 
                      ? 'border-blue-300 bg-blue-50' 
                      : 'border-gray-300 bg-gray-50 group-hover:border-blue-400 group-hover:bg-blue-50'
                  }`}
                >
                  <div className="flex flex-col items-center gap-4">
                    <motion.div
                      animate={uploading ? { rotate: 360 } : {}}
                      transition={{ duration: 1, repeat: uploading ? Infinity : 0, ease: "linear" }}
                    >
                      {uploading ? (
                        <FiLoader className="w-8 h-8 text-blue-500" />
                      ) : (
                        <FiUpload className="w-8 h-8 text-gray-400 group-hover:text-blue-500 transition-colors" />
                      )}
                    </motion.div>
                    <div>
                      <div className="font-medium text-gray-700">
                        {uploading ? 'Uploading to Pinecone...' : 'Click to upload or drag and drop'}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        JSON, CSV, TXT, PDF, DOCX files supported
                      </div>
                    </div>
                  </div>
                </motion.div>
              </div>

              {/* Person Data Status */}
              <AnimatePresence>
                {personData && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className={`p-4 rounded-lg border ${
                      personData.status === 'uploaded' 
                        ? 'bg-green-50 border-green-200' : 
                      personData.status === 'error' 
                        ? 'bg-red-50 border-red-200' : 
                        'bg-blue-50 border-blue-200'
                    }`}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                        personData.status === 'uploaded' ? 'bg-green-100' : 
                        personData.status === 'error' ? 'bg-red-100' : 'bg-blue-100'
                      }`}>
                        {personData.status === 'uploaded' ? (
                          <FiCheckCircle className="w-5 h-5 text-green-600" />
                        ) : personData.status === 'error' ? (
                          <FiX className="w-5 h-5 text-red-600" />
                        ) : (
                          <FiLoader className="w-5 h-5 text-blue-600 animate-spin" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="font-semibold text-gray-900">{personData.filename}</div>
                        <div className="text-sm text-gray-600 mt-1">
                          Status: <span className="capitalize">{personData.status}</span>
                          {personData.status === 'uploaded' && personData.person_id && (
                            <Badge variant="secondary" className="ml-2">
                              ID: {personData.person_id}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Step 2: Upload Templates */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <FiFileText className="h-5 w-5 text-purple-600" />
              </div>
              <span>Upload Templates (Max 5)</span>
              {templates.length > 0 && (
                <Badge variant="secondary">
                  {templates.filter(t => t.status === 'analyzed').length}/{templates.length} analyzed
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Select template files (DOCX, PDF, TXT) to analyze with AI for field identification
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            <div className="space-y-6">
              {/* Template Upload Area */}
              <div className="relative group">
                <input
                  type="file"
                  accept=".docx,.pdf,.txt"
                  multiple
                  onChange={handleTemplateUpload}
                  disabled={analyzing}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed z-10"
                />
                <motion.div 
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
                    analyzing 
                      ? 'border-purple-300 bg-purple-50' 
                      : 'border-gray-300 bg-gray-50 group-hover:border-purple-400 group-hover:bg-purple-50'
                  }`}
                >
                  <div className="flex flex-col items-center gap-4">
                    <motion.div
                      animate={analyzing ? { rotate: 360 } : {}}
                      transition={{ duration: 1, repeat: analyzing ? Infinity : 0, ease: "linear" }}
                    >
                      {analyzing ? (
                        <FiLoader className="w-8 h-8 text-purple-500" />
                      ) : (
                        <FiUpload className="w-8 h-8 text-gray-400 group-hover:text-purple-500 transition-colors" />
                      )}
                    </motion.div>
                    <div>
                      <div className="font-medium text-gray-700">
                        {analyzing ? 'Analyzing templates with AI...' : 'Upload multiple templates'}
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        DOCX, PDF, TXT files • Maximum 5 files
                      </div>
                    </div>
                  </div>
                </motion.div>
              </div>

              {/* Template Analysis Results */}
              {templates.length > 0 && (
                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-700 flex items-center gap-2">
                    <FiZap className="w-4 h-4" />
                    Template Analysis Results
                  </h4>
                  <AnimatePresence mode="popLayout">
                    {templates.map((template, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className={`border rounded-xl overflow-hidden transition-all duration-300 hover:shadow-lg ${
                          template.status === 'analyzed' ? 'border-green-200 bg-green-50/50' :
                          template.status === 'error' ? 'border-red-200 bg-red-50/50' : 
                          'border-blue-200 bg-blue-50/50'
                        }`}
                      >
                        <div className="p-6">
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                                template.status === 'analyzed' ? 'bg-green-100' :
                                template.status === 'error' ? 'bg-red-100' : 'bg-blue-100'
                              }`}>
                                {template.status === 'analyzed' ? (
                                  <FiCheckCircle className="w-5 h-5 text-green-600" />
                                ) : template.status === 'error' ? (
                                  <FiAlertCircle className="w-5 h-5 text-red-600" />
                                ) : (
                                  <FiLoader className="w-5 h-5 text-blue-600 animate-spin" />
                                )}
                              </div>
                              <div>
                                <span className="font-semibold text-gray-900">{template.filename}</span>
                                <div className="text-sm text-gray-500">Template {index + 1}</div>
                              </div>
                            </div>
                            <div className="flex items-center gap-3">
                              <Badge variant={
                                template.status === 'analyzed' ? 'success' :
                                template.status === 'error' ? 'destructive' : 
                                'secondary'
                              }>
                                {template.status}
                              </Badge>
                              {template.analysis && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => toggleTemplateExpansion(index)}
                                  className="h-8 w-8 p-0"
                                >
                                  {expandedTemplate === index ? (
                                    <FiChevronDown className="w-4 h-4" />
                                  ) : (
                                    <FiChevronRight className="w-4 h-4" />
                                  )}
                                </Button>
                              )}
                            </div>
                          </div>
                          
                          {template.analysis && (
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
                              <div className="flex items-center gap-2 text-sm text-gray-600">
                                <FiInfo className="w-4 h-4" />
                                <span><strong>Type:</strong> {template.analysis.template_info.template_type}</span>
                              </div>
                              <div className="flex items-center gap-2 text-sm text-gray-600">
                                <FiFileText className="w-4 h-4" />
                                <span><strong>Fields:</strong> {template.analysis.identified_fields.length}</span>
                              </div>
                              <div className="flex items-center gap-2 text-sm text-gray-600">
                                <FiCheckCircle className="w-4 h-4" />
                                <span><strong>Required:</strong> {template.analysis.identified_fields.filter(f => f.required).length}</span>
                              </div>
                            </div>
                          )}
                          
                          {/* Expandable Field Details */}
                          <AnimatePresence>
                            {template.analysis && expandedTemplate === index && (
                              <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="border-t pt-4 space-y-3 max-h-64 overflow-y-auto"
                              >
                                <h5 className="font-medium text-gray-700 mb-3">Identified Fields:</h5>
                                {template.analysis.identified_fields.map((field, fieldIndex) => (
                                  <div key={fieldIndex} className="bg-white/70 p-4 rounded-lg border border-gray-200">
                                    <div className="flex items-center gap-2 mb-2">
                                      <span className="font-semibold text-gray-800">{field.field_id}</span>
                                      <Badge variant="outline">{field.field_type}</Badge>
                                      {field.required && (
                                        <Badge variant="destructive">Required</Badge>
                                      )}
                                    </div>
                                    <div className="text-sm text-gray-600 mb-1">{field.description}</div>
                                    {field.context && (
                                      <div className="text-xs text-gray-500 italic">Context: {field.context}</div>
                                    )}
                                  </div>
                                ))}
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Step 3: Generate Forms */}
      <motion.div variants={itemVariants}>
        <Card className="hover:shadow-lg transition-all duration-300">
          <CardHeader>
            <CardTitle className="flex items-center space-x-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <FiZap className="h-5 w-5 text-green-600" />
              </div>
              <span>Generate Filled Forms</span>
            </CardTitle>
            <CardDescription>
              Use uploaded person data and analyzed templates to generate filled documents
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            <div className="space-y-6">
              <div className="flex gap-4">
                <Button
                  onClick={handleGenerateForms}
                  disabled={!canGenerate}
                  className="flex items-center space-x-2"
                >
                  {generating ? (
                    <>
                      <FiLoader className="w-4 h-4 animate-spin" />
                      <span>Generating Forms...</span>
                    </>
                  ) : (
                    <>
                      <FiZap className="w-4 h-4" />
                      <span>Generate Filled Forms</span>
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={clearAll}
                  className="flex items-center space-x-2"
                >
                  <FiRefreshCw className="w-4 h-4" />
                  <span>Clear All</span>
                </Button>
              </div>

              {!canGenerate && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="p-4 bg-amber-50 border border-amber-200 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <FiInfo className="w-5 h-5 text-amber-600" />
                    <span className="font-medium text-amber-800">
                      {!personData ? 'Please upload person data first.' :
                       personData.status !== 'uploaded' ? 'Person data upload in progress.' :
                       !templates.some(t => t.status === 'analyzed') ? 'Please upload and analyze at least one template.' :
                       'Ready to generate forms.'}
                    </span>
                  </div>
                </motion.div>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Generated Documents */}
      <AnimatePresence>
        {generatedDocs.length > 0 && (
          <motion.div
            variants={itemVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
          >
            <Card className="hover:shadow-lg transition-all duration-300">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center space-x-3">
                      <div className="p-2 bg-orange-100 rounded-lg">
                        <FiPackage className="h-5 w-5 text-orange-600" />
                      </div>
                      <span>Generated Documents</span>
                    </CardTitle>
                    <CardDescription>
                      Successfully generated documents are ready for download
                    </CardDescription>
                  </div>
                  {batchDownloadUrl && (
                    <Button asChild>
                      <a
                        href={`http://localhost:8000${batchDownloadUrl}`}
                        download
                        className="flex items-center space-x-2"
                      >
                        <FiDownload className="w-4 h-4" />
                        <span>Download All (ZIP)</span>
                      </a>
                    </Button>
                  )}
                </div>
              </CardHeader>
              
              <CardContent>
                <div className="space-y-4">
                  <AnimatePresence mode="popLayout">
                    {generatedDocs.map((doc, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className={`p-5 rounded-xl border transition-all duration-300 hover:shadow-lg ${
                          doc.success ? 'border-green-200 bg-green-50/50' : 'border-red-200 bg-red-50/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                              doc.success ? 'bg-green-100' : 'bg-red-100'
                            }`}>
                              {doc.success ? (
                                <FiCheckCircle className="w-6 h-6 text-green-600" />
                              ) : (
                                <FiAlertCircle className="w-6 h-6 text-red-600" />
                              )}
                            </div>
                            <div>
                              <h4 className="font-semibold text-gray-900">{doc.filename}</h4>
                              <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                                <span>Template #{doc.template_index + 1}</span>
                                <span className="flex items-center gap-1">
                                  <FiFileText className="w-3 h-3" />
                                  {doc.fields_found}/{doc.total_fields} fields filled
                                </span>
                                <Badge variant={doc.success ? "success" : "destructive"}>
                                  {Math.round((doc.fields_found / doc.total_fields) * 100)}% complete
                                </Badge>
                              </div>
                            </div>
                          </div>
                          {doc.success && (
                            <Button variant="outline" size="sm" asChild>
                              <a
                                href={`http://localhost:8000${doc.download_url}`}
                                download
                                className="flex items-center space-x-2"
                              >
                                <FiDownload className="w-4 h-4" />
                                <span>Download</span>
                              </a>
                            </Button>
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
