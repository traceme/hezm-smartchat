import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  Avatar,
  List,
  ListItem,
  Chip,
  Menu,
  MenuItem,
  Divider,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Send as SendIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  Settings as SettingsIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import conversationService, { Message } from '../services/conversationService';
import { useError } from '../contexts/ErrorContext';

interface ConversationAreaProps {
  selectedDocumentId?: string | null;
  selectedDocumentTitle?: string;
}

const ConversationArea: React.FC<ConversationAreaProps> = ({ 
  selectedDocumentId, 
  selectedDocumentTitle 
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState('GPT-4o');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Use error context for centralized error handling
  const { handleApiError, handleNetworkError, showError, showSuccess } = useError();

  const models = ['GPT-4o', 'Claude', 'Gemini'];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  // Clear messages when document changes
  useEffect(() => {
    if (selectedDocumentId) {
      setMessages([]);
      setError(null);
      // Add welcome message for the new document
      const welcomeMessage: Message = {
        id: 'welcome-' + Date.now(),
        content: `Hello! I've analyzed your document "${selectedDocumentTitle || 'this document'}". Feel free to ask me any questions about its content.`,
        isUser: false,
        timestamp: new Date(),
        sources: [],
      };
      setMessages([welcomeMessage]);
    }
  }, [selectedDocumentId, selectedDocumentTitle]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !selectedDocumentId) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setError(null);
    setIsStreaming(true);
    setStreamingContent('');

    try {
      // Use streaming API for real-time response
      const streamGenerator = conversationService.sendQueryStream(
        inputMessage,
        selectedModel,
        selectedDocumentId,
        messages
      );

      let finalResponse = '';
      let citations: string[] = [];
      let processingTime = 0;
      let modelUsed = selectedModel;
      
      for await (const chunk of streamGenerator) {
        if (chunk.type === 'chunk' && chunk.content) {
          finalResponse += chunk.content;
          setStreamingContent(prev => prev + chunk.content);
        } else if (chunk.type === 'citations' && chunk.citations) {
          citations = chunk.citations.map(citation => citation.metadata?.page || citation.id);
        } else if (chunk.type === 'final') {
          finalResponse = chunk.response || finalResponse;
          citations = chunk.citations?.map(citation => citation.metadata?.page || citation.id) || citations;
          processingTime = chunk.processing_time || 0;
          modelUsed = chunk.model_used || selectedModel;
          break;
        } else if (chunk.type === 'error') {
          throw new Error(chunk.error || 'Streaming error occurred');
        }
      }

      // Create final message from accumulated data
      const finalMessage: Message = {
        id: Date.now().toString(),
        content: finalResponse,
        isUser: false,
        timestamp: new Date(),
        sources: citations,
        model_used: modelUsed,
        processing_time: processingTime,
      };

      setMessages(prev => [...prev, finalMessage]);

    } catch (error: any) {
      console.error('Error sending message:', error);
      
      // Use centralized error handling
      if (error?.isNetworkError) {
        handleNetworkError(error);
      } else if (error?.isApiError) {
        handleApiError(error, 'Failed to send message to AI');
      } else {
        showError(
          'Failed to send message',
          error?.message || 'An unexpected error occurred while processing your request'
        );
      }
      
      // Add user-friendly error message to conversation
      const aiErrorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `I'm sorry, I'm having trouble processing your request right now. Please try again in a moment.`,
        isUser: false,
        timestamp: new Date(),
        error: error?.message || 'Processing error',
      };
      setMessages(prev => [...prev, aiErrorMessage]);
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
      setStreamingContent('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleModelSelect = (model: string) => {
    setSelectedModel(model);
    setAnchorEl(null);
  };

  if (!selectedDocumentId) {
    return (
      <Box
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'text.secondary',
          p: 4,
        }}
      >
        <BotIcon sx={{ fontSize: 64, mb: 2, opacity: 0.5 }} />
        <Typography variant="h6" gutterBottom>
          Select a Document to Start Chatting
        </Typography>
        <Typography variant="body2" align="center">
          Choose a document from the sidebar to begin your conversation.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Paper
        elevation={1}
        sx={{
          p: 2,
          borderRadius: 0,
          borderBottom: '1px solid #e0e0e0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 500 }}>
            {selectedDocumentTitle || 'Document Chat'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Ready for questions
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            label={selectedModel}
            variant="outlined"
            onClick={(e) => setAnchorEl(e.currentTarget)}
            onDelete={() => setAnchorEl(document.body)}
            deleteIcon={<SettingsIcon />}
            sx={{ cursor: 'pointer' }}
          />
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
          >
            {models.map((model) => (
              <MenuItem
                key={model}
                selected={model === selectedModel}
                onClick={() => handleModelSelect(model)}
              >
                {model}
              </MenuItem>
            ))}
          </Menu>
        </Box>
      </Paper>

      {/* Error Display */}
      {error && (
        <Alert 
          severity="error" 
          onClose={() => setError(null)}
          sx={{ m: 1, borderRadius: 2 }}
          icon={<ErrorIcon />}
        >
          {error}
        </Alert>
      )}

      {/* Messages */}
      <Box sx={{ flexGrow: 1, overflow: 'auto', p: 1 }}>
        <List sx={{ pb: 0 }}>
          {messages.map((message) => (
            <ListItem key={message.id} sx={{ py: 1, px: 0, alignItems: 'flex-start' }}>
              <Box sx={{ display: 'flex', width: '100%', gap: 1 }}>
                <Avatar
                  sx={{
                    width: 32,
                    height: 32,
                    bgcolor: message.isUser 
                      ? '#1a73e8' 
                      : message.error 
                        ? '#d32f2f' 
                        : '#34a853',
                  }}
                >
                  {message.isUser ? <PersonIcon /> : message.error ? <ErrorIcon /> : <BotIcon />}
                </Avatar>
                <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                    {message.isUser ? 'You' : selectedModel} • {message.timestamp.toLocaleTimeString()}
                    {message.processing_time && (
                      <> • {(message.processing_time / 1000).toFixed(1)}s</>
                    )}
                  </Typography>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      bgcolor: message.isUser 
                        ? '#f8f9fa' 
                        : message.error 
                          ? '#ffebee' 
                          : '#fff',
                      border: message.error 
                        ? '1px solid #f44336' 
                        : '1px solid #e0e0e0',
                      borderRadius: 2,
                    }}
                  >
                    {message.isUser ? (
                      <Typography variant="body2">{message.content}</Typography>
                    ) : (
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    )}
                    {message.sources && message.sources.length > 0 && (
                      <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {message.sources.map((source, index) => (
                          <Chip
                            key={index}
                            label={source}
                            size="small"
                            variant="outlined"
                            sx={{ height: 20, fontSize: '0.7rem' }}
                          />
                        ))}
                      </Box>
                    )}
                  </Paper>
                </Box>
              </Box>
            </ListItem>
          ))}
          
          {/* Streaming Message */}
          {isStreaming && streamingContent && (
            <ListItem sx={{ py: 1, px: 0, alignItems: 'flex-start' }}>
              <Box sx={{ display: 'flex', width: '100%', gap: 1 }}>
                <Avatar sx={{ width: 32, height: 32, bgcolor: '#34a853' }}>
                  <BotIcon />
                </Avatar>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                    {selectedModel} • typing...
                  </Typography>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      bgcolor: '#fff',
                      border: '1px solid #e0e0e0',
                      borderRadius: 2,
                    }}
                  >
                    <ReactMarkdown>{streamingContent}</ReactMarkdown>
                    <CircularProgress size={16} sx={{ ml: 1 }} />
                  </Paper>
                </Box>
              </Box>
            </ListItem>
          )}

          {/* Loading Message */}
          {isLoading && !isStreaming && (
            <ListItem sx={{ py: 1, px: 0, alignItems: 'flex-start' }}>
              <Box sx={{ display: 'flex', width: '100%', gap: 1 }}>
                <Avatar sx={{ width: 32, height: 32, bgcolor: '#34a853' }}>
                  <BotIcon />
                </Avatar>
                <Box sx={{ flexGrow: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                    {selectedModel} • searching...
                  </Typography>
                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      bgcolor: '#fff',
                      border: '1px solid #e0e0e0',
                      borderRadius: 2,
                    }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      <CircularProgress size={16} sx={{ mr: 1 }} />
                      Searching through your document...
                    </Typography>
                  </Paper>
                </Box>
              </Box>
            </ListItem>
          )}
        </List>
        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Paper
        elevation={1}
        sx={{
          p: 2,
          borderRadius: 0,
          borderTop: '1px solid #e0e0e0',
        }}
      >
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-end' }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            variant="outlined"
            placeholder={
              selectedDocumentId 
                ? "Ask a question about your document..." 
                : "Select a document to start chatting..."
            }
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={isLoading || !selectedDocumentId}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              },
            }}
          />
          <IconButton
            color="primary"
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading || !selectedDocumentId}
            sx={{
              bgcolor: '#1a73e8',
              color: 'white',
              '&:hover': {
                bgcolor: '#1557b0',
              },
              '&.Mui-disabled': {
                bgcolor: '#e0e0e0',
                color: '#999',
              },
            }}
          >
            {isLoading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
          </IconButton>
        </Box>
      </Paper>
    </Box>
  );
};

export default ConversationArea; 