import React, { useState } from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Typography,
  TextField,
  InputAdornment,
  Fab,
  Chip,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  Description as DocumentIcon,
  Add as AddIcon,
  CloudUpload as UploadIcon,
} from '@mui/icons-material';

interface Document {
  id: string;
  title: string;
  type: 'pdf' | 'epub' | 'txt' | 'docx';
  uploadDate: string;
  status: 'processing' | 'ready' | 'error';
  size: string;
}

// Mock data for development
const mockDocuments: Document[] = [
  {
    id: '1',
    title: 'Introduction to Machine Learning',
    type: 'pdf',
    uploadDate: '2024-01-15',
    status: 'ready',
    size: '2.3 MB',
  },
  {
    id: '2',
    title: 'React Development Guide',
    type: 'epub',
    uploadDate: '2024-01-14',
    status: 'ready',
    size: '1.8 MB',
  },
  {
    id: '3',
    title: 'Processing Document...',
    type: 'pdf',
    uploadDate: '2024-01-16',
    status: 'processing',
    size: '4.1 MB',
  },
];

const DocumentList: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDocument, setSelectedDocument] = useState<string | null>('1');

  const filteredDocuments = mockDocuments.filter((doc) =>
    doc.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusColor = (status: Document['status']) => {
    switch (status) {
      case 'ready':
        return 'success';
      case 'processing':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const getTypeIcon = (type: Document['type']) => {
    return <DocumentIcon />;
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0' }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 500 }}>
          My Documents
        </Typography>
        
        {/* Search */}
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search documents..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
            },
          }}
        />
      </Box>

      {/* Document List */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        <List sx={{ p: 0 }}>
          {filteredDocuments.map((document, index) => (
            <React.Fragment key={document.id}>
              <ListItem disablePadding>
                <ListItemButton
                  selected={selectedDocument === document.id}
                  onClick={() => setSelectedDocument(document.id)}
                  sx={{
                    py: 1.5,
                    px: 2,
                    '&.Mui-selected': {
                      backgroundColor: '#e8f0fe',
                      '&:hover': {
                        backgroundColor: '#e8f0fe',
                      },
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    {getTypeIcon(document.type)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: selectedDocument === document.id ? 500 : 400,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {document.title}
                      </Typography>
                    }
                    secondary={
                      <Box sx={{ mt: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          {document.size} • {document.uploadDate}
                        </Typography>
                        <Box sx={{ mt: 0.5 }}>
                          <Chip
                            label={document.status}
                            size="small"
                            color={getStatusColor(document.status)}
                            variant="outlined"
                            sx={{ height: 20, fontSize: '0.7rem' }}
                          />
                        </Box>
                      </Box>
                    }
                  />
                </ListItemButton>
              </ListItem>
              {index < filteredDocuments.length - 1 && (
                <Divider variant="inset" component="li" />
              )}
            </React.Fragment>
          ))}
        </List>

        {filteredDocuments.length === 0 && (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '200px',
              color: 'text.secondary',
            }}
          >
            <DocumentIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
            <Typography variant="body2">
              {searchQuery ? 'No documents found' : 'No documents yet'}
            </Typography>
          </Box>
        )}
      </Box>

      {/* Upload FAB */}
      <Box sx={{ position: 'absolute', bottom: 16, right: 16 }}>
        <Fab
          color="primary"
          aria-label="upload document"
          sx={{
            backgroundColor: '#1a73e8',
            '&:hover': {
              backgroundColor: '#1557b0',
            },
          }}
        >
          <UploadIcon />
        </Fab>
      </Box>
    </Box>
  );
};

export default DocumentList; 