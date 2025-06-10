import { useTheme, useMediaQuery } from '@mui/material/styles';

export const useResponsive = () => {
  const theme = useTheme();
  
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.between('sm', 'md'));
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'));
  
  const isMobileOrTablet = useMediaQuery(theme.breakpoints.down('md'));
  
  return {
    isMobile,
    isTablet,
    isDesktop,
    isMobileOrTablet,
  };
}; 