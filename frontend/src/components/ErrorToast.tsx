import React, { useState, useEffect } from 'react';
import {
  Snackbar,
  Alert,
  AlertTitle,
  Button,
  Box,
  Typography,
  Collapse
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  ContentCopy as ContentCopyIcon
} from '@mui/icons-material';

export interface ErrorToastData {
  id: string;
  message: string;
  severity: 'error' | 'warning' | 'info' | 'success';
  title?: string;
  details?: string;
  requestId?: string;
  duration?: number;
  actions?: Array<{
    label: string;
    onClick: () => void;
  }>;
}

interface ErrorToastProps {
  toast: ErrorToastData | null;
  onClose: () => void;
}

const ErrorToast: React.FC<ErrorToastProps> = ({ toast, onClose }) => {
  const [showDetails, setShowDetails] = useState(false);

  const handleClose = (event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    onClose();
  };

  const toggleDetails = () => {
    setShowDetails(!showDetails);
  };

  const copyRequestId = () => {
    if (toast?.requestId) {
      navigator.clipboard.writeText(toast.requestId);
    }
  };

  if (!toast) return null;

  return (
    <Snackbar
      open={true}
      autoHideDuration={toast.duration || (toast.severity === 'error' ? 8000 : 4000)}
      onClose={handleClose}
      anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
    >
      <Alert
        severity={toast.severity}
        onClose={handleClose}
        sx={{ 
          minWidth: 300,
          maxWidth: 500
        }}
      >
        {toast.title && <AlertTitle>{toast.title}</AlertTitle>}
        
        <Typography variant="body2" sx={{ mb: toast.details || toast.requestId ? 1 : 0 }}>
          {toast.message}
        </Typography>

        {/* Details and Request ID Section */}
        {(toast.details || toast.requestId) && (
          <Box>
            <Button
              size="small"
              onClick={toggleDetails}
              endIcon={showDetails ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              sx={{ p: 0, minWidth: 'auto', textTransform: 'none' }}
            >
              {showDetails ? 'Hide' : 'Show'} Details
            </Button>

            <Collapse in={showDetails}>
              <Box sx={{ mt: 1, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
                {toast.details && (
                  <Typography variant="body2" sx={{ fontSize: '0.8rem', mb: 1 }}>
                    {toast.details}
                  </Typography>
                )}
                
                {toast.requestId && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      Request ID: {toast.requestId}
                    </Typography>
                    <Button
                      size="small"
                      onClick={copyRequestId}
                      startIcon={<ContentCopyIcon />}
                      sx={{ minWidth: 'auto', p: 0.5 }}
                    >
                      Copy
                    </Button>
                  </Box>
                )}
              </Box>
            </Collapse>
          </Box>
        )}

        {/* Custom Actions */}
        {toast.actions && toast.actions.length > 0 && (
          <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
            {toast.actions.map((action, index) => (
              <Button
                key={index}
                size="small"
                onClick={action.onClick}
                variant="outlined"
                color="inherit"
              >
                {action.label}
              </Button>
            ))}
          </Box>
        )}
      </Alert>
    </Snackbar>
  );
};

export default ErrorToast; 