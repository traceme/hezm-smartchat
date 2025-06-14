import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import DocumentList from './DocumentList';
import ConversationArea from './ConversationArea';
import DocumentUpload from './DocumentUpload';
import documentService, { Document } from '../services/documentService';

const DRAWER_WIDTH = 320;

interface LayoutProps {
  children?: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  // State management
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [refreshDocuments, setRefreshDocuments] = useState(0);

  // Load selected document details when ID changes
  const loadSelectedDocument = useCallback(async (documentId: string | null) => {
    if (!documentId) {
      setSelectedDocument(null);
      return;
    }

    try {
      const document = await documentService.getDocument(documentId);
      setSelectedDocument(document);
    } catch (error) {
      console.error('Error loading selected document:', error);
      setSelectedDocument(null);
    }
  }, []);

  // Effect to load document when selection changes
  useEffect(() => {
    loadSelectedDocument(selectedDocumentId);
  }, [selectedDocumentId, loadSelectedDocument]);

  const handleDocumentSelect = (documentId: string | null) => {
    setSelectedDocumentId(documentId);
  };

  const handleDocumentUpload = () => {
    setUploadDialogOpen(true);
  };

  const handleUploadDialogClose = () => {
    setUploadDialogOpen(false);
  };

  const handleUploadComplete = (documentIds: number[]) => {
    console.log('Upload completed for documents:', documentIds);
    // Trigger refresh of document list
    setRefreshDocuments(prev => prev + 1);
    // Optionally select the first uploaded document
    if (documentIds.length > 0) {
      setSelectedDocumentId(documentIds[0].toString());
    }
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          zIndex: theme.zIndex.drawer + 1,
          backgroundColor: '#1a73e8',
        }}
      >
        <Toolbar>
          <Typography
            variant="h6"
            noWrap
            component="div"
            sx={{
              flexGrow: 1,
              fontWeight: 500,
              color: 'white',
            }}
          >
            SmartChat
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Document List Drawer */}
      <Drawer
        variant={isMobile ? 'temporary' : 'permanent'}
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
            mt: 8, // Account for AppBar height
            height: 'calc(100vh - 64px)',
            borderRight: '1px solid #e0e0e0',
          },
        }}
      >
        <DocumentList 
          selectedDocumentId={selectedDocumentId}
          onDocumentSelect={handleDocumentSelect}
          onDocumentUpload={handleDocumentUpload}
          key={refreshDocuments} // Force refresh when documents are uploaded
        />
      </Drawer>

      {/* Main Content Area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          mt: 8, // Account for AppBar height
          height: 'calc(100vh - 64px)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <ConversationArea 
          selectedDocumentId={selectedDocumentId} 
          selectedDocumentTitle={selectedDocument?.title}
        />
      </Box>

      {/* Document Upload Dialog */}
      <DocumentUpload
        open={uploadDialogOpen}
        onClose={handleUploadDialogClose}
        onUploadComplete={handleUploadComplete}
      />
    </Box>
  );
};

export default Layout; 