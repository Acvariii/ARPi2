import React from 'react';
import { Box, Paper, Stack, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';

export default function EmojiCardTile({
  emoji,
  title,
  corner,
  accent,
  isBack,
  onClick,
  enabled = true,
  width = 74,
}: {
  emoji: string;
  title: string;
  corner: string;
  accent?: string;
  isBack?: boolean;
  onClick?: () => void;
  enabled?: boolean;
  width?: number;
}): React.ReactElement {
  const theme = useTheme();
  const clickable = !!onClick && enabled;

  return (
    <Paper
      variant="outlined"
      onClick={clickable ? onClick : undefined}
      sx={{
        width,
        aspectRatio: '5 / 7',
        borderRadius: 1.25,
        overflow: 'hidden',
        userSelect: 'none',
        cursor: clickable ? 'pointer' : 'default',
        opacity: clickable ? 1 : 0.45,
        borderColor: clickable ? theme.palette.text.primary : 'divider',
        bgcolor: isBack ? theme.palette.primary.main : theme.palette.background.paper,
        color: theme.palette.text.primary,
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Accent border */}
      <Box
        sx={{
          position: 'absolute',
          inset: 0,
          border: `2px solid ${accent || theme.palette.divider}`,
          borderRadius: 1.25,
          pointerEvents: 'none',
          opacity: 0.9,
        }}
      />

      {/* Corners */}
      <Box sx={{ position: 'absolute', top: 6, left: 7, lineHeight: 1 }}>
        <Typography variant="caption" sx={{ fontWeight: 900, color: isBack ? theme.palette.common.white : theme.palette.text.primary }}>
          {corner}
        </Typography>
      </Box>
      <Box sx={{ position: 'absolute', bottom: 6, right: 7, lineHeight: 1, transform: 'rotate(180deg)' }}>
        <Typography variant="caption" sx={{ fontWeight: 900, color: isBack ? theme.palette.common.white : theme.palette.text.primary }}>
          {corner}
        </Typography>
      </Box>

      <Stack spacing={0.5} alignItems="center" sx={{ px: 1, textAlign: 'center' }}>
        <Typography variant="h5" sx={{ lineHeight: 1 }}>
          {emoji}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            fontWeight: 900,
            letterSpacing: 0.3,
            color: isBack ? theme.palette.common.white : theme.palette.text.secondary,
            lineHeight: 1.1,
          }}
        >
          {title}
        </Typography>
      </Stack>
    </Paper>
  );
}
