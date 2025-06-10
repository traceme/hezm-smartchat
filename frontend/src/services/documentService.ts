import axios, { AxiosResponse } from 'axios';

// Types for document management
export interface Document {
  id: string;
  title: string;
  original_filename: string;
  document_type: 'pdf' | 'epub' | 'txt' | 'docx' | 'md';
  status: 'uploading' | 'processing' | 'ready' | 'error';
  file_size: number;
  file_size_display: string;
  page_count?: number;
  word_count?: number;
  language?: string;
  processing_progress?: number;
  processing_error?: string;
  created_at: string;
  updated_at?: string;
  processed_at?: string;
  category?: string; // Frontend-only field for now
  description?: string; // Frontend-only field for now
}

export interface DocumentListResponse {
  documents: Document[];
  total_count: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export interface DocumentUpdateRequest {
  title?: string;
}

export interface DocumentStats {
  total_documents: number;
  status_counts: Record<string, number>;
  type_counts: Record<string, number>;
  total_storage_bytes: number;
  total_storage_display: string;
}

// API configuration
const API_BASE = process.env.REACT_APP_API_URL || '';
const DOCUMENTS_API = `${API_BASE}/api/documents`;

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: DOCUMENTS_API,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for auth (when implemented)
apiClient.interceptors.request.use(
  (config) => {
    // TODO: Add authentication headers when auth is implemented
    // const token = localStorage.getItem('auth_token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Document Service class
class DocumentService {
  /**
   * Get list of documents with filtering and sorting
   */
  async getDocuments(params: {
    search?: string;
    status?: string;
    document_type?: string;
    category?: string;
    sort_by?: 'title' | 'created_at' | 'file_size' | 'status';
    sort_order?: 'asc' | 'desc';
    skip?: number;
    limit?: number;
  } = {}): Promise<DocumentListResponse> {
    try {
      const response: AxiosResponse<DocumentListResponse> = await apiClient.get('/', {
        params: {
          ...params,
          // Map frontend categories to backend (for now, just pass through)
          // In future, we might need to handle category mapping
        },
      });

      // Transform backend response to frontend format
      const transformedDocuments = response.data.documents.map(doc => ({
        ...doc,
        id: doc.id.toString(), // Convert to string for frontend consistency
        // Add frontend-only fields based on patterns in the data
        category: this.inferCategory(doc.title, doc.original_filename),
        description: this.generateDescription(doc),
      }));

      return {
        ...response.data,
        documents: transformedDocuments,
      };
    } catch (error) {
      console.error('Error fetching documents:', error);
      throw this.handleError(error);
    }
  }

  /**
   * Get a specific document by ID
   */
  async getDocument(documentId: string): Promise<Document> {
    try {
      const response: AxiosResponse<Document> = await apiClient.get(`/${documentId}`);
      
      return {
        ...response.data,
        id: response.data.id.toString(),
        category: this.inferCategory(response.data.title, response.data.original_filename),
        description: this.generateDescription(response.data),
      };
    } catch (error) {
      console.error('Error fetching document:', error);
      throw this.handleError(error);
    }
  }

  /**
   * Update document metadata
   */
  async updateDocument(documentId: string, updateData: DocumentUpdateRequest): Promise<Document> {
    try {
      const response: AxiosResponse<Document> = await apiClient.put(`/${documentId}`, updateData);
      
      return {
        ...response.data,
        id: response.data.id.toString(),
        category: this.inferCategory(response.data.title, response.data.original_filename),
        description: this.generateDescription(response.data),
      };
    } catch (error) {
      console.error('Error updating document:', error);
      throw this.handleError(error);
    }
  }

  /**
   * Delete a document
   */
  async deleteDocument(documentId: string, permanent: boolean = false): Promise<void> {
    try {
      await apiClient.delete(`/${documentId}`, {
        params: { permanent },
      });
    } catch (error) {
      console.error('Error deleting document:', error);
      throw this.handleError(error);
    }
  }

  /**
   * Bulk delete documents
   */
  async bulkDeleteDocuments(documentIds: string[], permanent: boolean = false): Promise<{
    message: string;
    deleted_count: number;
    processed_ids: string[];
    missing_ids?: string[];
  }> {
    try {
      const response = await apiClient.post('/bulk-delete', documentIds.map(id => parseInt(id)), {
        params: { permanent },
      });
      
      return response.data;
    } catch (error) {
      console.error('Error bulk deleting documents:', error);
      throw this.handleError(error);
    }
  }

  /**
   * Get document statistics
   */
  async getDocumentStats(): Promise<DocumentStats> {
    try {
      const response: AxiosResponse<DocumentStats> = await apiClient.get('/stats/summary');
      return response.data;
    } catch (error) {
      console.error('Error fetching document stats:', error);
      throw this.handleError(error);
    }
  }

  /**
   * Upload a new document (delegates to upload API)
   */
  async uploadDocument(file: File, title?: string): Promise<{ document_id: number; status: string; message: string }> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (title) {
        formData.append('title', title);
      }

      const response = await axios.post(`${API_BASE}/api/upload/file`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes for large file uploads
      });

      return response.data;
    } catch (error) {
      console.error('Error uploading document:', error);
      throw this.handleError(error);
    }
  }

  // Helper methods

  /**
   * Infer category based on document title and filename
   */
  private inferCategory(title: string, filename: string): string {
    const text = `${title} ${filename}`.toLowerCase();
    
    if (text.includes('machine learning') || text.includes('ai') || text.includes('artificial intelligence') || text.includes('ml')) {
      return 'AI/ML';
    }
    if (text.includes('react') || text.includes('javascript') || text.includes('programming') || text.includes('code') || text.includes('development')) {
      return 'Programming';
    }
    if (text.includes('data science') || text.includes('python') || text.includes('analytics') || text.includes('statistics')) {
      return 'Data Science';
    }
    if (text.includes('business') || text.includes('management') || text.includes('strategy')) {
      return 'Business';
    }
    if (text.includes('research') || text.includes('academic') || text.includes('study')) {
      return 'Research';
    }
    
    return 'General';
  }

  /**
   * Generate a description based on document metadata
   */
  private generateDescription(doc: Partial<Document>): string {
    const parts = [];
    
    if (doc.page_count) {
      parts.push(`${doc.page_count} pages`);
    }
    if (doc.word_count) {
      parts.push(`${doc.word_count.toLocaleString()} words`);
    }
    if (doc.language && doc.language !== 'en') {
      parts.push(`Language: ${doc.language.toUpperCase()}`);
    }
    
    const description = parts.join(' • ');
    
    // Add status-specific descriptions
    if (doc.status === 'processing') {
      return description ? `Processing document... • ${description}` : 'Processing document...';
    }
    if (doc.status === 'error' && doc.processing_error) {
      return `Error: ${doc.processing_error}`;
    }
    
    return description || 'Document ready for chat';
  }

  /**
   * Handle API errors
   */
  private handleError(error: any): Error {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        // Server responded with error status
        const message = error.response.data?.detail || error.response.data?.message || error.message;
        return new Error(`API Error: ${message}`);
      } else if (error.request) {
        // Request was made but no response received
        return new Error('Network Error: Unable to connect to the server');
      }
    }
    
    return error instanceof Error ? error : new Error('Unknown error occurred');
  }
}

// Export singleton instance
export const documentService = new DocumentService();
export default documentService; 