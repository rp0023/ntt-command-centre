import { Suspense, useEffect } from 'react';
import { Box, Drawer, Toolbar, useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { Outlet } from 'react-router-dom';
import { TopBar } from './TopBar';
import { SidebarNav } from './SidebarNav';
import { DrawerHost } from './DrawerHost';
import { CopilotDock } from './CopilotDock';
import { useAppDispatch, useAppSelector } from '@/app/store/hooks';
import { setSidebarOpen } from '@/app/store/uiSlice';
import { RouteFallback } from '@/components/loaders/RouteFallback';
import { brandTokens } from '@/app/config/theme';

const DRAWER_WIDTH = 256;

export function AppShell() {
  const dispatch = useAppDispatch();
  const sidebarOpen = useAppSelector((s) => s.ui.sidebarOpen);
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'), { defaultMatches: true });
  const isDark = theme.palette.mode === 'dark';
  useEffect(() => {
    if (!isDesktop) dispatch(setSidebarOpen(false));
  }, [isDesktop, dispatch]);
  const sidebarPaperSx = {
    boxSizing: 'border-box' as const,
    bgcolor: isDark ? 'background.paper' : brandTokens.sidebarBg,
    color: isDark ? 'text.secondary' : brandTokens.sidebarText,
    borderRight: `1px solid ${isDark ? theme.palette.divider : brandTokens.line}`,
    overflowX: 'hidden' as const,
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <TopBar />
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', md: 'block' },
          width: sidebarOpen ? DRAWER_WIDTH : 0,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            ...sidebarPaperSx,
            width: sidebarOpen ? DRAWER_WIDTH : 0,
            transition: (t) => t.transitions.create('width'),
          },
        }}
        open
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto', py: 1.25 }}>
          <SidebarNav />
        </Box>
      </Drawer>
      <Drawer
        variant="temporary"
        open={sidebarOpen && !isDesktop}
        onClose={() => dispatch(setSidebarOpen(false))}
        ModalProps={{ keepMounted: true }}
        sx={{ display: { xs: 'block', md: 'none' }, '& .MuiDrawer-paper': { width: DRAWER_WIDTH, ...sidebarPaperSx } }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto', py: 1.25 }}>
          <SidebarNav onNavigate={() => dispatch(setSidebarOpen(false))} />
        </Box>
      </Drawer>
      <Box component="main" className="ntt-app-main" sx={{ flexGrow: 1, minWidth: 0 }}>
        <Toolbar className="ntt-no-print" />
        <Box sx={{ p: { xs: 1.5, sm: 2, md: 3.5 }, pb: { xs: 11, md: 3.5 }, maxWidth: 1520, mx: 'auto' }}>
          <Suspense fallback={<RouteFallback />}>
            <Outlet />
          </Suspense>
        </Box>
      </Box>
      <DrawerHost />
      <CopilotDock />
    </Box>
  );
}
