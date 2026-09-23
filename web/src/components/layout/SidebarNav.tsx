import { useMemo } from 'react';
import { Box, List, ListItemButton, ListItemIcon, ListItemText, Typography } from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import { NavLink } from 'react-router-dom';
import { navGroupsForPersona } from '@/constants/nav';
import { NavIcon } from './iconRegistry';
import { brandTokens } from '@/app/config/theme';
import { useAppSelector } from '@/app/store/hooks';

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const theme = useTheme();
  const persona = useAppSelector((s) => s.persona.current);
  const groups = useMemo(() => navGroupsForPersona(persona), [persona]);
  const isDark = theme.palette.mode === 'dark';
  const mutedColor = isDark ? theme.palette.text.secondary : brandTokens.sidebarMuted;
  const textColor = isDark ? theme.palette.text.primary : brandTokens.sidebarText;
  const activeBg = isDark ? alpha(theme.palette.primary.main, 0.16) : brandTokens.sidebarActive;
  const activeText = isDark ? theme.palette.primary.light : brandTokens.sidebarActiveText;

  return (
    <Box sx={{ px: 1.5 }}>
      {groups.map((group) => (
        <Box key={group.heading || group.items[0]?.to} sx={{ mb: 1.5 }}>
          {group.heading && (
            <Typography sx={{ px: 1.5, py: 1, fontSize: 12, fontWeight: 700, color: mutedColor }}>
              {group.heading}
            </Typography>
          )}
          <List dense disablePadding>
            {group.items.map((item) => (
              <ListItemButton
                key={item.to}
                component={NavLink}
                to={item.to}
                onClick={onNavigate}
                sx={{
                  borderRadius: 2,
                  mb: 0.25,
                  color: textColor,
                  '& .MuiListItemIcon-root': { color: mutedColor, minWidth: 34 },
                  '&.active': {
                    bgcolor: activeBg,
                    color: activeText,
                    '& .MuiListItemText-primary': { fontWeight: 700 },
                    '& .MuiListItemIcon-root': { color: activeText },
                  },
                  '&:hover': { bgcolor: isDark ? 'rgba(241,245,249,0.06)' : 'rgba(0,31,91,0.045)' },
                }}
              >
                <ListItemIcon>
                  <NavIcon iconKey={item.iconKey} fontSize="small" />
                </ListItemIcon>
                <ListItemText primary={item.label} primaryTypographyProps={{ fontSize: 14.5, fontWeight: 500 }} />
              </ListItemButton>
            ))}
          </List>
        </Box>
      ))}
    </Box>
  );
}
