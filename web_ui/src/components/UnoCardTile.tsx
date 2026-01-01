import React from 'react';
import { Box, Paper, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';

function faceFromText(theme: any, text: string): { bg: string; fg: string; center: string; corner: string } {
  const t = String(text || '').trim().toUpperCase();

  if (t.startsWith('WILD')) {
    return {
      bg: theme.palette.grey[800],
      fg: theme.palette.common.white,
      center: t.replace('WILD', 'WILD').replace('+4', '+4'),
      corner: t.includes('+4') ? '+4' : 'W',
    };
  }

  const c = t[0];
  const rest = t.slice(1);
  if (c === 'R') return { bg: theme.palette.error.main, fg: theme.palette.common.white, center: rest || 'R', corner: rest || 'R' };
  if (c === 'G') return { bg: theme.palette.success.main, fg: theme.palette.common.white, center: rest || 'G', corner: rest || 'G' };
  if (c === 'B') return { bg: theme.palette.info.main, fg: theme.palette.common.white, center: rest || 'B', corner: rest || 'B' };
  if (c === 'Y') return { bg: theme.palette.warning.main, fg: theme.palette.common.black, center: rest || 'Y', corner: rest || 'Y' };

  return {
    bg: theme.palette.background.paper,
    fg: theme.palette.text.primary,
    center: t || '—',
    corner: t || '—',
  };
}

export default function UnoCardTile({
  text,
  asBack,
  onClick,
  enabled = true,
  width = 74,
}: {
  text: string;
  asBack?: boolean;
  onClick?: () => void;
  enabled?: boolean;
  width?: number;
}): React.ReactElement {
  const theme = useTheme();
  const clickable = !!onClick && enabled;
  const face = faceFromText(theme, text);

  // Card back: neutral look (like the deck)
  const bg = asBack ? theme.palette.primary.main : face.bg;
  const fg = asBack ? theme.palette.common.white : face.fg;

  return (
    <Paper
      variant="outlined"
      onClick={clickable ? onClick : undefined}
      sx={{
        width,
        aspectRatio: '5 / 7',
        borderRadius: 2,
        overflow: 'hidden',
        userSelect: 'none',
        cursor: clickable ? 'pointer' : 'default',
        opacity: clickable ? 1 : 0.45,
        borderColor: clickable ? theme.palette.text.primary : 'divider',
        bgcolor: bg,
        color: fg,
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* corner labels */}
      <Box sx={{ position: 'absolute', top: 6, left: 7, lineHeight: 1 }}>
        <Typography variant="caption" sx={{ fontWeight: 800, color: fg }}>
          {asBack ? 'UNO' : face.corner}
        </Typography>
      </Box>
      <Box sx={{ position: 'absolute', bottom: 6, right: 7, lineHeight: 1, transform: 'rotate(180deg)' }}>
        <Typography variant="caption" sx={{ fontWeight: 800, color: fg }}>
          {asBack ? 'UNO' : face.corner}
        </Typography>
      </Box>

      {/* center oval */}
      <Box
        sx={{
          width: '76%',
          height: '58%',
          borderRadius: '999px',
          border: `2px solid ${theme.palette.common.white}`,
          bgcolor: 'rgba(0,0,0,0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Typography variant="subtitle1" sx={{ fontWeight: 900, letterSpacing: 0.5, color: fg }}>
          {asBack ? text : face.center}
        </Typography>
      </Box>
    </Paper>
  );
}
