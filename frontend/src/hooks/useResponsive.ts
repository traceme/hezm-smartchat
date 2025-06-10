import { useTheme } from '@mui/material/styles';
import { useMediaQuery } from '@mui/material';

export const useResponsive = () => {
  const theme = useTheme();
  
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isTablet = useMediaQuery(theme.breakpoints.between('md', 'lg'));
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg'));
  
  const isMobileOrTablet = useMediaQuery(theme.breakpoints.down('md'));
  
  return {
    isMobile,
    isTablet,
    isDesktop,
    isMobileOrTablet,
    breakpoints: theme.breakpoints,
  };
}; 