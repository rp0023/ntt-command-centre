import { Box } from '@mui/material';
import { useTheme } from '@mui/material/styles';

export function BrandMark({ compact = false }: { compact?: boolean }) {
  const dark = useTheme().palette.mode === 'dark';
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, minWidth: 0 }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          height: compact ? 28 : 34,
          px: 0.75,
          borderRadius: 1,
          bgcolor: dark ? 'transparent' : '#000',
          flexShrink: 0,
        }}
      >
        <Box
          component="img"
          src="/logo.png"
          alt="NTT"
          sx={{ height: compact ? 22 : 28, width: 'auto', maxWidth: { xs: 92, sm: 120 }, display: 'block', objectFit: 'contain' }}
        />
      </Box>
      {!compact && (
        <Box sx={{ width: '1px', height: 22, bgcolor: 'divider', display: { xs: 'none', sm: 'block' } }} />
      )}
      {!compact && (
        <Box
          component="span"
          sx={{
            fontWeight: 700,
            fontSize: { xs: 13, sm: 15.5 },
            letterSpacing: '-0.02em',
            color: 'text.primary',
            display: { xs: 'none', sm: 'block' },
            whiteSpace: 'nowrap',
          }}
        >
          Deal Intelligence
        </Box>
      )}
    </Box>
  );
}
