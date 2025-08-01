// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

// Other constants can be added here as needed
export const SUPPORTED_FILE_TYPES = {
  TEMPLATE: ['.docx'],
  DOCUMENT: ['.pdf', '.docx', '.txt']
} as const;

export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
