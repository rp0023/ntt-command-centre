import { createTheme, type Theme, type ThemeOptions } from '@mui/material/styles';

/**
 * NTT DATA-inspired chrome on the Terova layout:
 * NTT Blue + DATA magenta, Noto Sans (corporate Arial family), white cards.
 */
export const brandTokens = {
  nttBlue: '#0067B1',
  nttBlueDark: '#004B86',
  nttBlueLight: '#3D8CC8',
  nttBlueSoft: '#E6F1F8',
  nttMagenta: '#E6007E',
  nttCyan: '#00A9CE',
  navy: '#001F5B',
  navy2: '#0A2F6B',
  cream: '#F4F7FA',
  paper: '#FFFFFF',
  ink: '#001F5B',
  muted: '#5B6B7C',
  line: '#D7E1EA',
  sidebarBg: '#FFFFFF',
  sidebarText: '#1C2B3A',
  sidebarMuted: '#7A8794',
  sidebarActive: '#E6F1F8',
  sidebarActiveText: '#004B86',
  high: '#C62828',
  med: '#ED6C02',
  low: '#2E7D32',
  radius: 10,
  fontFamily: '"Noto Sans", "Helvetica Neue", Arial, sans-serif',
} as const;

const lightPalette: ThemeOptions['palette'] = {
  mode: 'light',
  primary: { main: brandTokens.nttBlue, dark: brandTokens.nttBlueDark, light: brandTokens.nttBlueLight },
  secondary: { main: brandTokens.nttMagenta },
  success: { main: brandTokens.low },
  warning: { main: brandTokens.med },
  error: { main: brandTokens.high },
  info: { main: brandTokens.nttCyan },
  background: { default: brandTokens.cream, paper: brandTokens.paper },
  text: { primary: brandTokens.ink, secondary: brandTokens.muted },
  divider: brandTokens.line,
};

const darkPalette: ThemeOptions['palette'] = {
  mode: 'dark',
  primary: { main: '#4FA3D8', dark: brandTokens.nttBlue, light: '#8EC4E4' },
  secondary: { main: '#FF4DA6' },
  success: { main: '#66BB6A' },
  warning: { main: '#FFB74D' },
  error: { main: '#EF9A9A' },
  info: { main: '#4DD0E1' },
  background: { default: '#07111F', paper: '#0E1A2B' },
  text: { primary: '#F0F4F8', secondary: '#9AA8B6' },
  divider: 'rgba(240,244,248,0.12)',
};

export function createAppTheme(mode: 'light' | 'dark'): Theme {
  const isDark = mode === 'dark';
  return createTheme({
    palette: isDark ? darkPalette : lightPalette,
    shape: { borderRadius: brandTokens.radius },
    typography: {
      fontFamily: brandTokens.fontFamily,
      fontSize: 15.5,
      fontWeightLight: 300,
      fontWeightRegular: 400,
      fontWeightMedium: 500,
      h4: { fontWeight: 700, letterSpacing: '-0.02em' },
      h5: { fontWeight: 700, letterSpacing: '-0.02em' },
      h6: { fontWeight: 600, letterSpacing: '-0.01em' },
      subtitle1: { fontWeight: 600 },
      subtitle2: { fontWeight: 600 },
      button: { textTransform: 'none', fontWeight: 600 },
      overline: { letterSpacing: '0.14em', fontWeight: 700 },
    },
    components: {
      MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' } } },
      MuiCard: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            border: `1px solid ${isDark ? 'rgba(240,244,248,0.10)' : brandTokens.line}`,
            borderRadius: brandTokens.radius + 2,
            boxShadow: isDark ? 'none' : '0 1px 2px rgba(0,31,91,.05), 0 1px 3px rgba(0,31,91,.06)',
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: { root: { borderRadius: brandTokens.radius - 2 } },
      },
      MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontWeight: 700,
            whiteSpace: 'nowrap',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            fontSize: 12,
          },
        },
      },
    },
  });
}

export const CHART_COLORS = ['#0067B1', '#E6007E', '#00A9CE', '#004B86', '#7B1FA2', '#2E7D32', '#ED6C02', '#455A64'];
