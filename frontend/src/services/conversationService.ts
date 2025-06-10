import axios, { AxiosResponse } from 'axios';

// Types for conversation management
export interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  sources?: string[];
  model_used?: string;
  processing_time?: number;
  error?: string;
}

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface QueryRequest {
  query: string;
  user_id?: number;
  document_id?: number;
  conversation_history?: ConversationMessage[];
  model_preference: string;
}

export interface StreamQueryRequest extends QueryRequest {}

export interface QueryResponse {
  response: string;
  citations: Array<{
    id: string;
    content: string;
    metadata: any;
  }>;
  fragments_found: number;
  fragments_used: number;
  model_used: string;
  model_name: string;
  usage: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
  processing_time: number;
  timestamp: string;
}

export interface StreamChunk {
  type: 'search' | 'citations' | 'chunk' | 'final' | 'error';
  content?: string;
  citations?: Array<{ id: string; content: string; metadata: any }>;
  response?: string;
  fragments_found?: number;
  fragments_used?: number;
  model_used?: string;
  processing_time?: number;
  timestamp?: string;
  error?: string;
}

export interface ModelInfo {
  provider: string;
  model: string;
  available: boolean;
  reason?: string;
}

// API configuration
const API_BASE = process.env.REACT_APP_API_URL || '';
const DIALOGUE_API = `${API_BASE}/api/dialogue`;

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: DIALOGUE_API,
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

// Conversation Service class
class ConversationService {
  /**
   * Map frontend model names to backend model preferences
   */
  private mapModelToBackend(frontendModel: string): string {
    const modelMap: Record<string, string> = {
      'GPT-4o': 'openai',
      'Claude': 'claude', 
      'Gemini': 'gemini',
    };
    return modelMap[frontendModel] || 'openai';
  }

  /**
   * Convert messages to conversation history format
   */
  private convertToConversationHistory(messages: Message[]): ConversationMessage[] {
    return messages.map(msg => ({
      role: msg.isUser ? 'user' : 'assistant',
      content: msg.content,
      timestamp: msg.timestamp.toISOString(),
    }));
  }

  /**
   * Send a query and get a complete response
   */
  async sendQuery(
    query: string,
    selectedModel: string,
    documentId?: string,
    conversationHistory: Message[] = []
  ): Promise<Message> {
    try {
      const request: QueryRequest = {
        query,
        model_preference: this.mapModelToBackend(selectedModel),
        document_id: documentId ? parseInt(documentId) : undefined,
        conversation_history: this.convertToConversationHistory(conversationHistory),
      };

      const response: AxiosResponse<QueryResponse> = await apiClient.post('/query', request);
      const data = response.data;

      // Convert backend response to frontend Message format
      return {
        id: Date.now().toString(),
        content: data.response,
        isUser: false,
        timestamp: new Date(data.timestamp),
        sources: data.citations.map(citation => citation.metadata?.page || citation.id),
        model_used: data.model_name,
        processing_time: data.processing_time,
      };
    } catch (error) {
      console.error('Error sending query:', error);
      throw this.handleError(error);
    }
  }

  /**
   * Send a query with streaming response
   */
  async *sendQueryStream(
    query: string,
    selectedModel: string,
    documentId?: string,
    conversationHistory: Message[] = []
  ): AsyncGenerator<StreamChunk, Message, unknown> {
    try {
      const request: StreamQueryRequest = {
        query,
        model_preference: this.mapModelToBackend(selectedModel),
        document_id: documentId ? parseInt(documentId) : undefined,
        conversation_history: this.convertToConversationHistory(conversationHistory),
      };

      const response = await fetch(`${DIALOGUE_API}/query/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Failed to get response reader');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let fullResponse = '';
      let finalData: Partial<QueryResponse> = {};

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const chunk: StreamChunk = JSON.parse(line.slice(6));
                
                if (chunk.type === 'chunk' && chunk.content) {
                  fullResponse += chunk.content;
                }
                
                if (chunk.type === 'final') {
                  finalData = {
                    response: chunk.response || fullResponse,
                    citations: chunk.citations || [],
                    fragments_found: chunk.fragments_found || 0,
                    fragments_used: chunk.fragments_used || 0,
                    model_used: chunk.model_used || selectedModel,
                    processing_time: chunk.processing_time || 0,
                    timestamp: chunk.timestamp || new Date().toISOString(),
                  };
                }
                
                yield chunk;
                
                if (chunk.type === 'error') {
                  throw new Error(chunk.error || 'Unknown streaming error');
                }
              } catch (parseError) {
                console.warn('Failed to parse chunk:', parseError);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      // Return final message
      return {
        id: Date.now().toString(),
        content: finalData.response || fullResponse,
        isUser: false,
        timestamp: new Date(finalData.timestamp || Date.now()),
        sources: finalData.citations?.map(citation => citation.metadata?.page || citation.id) || [],
        model_used: finalData.model_used,
        processing_time: finalData.processing_time,
      };
    } catch (error) {
      console.error('Error in streaming query:', error);
      throw this.handleError(error);
    }
  }

  /**
   * Get available models
   */
  async getAvailableModels(): Promise<ModelInfo[]> {
    try {
      const response: AxiosResponse<{ models: ModelInfo[] }> = await apiClient.get('/models');
      return response.data.models;
    } catch (error) {
      console.error('Error fetching available models:', error);
      throw this.handleError(error);
    }
  }

  /**
   * Handle API errors
   */
  private handleError(error: any): Error {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.detail || error.message || 'An error occurred';
      return new Error(message);
    }
    
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return new Error('Network error - please check your connection');
    }
    
    return error instanceof Error ? error : new Error('Unknown error occurred');
  }
}

// Create and export service instance
export const conversationService = new ConversationService();
export default conversationService; 