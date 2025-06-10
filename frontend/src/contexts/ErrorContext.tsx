import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import ErrorToast, { ErrorToastData } from '../components/ErrorToast';

interface ApiError {
  code: string;
  message: string;
  request_id?: string;
  details?: Record<string, any>;
}

interface ErrorContextValue {
  // Toast management
  showToast: (toast: Omit<ErrorToastData, 'id'>) => void;
  showError: (message: string, details?: string, requestId?: string) => void;
  showSuccess: (message: string, details?: string) => void;
  showWarning: (message: string, details?: string) => void;
  showInfo: (message: string, details?: string) => void;
  
  // API error handling
  handleApiError: (error: any, defaultMessage?: string) => void;
  
  // Network error handling
  handleNetworkError: (error: any) => void;
  
  // Clear all toasts
  clearToasts: () => void;
}

const ErrorContext = createContext<ErrorContextValue | undefined>(undefined);

interface ErrorProviderProps {
  children: ReactNode;
}

export const ErrorProvider: React.FC<ErrorProviderProps> = ({ children }) => {
  const [toasts, setToasts] = useState<ErrorToastData[]>([]);

  const generateId = () => Date.now().toString() + Math.random().toString(36).substr(2, 9);

  const showToast = useCallback((toastData: Omit<ErrorToastData, 'id'>) => {
    const toast: ErrorToastData = {
      ...toastData,
      id: generateId()
    };

    setToasts(prev => [...prev, toast]);

    // Auto-remove toast after duration
    const duration = toast.duration || (toast.severity === 'error' ? 8000 : 4000);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== toast.id));
    }, duration);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const showError = useCallback((message: string, details?: string, requestId?: string) => {
    showToast({
      message,
      severity: 'error',
      title: 'Error',
      details,
      requestId,
      duration: 8000
    });
  }, [showToast]);

  const showSuccess = useCallback((message: string, details?: string) => {
    showToast({
      message,
      severity: 'success',
      title: 'Success',
      details,
      duration: 4000
    });
  }, [showToast]);

  const showWarning = useCallback((message: string, details?: string) => {
    showToast({
      message,
      severity: 'warning',
      title: 'Warning',
      details,
      duration: 6000
    });
  }, [showToast]);

  const showInfo = useCallback((message: string, details?: string) => {
    showToast({
      message,
      severity: 'info',
      title: 'Information',
      details,
      duration: 4000
    });
  }, [showToast]);

  const handleApiError = useCallback((error: any, defaultMessage = 'An unexpected error occurred') => {
    console.error('API Error:', error);

    // Handle different types of errors
    if (error?.response?.data?.error) {
      // Standardized API error response
      const apiError: ApiError = error.response.data.error;
      
      let details = '';
      if (apiError.details) {
        if (apiError.details.validation_errors) {
          // Format validation errors
          details = apiError.details.validation_errors
            .map((ve: any) => `${ve.field}: ${ve.message}`)
            .join(', ');
        } else if (typeof apiError.details === 'object') {
          details = JSON.stringify(apiError.details, null, 2);
        } else {
          details = String(apiError.details);
        }
      }

      showError(
        apiError.message || defaultMessage,
        details,
        apiError.request_id
      );
    } else if (error?.response?.status) {
      // HTTP error without standardized format
      const status = error.response.status;
      const statusText = error.response.statusText || 'Unknown Error';
      
      let message = defaultMessage;
      switch (status) {
        case 400:
          message = 'Bad request. Please check your input.';
          break;
        case 401:
          message = 'Authentication required. Please log in.';
          break;
        case 403:
          message = 'Access denied. You do not have permission.';
          break;
        case 404:
          message = 'The requested resource was not found.';
          break;
        case 422:
          message = 'Invalid data provided. Please check your input.';
          break;
        case 429:
          message = 'Too many requests. Please try again later.';
          break;
        case 500:
          message = 'Server error. Please try again later.';
          break;
        case 502:
        case 503:
        case 504:
          message = 'Service temporarily unavailable. Please try again later.';
          break;
      }

      showError(
        message,
        `HTTP ${status}: ${statusText}`,
        error.response.headers?.['x-request-id']
      );
    } else if (error?.message) {
      // Generic error with message
      showError(error.message);
    } else {
      // Fallback error
      showError(defaultMessage);
    }
  }, [showError]);

  const handleNetworkError = useCallback((error: any) => {
    console.error('Network Error:', error);

    if (error.code === 'NETWORK_ERROR' || !navigator.onLine) {
      showError(
        'Network connection lost',
        'Please check your internet connection and try again.',
        undefined
      );
    } else if (error.code === 'TIMEOUT_ERROR') {
      showError(
        'Request timed out',
        'The request took too long to complete. Please try again.',
        undefined
      );
    } else {
      showError(
        'Network error occurred',
        'Please check your connection and try again.',
        undefined
      );
    }
  }, [showError]);

  const clearToasts = useCallback(() => {
    setToasts([]);
  }, []);

  const value: ErrorContextValue = {
    showToast,
    showError,
    showSuccess,
    showWarning,
    showInfo,
    handleApiError,
    handleNetworkError,
    clearToasts
  };

  return (
    <ErrorContext.Provider value={value}>
      {children}
      
      {/* Render all toasts */}
      {toasts.map((toast) => (
        <ErrorToast
          key={toast.id}
          toast={toast}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </ErrorContext.Provider>
  );
};

export const useError = (): ErrorContextValue => {
  const context = useContext(ErrorContext);
  if (!context) {
    throw new Error('useError must be used within an ErrorProvider');
  }
  return context;
};

export default ErrorContext; 