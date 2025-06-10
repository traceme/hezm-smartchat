import React from 'react';
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

const DRAWER_WIDTH = 320;

interface LayoutProps {
  children?: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

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
        <DocumentList />
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
        <ConversationArea />
      </Box>
    </Box>
  );
};

export default Layout; 