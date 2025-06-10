import React, { useState, useCallback, useRef } from 'react';
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  LinearProgress,
  Paper,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Chip,
  TextField,
  Alert,
  Divider,
  Fab,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Close as CloseIcon,
  Description as DocumentIcon,
  PictureAsPdf as PdfIcon,
  MenuBook as EpubIcon,
  TextSnippet as TxtIcon,
  Article as DocxIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import documentService from '../services/documentService';

interface UploadFile {
  id: string;
  file: File;
  title: string;
  status: 'pending' | 'uploading' | 'processing' | 'success' | 'error';
  progress: number;
  documentId?: number;
  error?: string;
}

interface DocumentUploadProps {
  open: boolean;
  onClose: () => void;
  onUploadComplete?: (documentIds: number[]) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  open,
  onClose,
  onUploadComplete,
}) => {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Supported file types and size limits
  const supportedTypes = ['application/pdf', 'application/epub+zip', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/markdown'];
  const maxFileSize = 500 * 1024 * 1024; // 500MB
  const maxFiles = 10;

  // Helper functions
  const getFileIcon = (type: string) => {
    if (type.includes('pdf')) return <PdfIcon sx={{ color: '#dc3545' }} />;
    if (type.includes('epub')) return <EpubIcon sx={{ color: '#6f42c1' }} />;
    if (type.includes('text')) return <TxtIcon sx={{ color: '#198754' }} />;
    if (type.includes('word')) return <DocxIcon sx={{ color: '#0d6efd' }} />;
    return <DocumentIcon />;
  };

  const getFileTypeFromMime = (mimeType: string): string => {
    if (mimeType.includes('pdf')) return 'PDF';
    if (mimeType.includes('epub')) return 'EPUB';
    if (mimeType.includes('text/plain')) return 'TXT';
    if (mimeType.includes('word')) return 'DOCX';
    if (mimeType.includes('markdown')) return 'MD';
    return 'Unknown';
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const generateFileId = () => Math.random().toString(36).substr(2, 9);

  // File validation
  const validateFile = (file: File): string | null => {
    if (!supportedTypes.includes(file.type)) {
      return `Unsupported file type. Supported: PDF, EPUB, TXT, DOCX, MD`;
    }
    if (file.size > maxFileSize) {
      return `File too large. Maximum size: ${formatFileSize(maxFileSize)}`;
    }
    return null;
  };

  // File handling
  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);
    
    if (files.length + fileArray.length > maxFiles) {
      alert(`Cannot upload more than ${maxFiles} files at once`);
      return;
    }

    const validFiles: UploadFile[] = [];
    const errors: string[] = [];

    fileArray.forEach((file) => {
      const error = validateFile(file);
      if (error) {
        errors.push(`${file.name}: ${error}`);
      } else {
        validFiles.push({
          id: generateFileId(),
          file,
          title: file.name.replace(/\.[^/.]+$/, ''), // Remove extension
          status: 'pending',
          progress: 0,
        });
      }
    });

    if (errors.length > 0) {
      alert(`Some files were rejected:\n${errors.join('\n')}`);
    }

    if (validFiles.length > 0) {
      setFiles(prev => [...prev, ...validFiles]);
    }
  }, [files.length]);

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget === e.target) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      addFiles(droppedFiles);
    }
  }, [addFiles]);

  // File input handler
  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles) {
      addFiles(selectedFiles);
    }
    // Reset the input to allow selecting the same file again
    e.target.value = '';
  }, [addFiles]);

  // File management
  const removeFile = useCallback((fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  }, []);

  const updateFileTitle = useCallback((fileId: string, newTitle: string) => {
    setFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, title: newTitle } : f
    ));
  }, []);

  // Upload functionality
  const uploadFile = async (uploadFile: UploadFile): Promise<void> => {
    try {
      // Update status to uploading
      setFiles(prev => prev.map(f => 
        f.id === uploadFile.id 
          ? { ...f, status: 'uploading', progress: 0 }
          : f
      ));

      // Simulate progress for demonstration
      const progressInterval = setInterval(() => {
        setFiles(prev => prev.map(f => {
          if (f.id === uploadFile.id && f.status === 'uploading') {
            const newProgress = Math.min(f.progress + Math.random() * 20, 90);
            return { ...f, progress: newProgress };
          }
          return f;
        }));
      }, 500);

      // Upload file
      const result = await documentService.uploadDocument(uploadFile.file, uploadFile.title);

      clearInterval(progressInterval);

      // Update status based on result
      if (result.status === 'success' || result.status === 'duplicate') {
        setFiles(prev => prev.map(f => 
          f.id === uploadFile.id 
            ? { 
                ...f, 
                status: result.status === 'duplicate' ? 'success' : 'processing',
                progress: 100,
                documentId: result.document_id 
              }
            : f
        ));

        // If not duplicate, simulate processing completion after a delay
        if (result.status === 'success') {
          setTimeout(() => {
            setFiles(prev => prev.map(f => 
              f.id === uploadFile.id 
                ? { ...f, status: 'success' }
                : f
            ));
          }, 2000 + Math.random() * 3000); // Random delay between 2-5 seconds
        }
      } else {
        setFiles(prev => prev.map(f => 
          f.id === uploadFile.id 
            ? { 
                ...f, 
                status: 'error', 
                progress: 0,
                error: result.message || 'Upload failed'
              }
            : f
        ));
      }
    } catch (error) {
      setFiles(prev => prev.map(f => 
        f.id === uploadFile.id 
          ? { 
              ...f, 
              status: 'error', 
              progress: 0,
              error: error instanceof Error ? error.message : 'Upload failed'
            }
          : f
      ));
    }
  };

  const uploadAllFiles = useCallback(async () => {
    const pendingFiles = files.filter(f => f.status === 'pending');
    if (pendingFiles.length === 0) return;

    setIsUploading(true);

    // Upload files sequentially to avoid overwhelming the server
    for (const file of pendingFiles) {
      await uploadFile(file);
      // Small delay between uploads
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    setIsUploading(false);
  }, [files]);

  // Dialog handlers
  const handleClose = useCallback(() => {
    if (isUploading) {
      const confirmClose = window.confirm('Upload in progress. Are you sure you want to close?');
      if (!confirmClose) return;
    }

    const completedDocumentIds = files
      .filter(f => f.status === 'success' && f.documentId)
      .map(f => f.documentId!);

    if (completedDocumentIds.length > 0) {
      onUploadComplete?.(completedDocumentIds);
    }

    setFiles([]);
    setIsUploading(false);
    onClose();
  }, [isUploading, files, onUploadComplete, onClose]);

  const handleStartUpload = useCallback(() => {
    uploadAllFiles();
  }, [uploadAllFiles]);

  // Statistics
  const stats = {
    total: files.length,
    pending: files.filter(f => f.status === 'pending').length,
    uploading: files.filter(f => f.status === 'uploading').length,
    processing: files.filter(f => f.status === 'processing').length,
    success: files.filter(f => f.status === 'success').length,
    error: files.filter(f => f.status === 'error').length,
  };

  const overallProgress = files.length > 0 
    ? (stats.success + stats.error) / files.length * 100 
    : 0;

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { height: '80vh', display: 'flex', flexDirection: 'column' }
      }}
    >
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6">Upload Documents</Typography>
        <IconButton onClick={handleClose} disabled={isUploading}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Upload Progress Summary */}
        {files.length > 0 && (
          <Paper sx={{ p: 2, backgroundColor: '#f8f9fa' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2">
                Upload Progress: {stats.success + stats.error} of {files.length} files
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {overallProgress.toFixed(0)}%
              </Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={overallProgress} 
              sx={{ height: 6, borderRadius: 3 }}
            />
            <Box sx={{ display: 'flex', gap: 2, mt: 1, flexWrap: 'wrap' }}>
              {stats.pending > 0 && <Chip label={`${stats.pending} Pending`} size="small" />}
              {stats.uploading > 0 && <Chip label={`${stats.uploading} Uploading`} size="small" color="info" />}
              {stats.processing > 0 && <Chip label={`${stats.processing} Processing`} size="small" color="warning" />}
              {stats.success > 0 && <Chip label={`${stats.success} Complete`} size="small" color="success" />}
              {stats.error > 0 && <Chip label={`${stats.error} Failed`} size="small" color="error" />}
            </Box>
          </Paper>
        )}

        {/* Drag and Drop Area */}
        <Paper
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          sx={{
            p: 4,
            textAlign: 'center',
            border: '2px dashed',
            borderColor: isDragging ? 'primary.main' : 'grey.300',
            backgroundColor: isDragging ? 'action.hover' : 'background.paper',
            cursor: 'pointer',
            transition: 'all 0.2s ease-in-out',
            '&:hover': {
              borderColor: 'primary.main',
              backgroundColor: 'action.hover',
            },
          }}
        >
          <UploadIcon 
            sx={{ 
              fontSize: 48, 
              color: isDragging ? 'primary.main' : 'grey.400',
              mb: 1 
            }} 
          />
          <Typography variant="h6" gutterBottom>
            {isDragging ? 'Drop files here' : 'Drag & drop files or click to browse'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Supported: PDF, EPUB, TXT, DOCX, MD • Max size: {formatFileSize(maxFileSize)} • Max files: {maxFiles}
          </Typography>
        </Paper>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.epub,.txt,.docx,.md"
          onChange={handleFileInput}
          style={{ display: 'none' }}
        />

        {/* File List */}
        {files.length > 0 && (
          <Paper sx={{ flexGrow: 1, overflow: 'auto' }}>
            <List>
              {files.map((uploadFile, index) => (
                <React.Fragment key={uploadFile.id}>
                  <ListItem>
                    <ListItemIcon>
                      {uploadFile.status === 'success' && <SuccessIcon color="success" />}
                      {uploadFile.status === 'error' && <ErrorIcon color="error" />}
                      {(uploadFile.status === 'uploading' || uploadFile.status === 'processing') && (
                        <CircularProgress size={24} />
                      )}
                      {uploadFile.status === 'pending' && getFileIcon(uploadFile.file.type)}
                    </ListItemIcon>

                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <TextField
                            value={uploadFile.title}
                            onChange={(e) => updateFileTitle(uploadFile.id, e.target.value)}
                            variant="standard"
                            size="small"
                            disabled={uploadFile.status !== 'pending'}
                            sx={{ flexGrow: 1 }}
                          />
                          <Chip
                            label={getFileTypeFromMime(uploadFile.file.type)}
                            size="small"
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="caption" color="text.secondary">
                            {formatFileSize(uploadFile.file.size)} • {uploadFile.file.name}
                          </Typography>
                          
                          {/* Status and Progress */}
                          <Box sx={{ mt: 0.5 }}>
                            {uploadFile.status === 'uploading' && (
                              <Box>
                                <Typography variant="caption" color="primary">
                                  Uploading... {uploadFile.progress.toFixed(0)}%
                                </Typography>
                                <LinearProgress 
                                  variant="determinate" 
                                  value={uploadFile.progress} 
                                  sx={{ mt: 0.5, height: 4, borderRadius: 2 }}
                                />
                              </Box>
                            )}
                            
                            {uploadFile.status === 'processing' && (
                              <Typography variant="caption" color="warning.main">
                                Processing document...
                              </Typography>
                            )}
                            
                            {uploadFile.status === 'success' && (
                              <Typography variant="caption" color="success.main">
                                Upload complete! Document ready.
                              </Typography>
                            )}
                            
                            {uploadFile.status === 'error' && (
                              <Typography variant="caption" color="error.main">
                                Error: {uploadFile.error}
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      }
                    />

                    <ListItemSecondaryAction>
                      {uploadFile.status === 'pending' && (
                        <IconButton
                          size="small"
                          onClick={() => removeFile(uploadFile.id)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      )}
                    </ListItemSecondaryAction>
                  </ListItem>
                  
                  {index < files.length - 1 && <Divider variant="inset" />}
                </React.Fragment>
              ))}
            </List>
          </Paper>
        )}

        {/* Warnings and Errors */}
        {files.some(f => f.status === 'error') && (
          <Alert severity="error">
            Some files failed to upload. Please check the errors above and try again.
          </Alert>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={handleClose} disabled={isUploading}>
          {stats.success > 0 ? 'Done' : 'Cancel'}
        </Button>
        <Button
          variant="contained"
          onClick={handleStartUpload}
          disabled={stats.pending === 0 || isUploading}
          startIcon={isUploading ? <CircularProgress size={16} /> : <UploadIcon />}
        >
          {isUploading ? 'Uploading...' : `Upload ${stats.pending} File${stats.pending !== 1 ? 's' : ''}`}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DocumentUpload; 