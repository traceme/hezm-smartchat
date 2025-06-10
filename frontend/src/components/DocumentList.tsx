import React, { useState, useMemo, useCallback, useEffect } from 'react';
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
  IconButton,
  Menu,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Checkbox,
  Button,
  Paper,
  Tooltip,
  Badge,
  ListItemSecondaryAction,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Snackbar,
  Alert,
  LinearProgress,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  Description as DocumentIcon,
  PictureAsPdf as PdfIcon,
  MenuBook as EpubIcon,
  TextSnippet as TxtIcon,
  Article as DocxIcon,
  CloudUpload as UploadIcon,
  MoreVert as MoreIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Label as CategoryIcon,
  Sort as SortIcon,
  FilterList as FilterIcon,
  GetApp as DownloadIcon,
  Refresh as RefreshIcon,
  SelectAll as SelectAllIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import documentService, { Document, DocumentListResponse } from '../services/documentService';

interface DocumentListProps {
  onDocumentSelect?: (documentId: string | null) => void;
  onDocumentUpload?: () => void;
  selectedDocumentId?: string | null;
}

type SortField = 'title' | 'created_at' | 'file_size' | 'status';
type SortOrder = 'asc' | 'desc';

const DocumentList: React.FC<DocumentListProps> = ({
  onDocumentSelect,
  onDocumentUpload,
  selectedDocumentId,
}) => {
  // State management
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
  const [selectedDocumentForMenu, setSelectedDocumentForMenu] = useState<string | null>(null);
  
  // Dialog states
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<string | null>(null);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [documentToRename, setDocumentToRename] = useState<string | null>(null);
  const [newDocumentTitle, setNewDocumentTitle] = useState('');
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [documentToRecategorize, setDocumentToRecategorize] = useState<string | null>(null);
  const [newDocumentCategory, setNewDocumentCategory] = useState('');
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'warning' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  // Load documents from API
  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = {
        search: searchQuery || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        sort_by: sortField,
        sort_order: sortOrder,
        limit: 1000, // Load all documents for now
      };

      const response = await documentService.getDocuments(params);
      setDocuments(response.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
      console.error('Error loading documents:', err);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, statusFilter, sortField, sortOrder]);

  // Load documents on mount and when filters change
  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Get unique categories and statuses for filters
  const categories = useMemo(() => {
    const cats = new Set(documents.map(doc => doc.category).filter(Boolean));
    return Array.from(cats);
  }, [documents]);

  const statuses = useMemo(() => {
    const stats = new Set(documents.map(doc => doc.status));
    return Array.from(stats);
  }, [documents]);

  // Filtered and sorted documents (frontend filtering for categories since backend doesn't support it yet)
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const matchesCategory = categoryFilter === 'all' || doc.category === categoryFilter;
      return matchesCategory;
    });
  }, [documents, categoryFilter]);

  // Event handlers
  const handleDocumentSelect = useCallback((documentId: string) => {
    onDocumentSelect?.(documentId);
  }, [onDocumentSelect]);

  const handleRefresh = useCallback(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleMenuClick = useCallback((event: React.MouseEvent<HTMLElement>, documentId: string) => {
    event.stopPropagation();
    setMenuAnchor(event.currentTarget);
    setSelectedDocumentForMenu(documentId);
  }, []);

  const handleMenuClose = useCallback(() => {
    setMenuAnchor(null);
    setSelectedDocumentForMenu(null);
  }, []);

  const handleDeleteClick = useCallback((documentId: string) => {
    setDocumentToDelete(documentId);
    setDeleteDialogOpen(true);
    handleMenuClose();
  }, [handleMenuClose]);

  const handleRenameClick = useCallback((documentId: string) => {
    const document = documents.find(d => d.id === documentId);
    if (document) {
      setDocumentToRename(documentId);
      setNewDocumentTitle(document.title);
      setRenameDialogOpen(true);
    }
    handleMenuClose();
  }, [documents, handleMenuClose]);

  const handleCategoryClick = useCallback((documentId: string) => {
    const document = documents.find(d => d.id === documentId);
    if (document) {
      setDocumentToRecategorize(documentId);
      setNewDocumentCategory(document.category || 'General');
      setCategoryDialogOpen(true);
    }
    handleMenuClose();
  }, [documents, handleMenuClose]);

  const handleDeleteConfirm = useCallback(async () => {
    if (documentToDelete) {
      try {
        await documentService.deleteDocument(documentToDelete);
        setSnackbar({
          open: true,
          message: 'Document deleted successfully',
          severity: 'success'
        });
        setDeleteDialogOpen(false);
        setDocumentToDelete(null);
        loadDocuments(); // Refresh the list
      } catch (err) {
        setSnackbar({
          open: true,
          message: err instanceof Error ? err.message : 'Failed to delete document',
          severity: 'error'
        });
      }
    }
  }, [documentToDelete, loadDocuments]);

  const handleRenameConfirm = useCallback(async () => {
    if (documentToRename && newDocumentTitle.trim()) {
      try {
        await documentService.updateDocument(documentToRename, { title: newDocumentTitle.trim() });
        setSnackbar({
          open: true,
          message: 'Document renamed successfully',
          severity: 'success'
        });
        setRenameDialogOpen(false);
        setDocumentToRename(null);
        setNewDocumentTitle('');
        loadDocuments(); // Refresh the list
      } catch (err) {
        setSnackbar({
          open: true,
          message: err instanceof Error ? err.message : 'Failed to rename document',
          severity: 'error'
        });
      }
    }
  }, [documentToRename, newDocumentTitle, loadDocuments]);

  const handleCategoryConfirm = useCallback(async () => {
    if (documentToRecategorize && newDocumentCategory.trim()) {
      try {
        // Note: Since backend doesn't support category yet, we'll just show success message
        // In a real implementation, we would call: 
        // await documentService.updateDocument(documentToRecategorize, { category: newDocumentCategory.trim() });
        
        setSnackbar({
          open: true,
          message: 'Category change saved (frontend only - backend support pending)',
          severity: 'warning'
        });
        setCategoryDialogOpen(false);
        setDocumentToRecategorize(null);
        setNewDocumentCategory('');
        // Note: We don't refresh since the backend doesn't support categories yet
      } catch (err) {
        setSnackbar({
          open: true,
          message: err instanceof Error ? err.message : 'Failed to change category',
          severity: 'error'
        });
      }
    }
  }, [documentToRecategorize, newDocumentCategory]);

  const handleBulkDelete = useCallback(async () => {
    if (selectedDocuments.size > 0) {
      try {
        const result = await documentService.bulkDeleteDocuments(Array.from(selectedDocuments));
        setSnackbar({
          open: true,
          message: result.message,
          severity: 'success'
        });
        setSelectedDocuments(new Set());
        loadDocuments(); // Refresh the list
      } catch (err) {
        setSnackbar({
          open: true,
          message: err instanceof Error ? err.message : 'Failed to delete documents',
          severity: 'error'
        });
      }
    }
  }, [selectedDocuments, loadDocuments]);

  const handleSelectAll = useCallback(() => {
    if (selectedDocuments.size === filteredDocuments.length) {
      setSelectedDocuments(new Set());
    } else {
      setSelectedDocuments(new Set(filteredDocuments.map(doc => doc.id)));
    }
  }, [filteredDocuments, selectedDocuments]);

  const handleDocumentCheckbox = useCallback((documentId: string, checked: boolean) => {
    const newSelected = new Set(selectedDocuments);
    if (checked) {
      newSelected.add(documentId);
    } else {
      newSelected.delete(documentId);
    }
    setSelectedDocuments(newSelected);
  }, [selectedDocuments]);

  // Helper functions
  const getStatusColor = (status: Document['status']) => {
    switch (status) {
      case 'ready':
        return 'success';
      case 'processing':
        return 'warning';
      case 'error':
        return 'error';
      case 'uploading':
        return 'info';
      default:
        return 'default';
    }
  };

  const getTypeIcon = (type: Document['document_type']) => {
    switch (type) {
      case 'pdf':
        return <PdfIcon sx={{ color: '#dc3545' }} />;
      case 'epub':
        return <EpubIcon sx={{ color: '#6f42c1' }} />;
      case 'txt':
        return <TxtIcon sx={{ color: '#198754' }} />;
      case 'docx':
        return <DocxIcon sx={{ color: '#0d6efd' }} />;
      case 'md':
        return <TxtIcon sx={{ color: '#fd7e14' }} />;
      default:
        return <DocumentIcon />;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const isAllSelected = selectedDocuments.size === filteredDocuments.length && filteredDocuments.length > 0;
  const isPartiallySelected = selectedDocuments.size > 0 && selectedDocuments.size < filteredDocuments.length;

  // Show loading state
  if (loading) {
    return (
      <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  // Show error state
  if (error) {
    return (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', p: 2 }}>
        <Typography variant="h6" color="error" gutterBottom>
          Failed to load documents
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {error}
        </Typography>
        <Button variant="outlined" onClick={handleRefresh} startIcon={<RefreshIcon />}>
          Try Again
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 500 }}>
            My Documents
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Refresh">
              <IconButton size="small" onClick={handleRefresh}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Toggle Filters">
              <IconButton 
                size="small" 
                onClick={() => setShowFilters(!showFilters)}
                color={showFilters ? 'primary' : 'default'}
              >
                <FilterIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
        
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
            mb: showFilters ? 2 : 0,
            '& .MuiOutlinedInput-root': {
              borderRadius: 2,
            },
          }}
        />

        {/* Filters */}
        {showFilters && (
          <Paper sx={{ p: 2, mt: 2, backgroundColor: '#f8f9fa' }}>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Category</InputLabel>
                <Select
                  value={categoryFilter}
                  label="Category"
                  onChange={(e) => setCategoryFilter(e.target.value)}
                >
                  <MenuItem value="all">All Categories</MenuItem>
                  {categories.map((category) => (
                    <MenuItem key={category} value={category}>
                      {category}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Status</InputLabel>
                <Select
                  value={statusFilter}
                  label="Status"
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <MenuItem value="all">All Statuses</MenuItem>
                  {statuses.map((status) => (
                    <MenuItem key={status} value={status}>
                      {status.charAt(0).toUpperCase() + status.slice(1)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Sort By</InputLabel>
                <Select
                  value={sortField}
                  label="Sort By"
                  onChange={(e) => setSortField(e.target.value as SortField)}
                >
                  <MenuItem value="created_at">Upload Date</MenuItem>
                  <MenuItem value="title">Title</MenuItem>
                  <MenuItem value="file_size">Size</MenuItem>
                  <MenuItem value="status">Status</MenuItem>
                </Select>
              </FormControl>

              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>Order</InputLabel>
                <Select
                  value={sortOrder}
                  label="Order"
                  onChange={(e) => setSortOrder(e.target.value as SortOrder)}
                >
                  <MenuItem value="asc">Ascending</MenuItem>
                  <MenuItem value="desc">Descending</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </Paper>
        )}

        {/* Bulk Actions */}
        {selectedDocuments.size > 0 && (
          <Paper sx={{ p: 1, mt: 2, backgroundColor: '#e3f2fd', display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" sx={{ flexGrow: 1 }}>
              {selectedDocuments.size} document(s) selected
            </Typography>
            <Button
              size="small"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={handleBulkDelete}
            >
              Delete
            </Button>
          </Paper>
        )}
      </Box>

      {/* Document Count and Select All */}
      {filteredDocuments.length > 0 && (
        <Box sx={{ px: 2, py: 1, borderBottom: '1px solid #e0e0e0', display: 'flex', alignItems: 'center', gap: 1 }}>
          <Checkbox
            indeterminate={isPartiallySelected}
            checked={isAllSelected}
            onChange={handleSelectAll}
            size="small"
          />
          <Typography variant="body2" color="text.secondary">
            {filteredDocuments.length} document(s)
          </Typography>
        </Box>
      )}

      {/* Document List */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        <List sx={{ p: 0 }}>
          {filteredDocuments.map((document, index) => (
            <React.Fragment key={document.id}>
              <ListItem disablePadding>
                <ListItemButton
                  selected={selectedDocumentId === document.id}
                  onClick={() => handleDocumentSelect(document.id)}
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
                  <Checkbox
                    checked={selectedDocuments.has(document.id)}
                    onChange={(e) => handleDocumentCheckbox(document.id, e.target.checked)}
                    onClick={(e) => e.stopPropagation()}
                    size="small"
                    sx={{ mr: 1 }}
                  />
                  
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    {getTypeIcon(document.document_type)}
                  </ListItemIcon>
                  
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: selectedDocumentId === document.id ? 500 : 400,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            flexGrow: 1,
                          }}
                        >
                          {document.title}
                        </Typography>
                        {document.category && (
                          <Chip
                            label={document.category}
                            size="small"
                            variant="outlined"
                            sx={{ height: 18, fontSize: '0.65rem' }}
                          />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">
                          {document.file_size_display} • {formatDate(document.created_at)}
                          {document.page_count && ` • ${document.page_count} pages`}
                        </Typography>
                        <Box sx={{ mt: 0.5, display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Chip
                            label={document.status}
                            size="small"
                            color={getStatusColor(document.status)}
                            variant="outlined"
                            sx={{ height: 20, fontSize: '0.7rem' }}
                          />
                          {document.status === 'processing' && document.processing_progress && (
                            <Box sx={{ flexGrow: 1, mr: 2 }}>
                              <LinearProgress 
                                variant="determinate" 
                                value={document.processing_progress}
                                sx={{ height: 4, borderRadius: 2 }}
                              />
                            </Box>
                          )}
                        </Box>
                      </Box>
                    }
                  />
                  
                  <ListItemSecondaryAction>
                    <IconButton
                      size="small"
                      onClick={(e) => handleMenuClick(e, document.id)}
                    >
                      <MoreIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
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
              {searchQuery || categoryFilter !== 'all' || statusFilter !== 'all' 
                ? 'No documents match your filters' 
                : 'No documents yet'}
            </Typography>
            {!searchQuery && categoryFilter === 'all' && statusFilter === 'all' && (
              <Button
                variant="outlined"
                onClick={onDocumentUpload}
                sx={{ mt: 2 }}
                startIcon={<UploadIcon />}
              >
                Upload your first document
              </Button>
            )}
          </Box>
        )}
      </Box>

      {/* Upload FAB */}
      <Box sx={{ position: 'absolute', bottom: 16, right: 16 }}>
        <Fab
          color="primary"
          aria-label="upload document"
          onClick={onDocumentUpload}
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

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => selectedDocumentForMenu && handleRenameClick(selectedDocumentForMenu)}>
          <EditIcon sx={{ mr: 1 }} fontSize="small" />
          Rename
        </MenuItem>
        <MenuItem onClick={() => selectedDocumentForMenu && handleCategoryClick(selectedDocumentForMenu)}>
          <CategoryIcon sx={{ mr: 1 }} fontSize="small" />
          Change Category
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <DownloadIcon sx={{ mr: 1 }} fontSize="small" />
          Download
        </MenuItem>
        <Divider />
        <MenuItem 
          onClick={() => selectedDocumentForMenu && handleDeleteClick(selectedDocumentForMenu)}
          sx={{ color: 'error.main' }}
        >
          <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
          Delete
        </MenuItem>
      </Menu>

      {/* Rename Dialog */}
      <Dialog
        open={renameDialogOpen}
        onClose={() => setRenameDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Rename Document</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Document Title"
            fullWidth
            variant="outlined"
            value={newDocumentTitle}
            onChange={(e) => setNewDocumentTitle(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleRenameConfirm();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleRenameConfirm} 
            variant="contained"
            disabled={!newDocumentTitle.trim()}
          >
            Rename
          </Button>
        </DialogActions>
      </Dialog>

      {/* Category Dialog */}
      <Dialog
        open={categoryDialogOpen}
        onClose={() => setCategoryDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Change Category</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense">
            <InputLabel>Category</InputLabel>
            <Select
              value={newDocumentCategory}
              label="Category"
              onChange={(e) => setNewDocumentCategory(e.target.value)}
            >
              <MenuItem value="General">General</MenuItem>
              <MenuItem value="AI/ML">AI/ML</MenuItem>
              <MenuItem value="Programming">Programming</MenuItem>
              <MenuItem value="Data Science">Data Science</MenuItem>
              <MenuItem value="Business">Business</MenuItem>
              <MenuItem value="Research">Research</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCategoryDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleCategoryConfirm} 
            variant="contained"
            disabled={!newDocumentCategory.trim()}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>Delete Document</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete this document? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default DocumentList; 