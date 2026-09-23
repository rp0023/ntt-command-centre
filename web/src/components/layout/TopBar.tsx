import { AppBar, Box, IconButton, Toolbar, Tooltip } from '@mui/material';
import MenuRoundedIcon from '@mui/icons-material/MenuRounded';
import LightModeRoundedIcon from '@mui/icons-material/LightModeRounded';
import DarkModeRoundedIcon from '@mui/icons-material/DarkModeRounded';
import { BrandMark } from './BrandMark';
import { PersonaSwitcher } from './PersonaSwitcher';
import { AlertsBell } from './AlertsBell';
import { useAppDispatch, useAppSelector } from '@/app/store/hooks';
import { toggleSidebar, toggleTheme } from '@/app/store/uiSlice';

export function TopBar() {
  const dispatch = useAppDispatch();
  const themeMode = useAppSelector((s) => s.ui.themeMode);
  return (
    <AppBar position="fixed" elevation={0} color="default" sx={{ zIndex: (t) => t.zIndex.drawer + 1, bgcolor: 'background.paper', borderBottom: 1, borderColor: 'divider' }}>
      <Toolbar sx={{ gap: { xs: 0.5, sm: 1 }, minHeight: { xs: 56, sm: 64 }, px: { xs: 1, sm: 2 } }}>
        <IconButton edge="start" onClick={() => dispatch(toggleSidebar())} aria-label="Toggle navigation">
          <MenuRoundedIcon />
        </IconButton>
        <BrandMark />
        <Box sx={{ flexGrow: 1 }} />
        <PersonaSwitcher />
        <AlertsBell />
        <Tooltip title={themeMode === 'light' ? 'Dark mode' : 'Light mode'}>
          <IconButton onClick={() => dispatch(toggleTheme())} aria-label="Toggle colour mode">
            {themeMode === 'light' ? <DarkModeRoundedIcon /> : <LightModeRoundedIcon />}
          </IconButton>
        </Tooltip>
      </Toolbar>
    </AppBar>
  );
}
