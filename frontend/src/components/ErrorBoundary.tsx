import React, { Component, ReactNode } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  Button, 
  Alert,
  Collapse,
  IconButton
} from '@mui/material';
import {
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  BugReport as BugReportIcon
} from '@mui/icons-material';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  showDetails: boolean;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  resetOnPropsChange?: boolean;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({
      error,
      errorInfo
    });

    // Log error to console
    console.error('Error caught by ErrorBoundary:', error, errorInfo);

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to external service (if configured)
    this.logErrorToService(error, errorInfo);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    const { resetOnPropsChange } = this.props;
    const { hasError } = this.state;

    if (hasError && resetOnPropsChange && prevProps.children !== this.props.children) {
      this.resetError();
    }
  }

  private logErrorToService = (error: Error, errorInfo: React.ErrorInfo) => {
    // In production, you would integrate with a service like Sentry, LogRocket, etc.
    const errorData = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    try {
      // Store in localStorage for now (in production, send to monitoring service)
      const existingErrors = JSON.parse(localStorage.getItem('smartchat_errors') || '[]');
      existingErrors.push(errorData);
      
      // Keep only the last 10 errors
      if (existingErrors.length > 10) {
        existingErrors.splice(0, existingErrors.length - 10);
      }
      
      localStorage.setItem('smartchat_errors', JSON.stringify(existingErrors));
    } catch (loggingError) {
      console.error('Failed to log error:', loggingError);
    }
  };

  private resetError = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false
    });
  };

  private toggleDetails = () => {
    this.setState(prevState => ({
      showDetails: !prevState.showDetails
    }));
  };

  private reloadPage = () => {
    window.location.reload();
  };

  render() {
    const { hasError, error, errorInfo, showDetails } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      // Custom fallback UI
      if (fallback) {
        return fallback;
      }

      // Default error UI
      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '400px',
            p: 3,
            textAlign: 'center'
          }}
        >
          <Paper
            elevation={3}
            sx={{
              p: 4,
              maxWidth: 600,
              width: '100%'
            }}
          >
            {/* Error Icon and Title */}
            <Box sx={{ mb: 3 }}>
              <ErrorIcon 
                sx={{ 
                  fontSize: 64, 
                  color: 'error.main',
                  mb: 2 
                }} 
              />
              <Typography variant="h5" component="h1" gutterBottom>
                Oops! Something went wrong
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                We encountered an unexpected error. Don't worry, your data is safe.
              </Typography>
            </Box>

            {/* Error Alert */}
            <Alert severity="error" sx={{ mb: 3, textAlign: 'left' }}>
              <Typography variant="body2">
                <strong>Error:</strong> {error?.message || 'An unknown error occurred'}
              </Typography>
            </Alert>

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3, justifyContent: 'center' }}>
              <Button
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={this.resetError}
                color="primary"
              >
                Try Again
              </Button>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={this.reloadPage}
              >
                Reload Page
              </Button>
            </Box>

            {/* Technical Details Toggle */}
            <Box sx={{ textAlign: 'center' }}>
              <Button
                variant="text"
                size="small"
                startIcon={<BugReportIcon />}
                endIcon={showDetails ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                onClick={this.toggleDetails}
                color="inherit"
              >
                {showDetails ? 'Hide' : 'Show'} Technical Details
              </Button>

              <Collapse in={showDetails}>
                <Box
                  sx={{
                    mt: 2,
                    p: 2,
                    bgcolor: 'grey.100',
                    borderRadius: 1,
                    textAlign: 'left'
                  }}
                >
                  {error && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Error Message:
                      </Typography>
                      <Typography variant="body2" component="pre" sx={{ fontSize: '0.8rem' }}>
                        {error.message}
                      </Typography>
                    </Box>
                  )}

                  {error?.stack && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Stack Trace:
                      </Typography>
                      <Typography 
                        variant="body2" 
                        component="pre" 
                        sx={{ 
                          fontSize: '0.7rem',
                          maxHeight: 200,
                          overflow: 'auto',
                          whiteSpace: 'pre-wrap'
                        }}
                      >
                        {error.stack}
                      </Typography>
                    </Box>
                  )}

                  {errorInfo?.componentStack && (
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>
                        Component Stack:
                      </Typography>
                      <Typography 
                        variant="body2" 
                        component="pre" 
                        sx={{ 
                          fontSize: '0.7rem',
                          maxHeight: 200,
                          overflow: 'auto',
                          whiteSpace: 'pre-wrap'
                        }}
                      >
                        {errorInfo.componentStack}
                      </Typography>
                    </Box>
                  )}
                </Box>
              </Collapse>
            </Box>
          </Paper>
        </Box>
      );
    }

    return children;
  }
}

export default ErrorBoundary; 